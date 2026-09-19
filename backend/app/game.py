"""游戏状态管理(单局):说书人配置板子/人数,玩家选环形座位入座。

v1 完整版新增:
- 昼夜阶段(phase: night/day)与夜晚流程助手(按 NIGHT_ORDER 逐步推进)
- 状态标记(中毒/醉酒/疯狂,仅说书人可见)
- 白天提名→投票→处决
- JSON 自动存档:每次变更即写盘,进程重启自动恢复
"""

import json
import os
import random
import secrets
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .night_order import NIGHT_ORDER
from .roles import (COMPOSITION, DEMON, MINION, OUTSIDER, SCRIPTS,
                    SCRIPT_ADJUST_ROLES, ROLE_ADJUSTMENTS, TOWNSFOLK)
from .scripts.travelers import (DUSK_ORDER as TRAVELER_DUSK,
                                RECOMMENDED as TRAVELER_RECOMMENDED,
                                ROLE_BY_ID as TRAVELER_BY_ID,
                                ROLES as TRAVELERS)
from .scripts.wafu_leiming import NIGHT_ACTIONS

SAVE_PATH = Path(__file__).resolve().parent.parent / "data" / "game.json"

# 说书人标记:中毒/醉酒/疯狂/角色转变/阵营转变——同一座位可同时挂多个(列表存储)
MARKERS = ("poisoned", "drunk", "mad", "role-change", "team-change")
MARKER_LABELS = {"poisoned": "中毒", "drunk": "醉酒", "mad": "疯狂"}

# 认知覆盖类角色 → 假身份可取阵营(配板时决定):酒鬼看到镇民,疯子以为自己是恶魔
FAKE_POOLS = {"drunk": (TOWNSFOLK,), "lunatic": (DEMON,)}


@dataclass
class Player:
    id: str
    name: str
    seat: int | None = None
    role_id: str | None = None
    alive: bool = True
    died_day: int | None = None  # 死亡公开在第几天:夜里死=该夜天亮的 day_no,白天死=当天 day_no;复活/未死=None
    dead_vote_used: bool = False  # 死票:每个死者整局只有一票,举手交出后置 True(复活重置)
    wish: str | None = None  # 许愿(仅大厅):善良/邪恶或自定义文字,说书人配板时参考;仅本人与说书人可见

    def public(self) -> dict:
        return {"id": self.id, "name": self.name, "seat": self.seat, "alive": self.alive}

    def private(self, roles: dict, fake_id: str | None = None) -> dict:
        """玩家自己看到的视图。fake_id 为认知覆盖:酒鬼看到说书人标记的假镇民角色。"""
        view = self.public()
        rid = fake_id if (fake_id and self.role_id) else self.role_id
        if rid:
            view["role"] = roles[rid]
        return view

    def storyteller(self, roles: dict) -> dict:
        """说书人全知视图。"""
        view = self.public()
        view["wish"] = self.wish  # 许愿仅说书人可见(玩家座位列表里的 public() 不带)
        if self.role_id:
            view["role"] = roles[self.role_id]
        return view


class GameManager:
    """一局游戏的全部状态;每次变更自动存档,重启自动恢复。"""

    def __init__(self) -> None:
        self.reset()
        self.script_id: str = "trouble-brewing"  # 说书人可配置
        self.player_count: int = 6
        self._restore_autosave()  # 进程重启 → 恢复上次存档(若有)

    def reset(self) -> None:
        # 注意:reset 不写盘 → 误重置可用「读档」撤销;开始新局的第一次变更会覆盖存档
        self.players: dict[str, Player] = {}
        self.status: str = "lobby"  # lobby | playing
        self.seat_roles: dict[int, str] = {}  # 预发身份:座位号 → 角色 id(未入座也能先发)
        self.current_dead_votes: set[int] = set()  # 当前提名中交出的死票座位(结算即清空;未结算时取消举手可归还)
        self.seat_fakes: dict[int, str] = {}  # 认知覆盖:座位号 → 玩家看到的假角色 id(酒鬼/疯子)
        self.lunatic_minions: dict[int, list[int]] = {}  # 疯子:座位号 → 疯子以为的爪牙座位(说书人选,不一定是真爪牙)
        self.lunatic_bluffs: dict[int, list[str]] = {}  # 疯子:座位号 → 说书人给疯子的 3 个伪装(不一定是恶魔的真伪装)
        self.seat_markers: dict[int, list] = {}  # 状态标记:座位号 → [poisoned/drunk/mad]
        self.mad_about: dict[int, str] = {}  # 疯狂内容:座位号 → 善良角色 id(被疯狂者疯狂宣称自己是该角色)
        self.seat_alive: dict[int, bool] = {}  # 空座生死(说书人标记为准):只存 False,复活即删除
        self.seat_dead_day: dict[int, int] = {}  # 空座死亡公开在第几天
        self.seat_dead_vote: dict[int, bool] = {}  # 空座死票是否已交
        self.seat_role_changes: dict[int, str] = {}  # 角色转变:座位号 → 变成的新角色 id(说书人选择标记,告知玩家)
        self.seat_team_changes: dict[int, str] = {}  # 阵营转变:座位号 → 新阵营 good/evil(说书人选择标记,告知玩家)
        self.phase: str | None = None  # None(大厅)| "night" | "day"
        self.day_stage: str = "talk"  # 白天子阶段:"talk" 公聊私聊 | "nom" 提名阶段(说书人控节奏)
        self.night_no: int = 1  # 当前是第几夜(1 起)
        self.day_no: int = 0  # 当前是第几天(第一次天亮置 1)
        self.night_steps: list[dict] = []  # 本夜步骤 [{key,name,hint,fake_for?}]
        self.night_idx: int = 0  # 当前走到第几步
        self.nominations: list[dict] = []  # 提名历史 [{day,nominator,nominee,votes,passed,executed}]
        self.current: dict | None = None  # 进行中的提名 {nominator,nominee,votes}
        self.night_kills: dict = {}  # 夜晚刀人(瓦釜雷鸣手机操作):{str(夜): {seat: 被刀座, by: 恶魔座, role: rid, lunatic_seat: 疯子选的座, lunatic_by: 疯子座}}
        self.night_choices: dict = {}  # 夜晚信息交互:{str(夜): {str(座): {role, targets: [座], reply: 说书人回复}}}
        self.fortuneteller_red: int | None = None  # 占卜师宿敌(红鲱鱼):说书人私下标记的善良玩家座位(只有说书人知道)
        self.travelers: list[dict] = []  # 旅行者:[{id(t1..),player_id,name,role_id,align,alive,exiled,joined_phase,joined_no,died_day,dead_vote_used}]
        self.bluffs: list[str] = []  # 恶魔的三个伪装:不在场的好角色 id(开局时抽取)
        self.sentinel: int = 0  # 哨兵(神职角色):0=关 / +1 / -1 / 2=在场但不调整
        self.room_code: str = f"{random.randrange(10000):04d}"  # 房间号:4 位数字,说书人可改,玩家凭名字+房号加入
        self.saved_at: float | None = None

    @property
    def roles(self) -> dict:
        return {r["id"]: r for r in SCRIPTS[self.script_id]["roles"]}

    @property
    def seats(self) -> dict[int, Player]:
        return {p.seat: p for p in self.players.values() if p.seat is not None}

    # ---- 存档 ----

    def save(self) -> None:
        """任何状态变更后调用:原子写盘(临时文件 + os.replace)。"""
        payload = {
            "players": {pid: {"id": p.id, "name": p.name, "seat": p.seat,
                              "role_id": p.role_id, "alive": p.alive,
                              "died_day": p.died_day,
                              "dead_vote_used": p.dead_vote_used,
                              "wish": p.wish}
                        for pid, p in self.players.items()},
            "status": self.status, "script_id": self.script_id,
            "player_count": self.player_count,
            "seat_roles": self.seat_roles, "seat_fakes": self.seat_fakes,
            "lunatic_minions": self.lunatic_minions, "lunatic_bluffs": self.lunatic_bluffs,
            "seat_markers": self.seat_markers, "mad_about": self.mad_about,
            "seat_alive": self.seat_alive, "seat_dead_day": self.seat_dead_day,
            "seat_dead_vote": self.seat_dead_vote,
            "seat_role_changes": self.seat_role_changes,
            "seat_team_changes": self.seat_team_changes,
            "phase": self.phase, "night_no": self.night_no, "day_no": self.day_no,
            "day_stage": self.day_stage,
            "night_steps": self.night_steps, "night_idx": self.night_idx,
            "nominations": self.nominations, "current": self.current,
            "current_dead_votes": sorted(map(str, self.current_dead_votes)),  # 座位号或旅行者 id 混存,统一转 str 排序
            "night_kills": self.night_kills,
            "night_choices": self.night_choices,
            "fortuneteller_red": self.fortuneteller_red,
            "travelers": self.travelers,
            "bluffs": self.bluffs, "sentinel": self.sentinel, "room_code": self.room_code,
        }
        SAVE_PATH.parent.mkdir(exist_ok=True)
        tmp = SAVE_PATH.with_suffix(".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, SAVE_PATH)
        self.saved_at = time.time()

    def _restore_autosave(self) -> None:
        if not SAVE_PATH.exists():
            return
        try:
            d = json.loads(SAVE_PATH.read_text(encoding="utf-8"))
            for pd in d["players"].values():  # 兼容:开发期间字段曾叫 died_night,迁移为 died_day
                if "died_night" in pd:
                    pd.setdefault("died_day", pd.pop("died_night"))
            self.players = {pid: Player(**p) for pid, p in d["players"].items()}
            for key in ("status", "script_id", "player_count", "seat_roles",
                        "seat_fakes", "seat_markers", "phase", "night_no",
                        "day_no", "night_steps", "night_idx", "nominations",
                        "current", "bluffs"):
                setattr(self, key, d[key])
            self.day_stage = d.get("day_stage", "talk")  # 旧存档没有白天子阶段 → 默认公聊
            self.sentinel = d.get("sentinel", 0)  # 旧存档没有哨兵字段 → 默认关
            self.room_code = d.get("room_code") or f"{random.randrange(10000):04d}"  # 旧存档没有房间号 → 现生成
            self.lunatic_minions = d.get("lunatic_minions", {})  # 旧存档没有疯子假爪牙/伪装字段 → 空
            self.lunatic_bluffs = d.get("lunatic_bluffs", {})
            # 死票座位/旅行者 id 存档时统一转 str,读档时数字座位还原为 int(旅行者 id 保持 "t1" 字符串)
            self.current_dead_votes = {int(x) if isinstance(x, str) and x.isdigit() else x
                                       for x in d.get("current_dead_votes", [])}
            self.seat_role_changes = d.get("seat_role_changes", {})  # 旧存档没有角色转变 → 空
            self.mad_about = {int(k): v for k, v in d.get("mad_about", {}).items()}  # 旧存档没有疯狂内容 → 空
            self.seat_alive = {int(k): v for k, v in d.get("seat_alive", {}).items()}  # 空座生死 → 空
            self.seat_dead_day = {int(k): v for k, v in d.get("seat_dead_day", {}).items()}
            self.seat_dead_vote = {int(k): v for k, v in d.get("seat_dead_vote", {}).items()}
            self.seat_team_changes = d.get("seat_team_changes", {})  # 旧存档没有阵营转变 → 空
            self.travelers = d.get("travelers", [])  # 旧存档没有旅行者 → 空
            self.night_kills = d.get("night_kills", {})  # 旧存档没有夜晚刀人 → 空
            self.night_choices = d.get("night_choices", {})  # 旧存档没有夜晚信息交互 → 空
            self.fortuneteller_red = d.get("fortuneteller_red")  # 旧存档没有宿敌 → None
            self.saved_at = time.time()
        except (KeyError, TypeError, ValueError):
            pass  # 存档损坏 → 用干净状态开局

    def load(self) -> None:
        """说书人手动读档:放弃当前内存状态,从磁盘恢复。"""
        self.reset()
        self.script_id = "trouble-brewing"
        self.player_count = 6
        self._restore_autosave()

    # ---- 局配置 ----

    def configure(self, script_id: str, player_count: int) -> None:
        if script_id not in SCRIPTS:
            raise ValueError("未知脚本")
        min_players = SCRIPTS[script_id].get("min_players", 5)
        if not min_players <= player_count <= 15:
            raise ValueError(f"人数需在 {min_players}~15 之间")
        self.script_id = script_id
        self.player_count = player_count
        for p in self.players.values():  # 改配置 → 清空座位与角色,玩家重新入座
            p.seat = None
            p.role_id = None
            p.alive = True
            p.died_day = None
        self.seat_roles = {}  # 预发身份一并清空
        self.seat_fakes = {}  # 认知覆盖一并清空
        self.lunatic_minions = {}
        self.lunatic_bluffs = {}
        self.seat_markers = {}  # 状态标记一并清空
        self.mad_about = {}  # 疯狂内容一并清空
        self.seat_alive = {}  # 空座生死一并清空
        self.seat_dead_day = {}
        self.seat_dead_vote = {}
        self.seat_role_changes = {}  # 角色转变一并清空
        self.seat_team_changes = {}  # 阵营转变一并清空
        self.phase = None
        self.day_stage = "talk"
        self.night_no, self.day_no = 1, 0
        self.night_steps, self.night_idx = [], 0
        self.nominations, self.current = [], None
        self.night_kills = {}  # 换板子/人数 → 夜晚刀人清空
        self.night_choices = {}  # 夜晚信息交互一并清空
        self.fortuneteller_red = None  # 宿敌随角色清空
        self.travelers = []  # 旅行者只存在于进行中的局,改配置即清空
        self.bluffs = []
        self.sentinel = 0  # 哨兵选择跟板子走:换板子/人数即重置
        self.status = "lobby"
        self.save()

    def set_sentinel(self, value: int) -> None:
        """哨兵(神职角色):说书人选择外来者 +1/−1,2=在场但不调整,0 关闭。仅开局前可改。"""
        if value not in (-1, 0, 1, 2):
            raise ValueError("哨兵取值需为 -1 / 0 / +1 / 2(不变)")
        if self.status == "playing":
            raise ValueError("本局已开始,不能修改哨兵")
        if value == -1 and COMPOSITION[self.player_count][1] < 1:
            raise ValueError(f"{self.player_count} 人局官方配比没有外来者,哨兵不能 −1")
        self.sentinel = value
        self.save()

    def set_room_code(self, code: str) -> None:
        """说书人设定房间号:4 位数字。随时可改(不限制 lobby),改号后新加入者需用新码。"""
        if len(code) != 4 or not code.isdigit():
            raise ValueError("房间号需为 4 位数字")
        self.room_code = code
        self.save()

    # ---- 玩家进出 ----

    def add_player(self, name: str) -> Player:
        player = Player(id=secrets.token_hex(4), name=name.strip()[:20])
        self.players[player.id] = player
        self.save()
        return player

    def set_wish(self, player_id: str, wish: str | None) -> None:
        """许愿(仅大厅):开局前表达愿望——善良/邪恶或自定义文字;空/None = 清除。"""
        if player_id not in self.players:
            raise ValueError("玩家不存在")
        if self.status != "lobby":
            raise ValueError("游戏已开始,不能再许愿")
        me = self.players[player_id]
        wish = (wish or "").strip()[:30]
        me.wish = wish or None
        self.save()

    def sit(self, player_id: str, seat: int) -> None:
        if player_id not in self.players:
            raise ValueError("玩家不存在")
        if not 1 <= seat <= self.player_count:
            raise ValueError(f"座位需在 1~{self.player_count} 之间")
        me = self.players[player_id]
        if self.status == "playing" and me.seat is not None:
            raise ValueError("游戏进行中,不能换座")
        owner = self.seats.get(seat)
        if owner and owner.id != player_id:
            raise ValueError(f"座位 {seat} 已被 {owner.name} 占用")
        me.seat = seat
        # 预发身份跟随座位:入座即继承该座已发的角色(开局后迟到的玩家同样继承)
        me.role_id = self.seat_roles.get(seat)
        # 生死/死票同样以座位标记为准:空座被标死的角色,入座玩家继承死亡状态
        if seat in self.seat_alive:
            me.alive = self.seat_alive[seat]
            me.died_day = self.seat_dead_day.get(seat)
            me.dead_vote_used = self.seat_dead_vote.get(seat, False)
        if (self.status == "lobby" and self.seat_roles
                and len(self.seats) == self.player_count):
            self.status = "playing"  # 预发身份全部入座 → 自动开局
            self._begin_night()
        self.save()

    def remove_player(self, player_id: str) -> None:
        if player_id not in self.players:
            return
        del self.players[player_id]  # 座位随玩家释放
        self.save()

    # ---- 旅行者 ----

    def traveler_of(self, player_id: str) -> dict | None:
        return next((t for t in self.travelers if t["player_id"] == player_id), None)

    def _traveler(self, traveler_id: str) -> dict:
        t = next((x for x in self.travelers if x["id"] == traveler_id), None)
        if t is None:
            raise ValueError("旅行者不存在")
        return t

    def add_traveler(self, player_id: str) -> dict:
        """玩家以旅行者身份加入:开局后任意时刻可加入,不占座位、不算配板。"""
        if self.status != "playing":
            raise ValueError("游戏开始后旅行者才能加入")
        if player_id not in self.players:
            raise ValueError("玩家不存在")
        me = self.players[player_id]
        if me.seat is not None:
            raise ValueError("你已入座,不能作为旅行者加入")
        if self.traveler_of(player_id):
            raise ValueError("你已经是旅行者")
        t = {
            "id": f"t{len(self.travelers) + 1}",  # 旅行者从不移除,序号只增不重复
            "player_id": player_id,
            "name": me.name,
            "role_id": None,   # 等说书人指派旅行者角色
            "align": "good",   # 阵营由说书人私下决定(官方:绝大多数情况给善良)
            "alive": True,
            "exiled": False,   # 流放 = 旅行者的处决(白天投票通过或说书人随时执行)
            "joined_phase": self.phase,
            "joined_no": self.day_no if self.phase == "day" else self.night_no,
            "died_day": None,
            "dead_vote_used": False,  # 死票:死亡旅行者同样获得一枚(流放表决不消耗)
        }
        self.travelers.append(t)
        self.save()
        return t

    def add_traveler_st(self, name: str) -> dict:
        """说书人直接添加旅行者(无手机关联,说书人代管投票/生死):开局后任意时刻。"""
        if self.status != "playing":
            raise ValueError("游戏开始后才能添加旅行者")
        name = (name or "").strip()
        if not name:
            raise ValueError("请填写旅行者名字")
        t = {
            "id": f"t{len(self.travelers) + 1}",  # 旅行者从不移除,序号只增不重复
            "player_id": None,   # 说书人添加:无手机关联
            "name": name[:20],
            "role_id": None,   # 等说书人指派旅行者角色
            "align": "good",   # 阵营由说书人私下决定(官方:绝大多数情况给善良)
            "alive": True,
            "exiled": False,
            "joined_phase": self.phase,
            "joined_no": self.day_no if self.phase == "day" else self.night_no,
            "died_day": None,
            "dead_vote_used": False,
        }
        self.travelers.append(t)
        self.save()
        return t

    def assign_traveler(self, traveler_id: str, role_id: str, align: str | None = None) -> None:
        """说书人给旅行者指派角色(与阵营):角色限官方旅行者池,阵营 good/evil(默认善良)。"""
        if self.status != "playing":
            raise ValueError("游戏开始后才能指派旅行者")
        t = self._traveler(traveler_id)
        if role_id not in TRAVELER_BY_ID:
            raise ValueError("不是旅行者角色")
        if align is not None and align not in ("good", "evil"):
            raise ValueError("阵营需为 good/evil")
        t["role_id"] = role_id
        if align:
            t["align"] = align
        self.save()

    def exile_traveler(self, traveler_id: str, exiled: bool) -> None:
        """流放/撤销流放:白天投票流放,或说书人随时执行(早退玩家)。流放当场公开。"""
        t = self._traveler(traveler_id)
        t["exiled"] = exiled
        t["alive"] = not exiled
        t["died_day"] = (self.day_no if self.phase == "day" else self.night_no) if exiled else None
        self.save()

    def toggle_traveler_alive(self, traveler_id: str) -> None:
        """旅行者生/死标记(恶魔夜袭等);夜里死天亮才公开(与座位玩家同规则)。"""
        t = self._traveler(traveler_id)
        if t["exiled"]:
            raise ValueError("已流放:先撤销流放才能改动生死")
        t["alive"] = not t["alive"]
        t["died_day"] = None if t["alive"] else (self.day_no if self.phase == "day" else self.night_no)
        self.save()

    def _target(self, target: int | str) -> tuple[Player | None, dict | None]:
        """提名/投票目标:座位 int → (玩家,None);"t1" 字符串 → (None,旅行者)。"""
        if isinstance(target, int):
            return self.seats.get(target), None
        return None, next((t for t in self.travelers if t["id"] == target), None)

    # ---- 角色分配 ----

    def assign_roles(self) -> list[dict]:
        """随机分配角色。人未齐也能发牌:全部座位一次性抽出,空座挂预发身份,
        迟到玩家入座自动继承。发完立即进入第一夜。"""
        n = self.player_count
        if self.status == "playing":
            raise ValueError("本局已开始,先重置")

        comp = list(COMPOSITION[n])
        by_team = {team: [r for r in SCRIPTS[self.script_id]["roles"] if r["team"] == team]
                   for team in (TOWNSFOLK, OUTSIDER, MINION, DEMON)}

        demons = random.sample(by_team[DEMON], comp[3])
        if any(r["id"] == "lil-monsta" for r in demons):
            # 小怪宝官方开局:移除恶魔角色标记、加入一个爪牙标记(小怪宝不是玩家,由爪牙每晚决定照看者)
            pool = random.sample(by_team[MINION], comp[2] + 1)
        else:
            pool = demons + random.sample(by_team[MINION], comp[2])
        # 第一轮配比:已抽中的恶魔/爪牙触发调整(方古/亡骨魔/男爵/教父)
        comp = list(self.expected_composition([r["id"] for r in pool]))
        pool += random.sample(by_team[OUTSIDER], comp[1])
        pool += random.sample(by_team[TOWNSFOLK], comp[0])
        # 第二轮配比:镇民里的调整角色(气球驾驶员 +1 外来者)抽中后,按最终期望配比
        # 用换人法对账。注意所有调整先叠加再钳制:亡骨魔 −1 与气球驾驶员 +1 恰好抵消时不做替换
        adjust_ids = SCRIPT_ADJUST_ROLES.get(self.script_id, ())
        final = list(self.expected_composition([r["id"] for r in pool]))
        while True:
            outsiders = sum(1 for r in pool if r["team"] == OUTSIDER)
            if outsiders < final[1]:  # 缺外来者:换掉一名非调整镇民
                victim = next((r for r in pool
                               if r["team"] == TOWNSFOLK and r["id"] not in adjust_ids), None)
                if victim is None:
                    break
                pool.remove(victim)
                pool.append(random.sample(by_team[OUTSIDER], 1)[0])
            elif outsiders > final[1]:  # 多外来者:换回一名镇民
                victim = next(r for r in pool if r["team"] == OUTSIDER)
                pool.remove(victim)
                pool.append(random.sample(by_team[TOWNSFOLK], 1)[0])
            else:
                break
        random.shuffle(pool)

        self.seat_roles = {}  # 随机分配覆盖整局:清掉之前的预发草稿
        for seat in range(1, n + 1):
            rid = pool[seat - 1]["id"]
            p = self.seats.get(seat)
            if p:
                p.role_id = rid
            else:
                self.seat_roles[seat] = rid  # 空座挂预发身份,等人迟到入座继承
        self.bluffs = self._pick_bluffs({r["id"] for r in pool})  # 配版时即抽好伪装
        # 认知覆盖不自动抽:假身份由说书人显式选定(ST 面板提示待定座位,玩家卡先别给看)
        self.seat_fakes = {}
        self.lunatic_minions = {}
        self.lunatic_bluffs = {}
        self.status = "playing"
        self._begin_night()  # 发完角色 → 第一夜开始
        self.save()
        by_seat = sorted((p for p in self.players.values() if p.seat is not None),
                         key=lambda p: p.seat)  # 没入座的玩家(seat=None)不参与排序,否则 None 比较会 500
        return [p.storyteller(self.roles) for p in by_seat]

    def expected_composition(self, role_ids: list[str]) -> tuple:
        """按在场角色计算配比:基础表 + 脚本调整 + 哨兵,外来者数钳制 ≥ 0。"""
        comp = list(COMPOSITION[self.player_count])
        for rid in SCRIPT_ADJUST_ROLES.get(self.script_id, ()):
            if rid in role_ids:
                dt, do, dm, dd = ROLE_ADJUSTMENTS[rid]
                comp[0] += dt
                comp[1] += do
                comp[2] += dm
                comp[3] += dd
        if self.sentinel in (-1, 1):
            comp[1] += self.sentinel  # 哨兵:说书人定的 +1/−1 外来者(2=不变 不调整)
            comp[0] -= self.sentinel  # 镇民反向调整,总人数保持不变
        if comp[1] < 0:
            comp[0] += comp[1]
            comp[1] = 0
        return tuple(comp)

    def assign_manual(self, assignments: list[dict], bluffs: list[str] | None = None,
                      fakes: list[dict] | None = None) -> list[dict]:
        """说书人手动发身份:为每个座位指定角色。

        硬校验:恶魔恰 1 名、爪牙至少 1 名;镇民/外来者配比只作提示(教父 ±1 等由说书人决定)。
        无需等玩家入座:身份先挂在座位上,玩家入座时自动继承;全员入座后自动开局。
        伪装在配版时就选好:bluffs 给 3 个不在场好角色;不给则自动抽取。
        认知覆盖同样配版时决定:fakes 指定疯子/酒鬼看到的假身份,未指定的自动抽取。
        """
        if self.status == "playing":
            raise ValueError("本局已开始,先重置")
        seat_of = self.seats
        if len(assignments) != self.player_count:
            raise ValueError(f"需为全部 {self.player_count} 个座位指定角色")
        picked: dict[int, str] = {}
        for item in assignments:
            seat, rid = item.get("seat"), item.get("role")
            if not isinstance(seat, int) or not 1 <= seat <= self.player_count:
                raise ValueError(f"座位 {seat} 无效")
            if seat in picked:
                raise ValueError(f"座位 {seat} 被重复分配")
            if rid not in self.roles:
                raise ValueError(f"角色 {rid} 不属于当前板子")
            picked[seat] = rid
        teams = Counter(self.roles[rid]["team"] for rid in picked.values())
        if len(set(picked.values())) != len(picked):
            raise ValueError("角色不能重复:每个角色在本局最多出现一次")
        if teams.get(DEMON, 0) != 1:
            raise ValueError("必须且只能有 1 名恶魔")
        if teams.get(MINION, 0) < 1:
            raise ValueError("至少要有 1 名爪牙")
        # 伪装:配版时选好(说书人指定 3 个不在场好角色,或自动抽取)
        if bluffs is None:
            self.bluffs = self._pick_bluffs(set(picked.values()))
        else:
            if len(bluffs) != 3 or len(set(bluffs)) != 3:
                raise ValueError("伪装需为 3 个不重复角色")
            for rid in bluffs:
                if rid not in self.roles:
                    raise ValueError(f"角色 {rid} 不属于当前板子")
                if self.roles[rid]["team"] not in self._bluff_teams():
                    raise ValueError("伪装必须是好角色(暗流涌动限镇民)")
                if rid in picked.values():
                    raise ValueError(f"伪装必须不在场:{rid} 已分配给座位")
            self.bluffs = list(bluffs)
        # 认知覆盖由说书人显式决定:fakes 给每个疯子/酒鬼座位指定看到的假身份;
        # 疯子还须指定「以为谁是爪牙」(不一定是真爪牙)和 3 个伪装(不一定是恶魔的真伪装)。
        # 假身份/假伪装允许与在场角色相同——认知覆盖不计算配板
        new_fakes: dict[int, str] = {}
        new_lun_minions: dict[int, list[int]] = {}
        new_lun_bluffs: dict[int, list[str]] = {}
        for item in fakes or []:
            seat, rid = item.get("seat"), item.get("role")
            if not isinstance(seat, int) or seat not in picked:
                raise ValueError(f"伪造身份的座位 {seat} 无效")
            real = picked[seat]
            if real not in FAKE_POOLS:
                raise ValueError(f"座位 {seat} 的角色没有认知覆盖")
            if rid not in self.roles or self.roles[rid]["team"] not in FAKE_POOLS[real]:
                raise ValueError(f"座位 {seat} 的伪造身份无效")
            new_fakes[seat] = rid
            if real == "lunatic":
                minions = item.get("minions") or []
                if (not isinstance(minions, list) or not minions
                        or any(not isinstance(m, int) or not 1 <= m <= self.player_count
                               or m == seat for m in minions)
                        or len(set(minions)) != len(minions)):
                    raise ValueError(f"座位 {seat} 的疯子须指定至少一个假爪牙座位(1~{self.player_count},不含自己)")
                bluffs = item.get("bluffs") or []
                if (len(bluffs) != 3 or len(set(bluffs)) != 3
                        or any(b not in self.roles or self.roles[b]["team"] not in self._bluff_teams()
                               for b in bluffs)):
                    raise ValueError(f"座位 {seat} 的疯子伪装须为 3 个不重复的好角色(允许与在场角色相同)")
                new_lun_minions[seat] = list(minions)
                new_lun_bluffs[seat] = list(bluffs)
        for seat, real in picked.items():
            if real in FAKE_POOLS and seat not in new_fakes:
                raise ValueError(f"座位 {seat} 的{self.roles[real]['name']}须指定看到的假身份")
        self.seat_fakes = new_fakes
        self.lunatic_minions = new_lun_minions
        self.lunatic_bluffs = new_lun_bluffs
        self.seat_roles = dict(picked)  # 身份挂在座位上,没人入座也可以先发
        for seat, player in seat_of.items():  # 已入座的玩家当场继承
            player.role_id = picked[seat]
        if len(seat_of) == self.player_count:
            self.status = "playing"  # 全员已入座 → 立即开局;否则等 sit() 补满自动开局
            self._begin_night()
        self.save()
        by_seat = sorted((p for p in self.players.values() if p.seat is not None),
                         key=lambda p: p.seat)  # 没入座的玩家(seat=None)不参与排序,否则 None 比较会 500
        return [p.storyteller(self.roles) for p in by_seat]

    def start_game(self) -> None:
        """说书人强制开局:人未齐也能进入游戏。

        前提是每个座位都已有身份(已入座玩家持有角色,或空座已预发)。
        开局后迟到的玩家只能坐空座,入座即继承该座预发身份。
        """
        if self.status == "playing":
            raise ValueError("本局已开始")
        missing = [seat for seat in range(1, self.player_count + 1)
                   if seat not in self.seat_roles
                   and (self.seats.get(seat) is None or self.seats[seat].role_id is None)]
        if missing:
            raise ValueError(f"还有 {len(missing)} 个座位没有身份(座位 {','.join(map(str, missing))}),先分配角色")
        self.status = "playing"
        self._begin_night()  # 第 1 夜开始
        self.save()

    # ---- 昼夜阶段与夜晚流程 ----

    def _bluff_teams(self) -> tuple[str, ...]:
        """伪装可取的好角色阵营:暗流涌动限镇民,其余脚本镇民+外来者。"""
        return (TOWNSFOLK,) if self.script_id == "trouble-brewing" else (TOWNSFOLK, OUTSIDER)

    def _pick_bluffs(self, present: set[str]) -> list[str]:
        """从不在场的好角色里随机抽三个伪装。"""
        pool = [r["id"] for r in self.roles.values()
                if r["team"] in self._bluff_teams() and r["id"] not in present]
        return random.sample(pool, min(3, len(pool)))

    def _begin_night(self) -> None:
        """进入夜晚:按本夜在场角色组装步骤表(酒鬼的假角色作为附加步骤)。"""
        if self.night_no == 1 and not self.bluffs:  # 兜底:老存档没伪装时第一夜补抽,后续夜不再重抽
            present = set(self.seat_roles.values()) | {p.role_id for p in self.players.values() if p.role_id}
            self.bluffs = self._pick_bluffs(present)
        kind = "first" if self.night_no == 1 else "other"
        sheet = NIGHT_ORDER[self.script_id][kind]
        # 在场角色 = 已入座玩家 + 空座预发身份(人未齐开局时,空座角色也排进夜晚)
        present = ({p.role_id for p in self.players.values() if p.role_id}
                   | set(self.seat_roles.values()))
        fake_by_role: dict[str, list[int]] = {}
        for seat, rid in self.seat_fakes.items():
            fake_by_role.setdefault(rid, []).append(seat)
        sheet_keys = {st["key"] for st in sheet}
        lunatic_seats = {l["seat"] for l in self._role_seats("lunatic")}
        # 疯子:官方顺序先恶魔后疯子——本夜有假恶魔步时由其覆盖唤醒,否则把疯子步挪到恶魔会面之后
        lunatic_covered = {s for s in lunatic_seats
                           if s in self.seat_fakes and self.seat_fakes[s] in sheet_keys}
        steps: list[dict] = []
        pending_lunatic: dict | None = None
        for st in sheet:
            key = st["key"]
            if key == "lunatic" and lunatic_seats:
                if lunatic_covered == lunatic_seats:
                    continue  # 疯子扮演假恶魔:附加步紧随恶魔步,不提前单独唤醒
                pending_lunatic = dict(st)  # 挪到恶魔会面之后再唤醒疯子
                continue
            if key in ("dusk", "dawn", "minioninfo", "demoninfo") or key in present:
                steps.append(dict(st))
            if key == "demoninfo" and pending_lunatic is not None:
                steps.append(pending_lunatic)
                pending_lunatic = None
            for seat in fake_by_role.get(key, []):  # 假身份步骤:紧随真实步骤,标注座位
                steps.append({**st, "fake_for": seat})
        if pending_lunatic is not None:  # 兜底:本夜无恶魔会面步时,疯子步放在末尾
            steps.append(pending_lunatic)
        # 旅行者夜晚行动:官方顺序中全部在黄昏阶段(检查闭眼之后),插在 dusk 步后面
        dusk_idx = next((i for i, st in enumerate(steps) if st["key"] == "dusk"), None)
        if dusk_idx is not None:
            inject = []
            for rid in TRAVELER_DUSK:
                holders = [t for t in self.travelers if t["role_id"] == rid and t["alive"]]
                if not holders:
                    continue
                if rid == "apprentice":
                    # 学徒:只在加入后的首个夜晚行动(夜里加入=当晚;白天加入=下一夜)
                    if not any(t["joined_no"] == self.night_no if t["joined_phase"] == "night"
                               else t["joined_no"] + 1 == self.night_no for t in holders):
                        continue
                r = TRAVELER_BY_ID[rid]
                inject.append({"key": rid, "name": f"🎒 {r['name']}", "hint": r["ability"],
                               "traveler": True})
            steps[dusk_idx + 1:dusk_idx + 1] = inject
        self.night_steps = steps
        self.night_idx = 0
        self.phase = "night"

    def night_goto(self, idx: int) -> None:
        if self.phase != "night":
            raise ValueError("现在是白天,没有夜晚步骤")
        if not 0 <= idx < len(self.night_steps):
            raise ValueError(f"步骤需在 0~{len(self.night_steps) - 1} 之间")
        self.night_idx = idx
        self.save()

    def night_next(self) -> None:
        if self.phase != "night":
            raise ValueError("现在是白天,不能推进夜晚")
        if self.night_idx + 1 < len(self.night_steps):
            self.night_idx += 1
        else:  # 走完最后一步(dawn)→ 天亮
            self._apply_night_kills()  # 恶魔刀人自动执行:夜里死,天亮才公开
            self.phase = "day"
            self.day_no += 1
            self.day_stage = "talk"  # 天亮先进入公聊私聊阶段,说书人宣布后才进提名
        self.save()

    def night_prev(self) -> None:
        if self.phase != "night" or self.night_idx <= 0:
            raise ValueError("已经在第一步,不能后退")
        self.night_idx -= 1
        self.save()

    def end_day(self) -> None:
        if self.phase != "day":
            raise ValueError("现在是夜晚,不能结束白天")
        self._end_day_execution()  # 白天结束:结算处决(最多票者死,平票无人死)
        self.night_no += 1
        self._begin_night()
        self.save()

    # ---- 夜晚刀人(瓦釜雷鸣手机操作,先只开放这一板) ----

    def submit_night_kill(self, player_id: str, seat: int) -> None:
        """恶魔手机选择刀杀目标(夜晚任意时刻可改,天亮自动执行);疯子同样可选(演戏,不生效)。"""
        if self.script_id != "wafu-leiming":
            raise ValueError("该板子暂未开放手机刀人")
        me = self.players[player_id]
        if me.seat is None:
            raise ValueError("你还没有入座")
        self.submit_night_kill_seat(me.seat, seat)

    def submit_night_kill_seat(self, seat: int, target: int) -> None:
        """说书人按座位代操作刀人(空座角色也可,便于测试人未齐开局)。"""
        if self.script_id != "wafu-leiming":
            raise ValueError("该板子暂未开放手机刀人")
        if self.phase != "night":
            raise ValueError("夜晚才能选择刀人")
        rid = self._seat_real_role(seat)
        team = self.roles[rid]["team"] if rid else None
        if rid is None or (team != DEMON and rid != "lunatic"):
            raise ValueError("该座位角色没有夜晚刀人能力")
        p = self.seats.get(seat)
        if p is not None and not p.alive:
            raise ValueError("死者不能行动")
        if not 1 <= target <= self.player_count or self._seat_real_role(target) is None:
            raise ValueError("目标需为有角色的座位")
        if not self._seat_alive(target):
            raise ValueError("目标需存活")
        entry = self.night_kills.setdefault(str(self.night_no), {})
        if rid == "lunatic":
            entry["lunatic_seat"] = target  # 疯子以为自己是恶魔:选择只演戏,天亮不执行
            entry["lunatic_by"] = seat
        else:
            entry["seat"] = target
            entry["by"] = seat
            entry["role"] = rid
        self.save()

    def _apply_night_kills(self) -> None:
        """天亮时执行恶魔刀人:died_day=夜号,与既有「夜里死天亮公开」规则一致。
        麻脸巫婆创造了恶魔 → 本夜死亡由说书人决定,跳过自动执行(说书人手动标记)。
        空座同样可被刀死(以座位级生死标记为准)。"""
        entry = self.night_kills.get(str(self.night_no))
        if not entry or entry.get("seat") is None:
            return
        if entry.get("arbitrary"):
            return
        seat = entry["seat"]
        victim = self.seats.get(seat)
        if victim is not None:
            if victim.alive:
                victim.alive = False
                victim.died_day = self.night_no
        elif seat in self.seat_roles and self.seat_alive.get(seat, True):
            self.seat_alive[seat] = False
            self.seat_dead_day[seat] = self.night_no

    # ---- 夜晚信息交互(瓦釜雷鸣手机操作) ----

    def submit_night_choice(self, player_id: str, targets: list[int], char: str | None = None) -> None:
        """占卜师/筑梦师等手机选人:说书人看到选择后电子回复结果。重新提交会清掉旧回复。
        麻脸巫婆:额外选变身后的角色(必须不在场,死亡角色也算在场)。"""
        if self.script_id != "wafu-leiming":
            raise ValueError("该板子暂未开放夜晚信息交互")
        me = self.players[player_id]
        if me.seat is None:
            raise ValueError("你还没有入座")
        self.submit_night_choice_seat(me.seat, targets, char)

    def submit_night_choice_seat(self, seat: int, targets: list[int], char: str | None = None) -> None:
        """说书人按座位代操作夜晚选人(空座角色也可,便于测试人未齐开局)。"""
        if self.script_id != "wafu-leiming":
            raise ValueError("该板子暂未开放夜晚信息交互")
        if self.phase != "night":
            raise ValueError("夜晚才能行动")
        rid = self._seat_real_role(seat)
        eff = self.seat_fakes.get(seat) if rid in FAKE_POOLS else rid  # 酒鬼用假身份行动(以为自己是占卜师)
        act = NIGHT_ACTIONS.get(eff)
        if act is None:
            raise ValueError("该座位角色没有夜晚选择行动")
        if act.get("info_first") and self.night_no == 1:
            raise ValueError("首个夜晚只得到信息,不能行动")
        p = self.seats.get(seat)
        if p is not None and not p.alive and not (rid == "ravenkeeper" and p.died_day == self.night_no):
            raise ValueError("死者不能行动")
        count = act["count"]
        if (not isinstance(targets, list) or len(targets) != count
                or any(not isinstance(t, int) or not 1 <= t <= self.player_count for t in targets)
                or len(set(targets)) != count):
            raise ValueError(f"需选择 {count} 名有效玩家")
        for t in targets:
            if self._seat_real_role(t) is None:
                raise ValueError(f"座位 {t} 没有角色")
        old = self.night_choices.get(str(self.night_no), {}).get(str(seat))
        entry = {"role": eff, "targets": sorted(targets), "reply": None}
        if old is not None and old.get("prev_target") is not None:
            entry["prev_target"] = old["prev_target"]  # 重提交换目标:记住旧目标以便解除其疯狂
        if act.get("char"):
            if not char or char not in self.roles:
                raise ValueError("变身后的角色必须是本板子角色")
            if act.get("good_char") and self.roles[char]["team"] not in (TOWNSFOLK, OUTSIDER):
                raise ValueError("疯狂宣称必须是善良角色")
            entry["char"] = char
        self.night_choices.setdefault(str(self.night_no), {})[str(seat)] = entry
        if act.get("char") and char in self.roles:
            if eff == "pithag":
                self._apply_pithag(seat)  # 自动转变(提交即生效);角色在场 → 静默无效
            elif eff == "cerenovus":
                self._apply_cerenovus(seat)  # 疯狂自动生效:被疯狂者手机被告知
        self.save()

    def _apply_pithag(self, seat: int) -> None:
        """自动应用麻脸巫婆的变身:角色在场(存活或死亡,含空座预发)→ 静默无效,麻脸巫婆自己不知道;
        生效则角色立即改变并告知玩家;创造恶魔 → 本夜死亡由说书人决定;
        新角色在本夜行动顺序中位于麻脸巫婆之后 → 注入其步骤,按轮次发动行动。"""
        entry = self.night_choices.get(str(self.night_no), {}).get(str(seat))
        if entry is None or entry.get("role") != "pithag" or entry.get("applied"):
            return
        char, target = entry["char"], entry["targets"][0]
        in_play = ({p.role_id for p in self.players.values() if p.role_id}
                   | set(self.seat_roles.values()))
        if char in in_play:
            entry["invalid"] = True  # 已在场:静默不生效(说书人可见,麻脸巫婆不知情)
            return
        if target not in self.seat_roles:
            entry["invalid"] = True
            return
        p = self.seats.get(target)  # 空座也可变身(只改预发身份,便于测试)
        entry["from"] = p.role_id if p is not None else self.seat_roles[target]
        if p is not None:
            p.role_id = char
        self.seat_roles[target] = char
        if p is not None:
            self.seat_role_changes[target] = char  # 玩家手机收到角色转变提示
        entry["applied"] = True
        if self.roles[char]["team"] == DEMON:
            # 创造恶魔:当晚死亡由说书人决定,天亮跳过自动刀人
            self.night_kills.setdefault(str(self.night_no), {})["arbitrary"] = True
        # 按行动轮次发动:新角色在本夜顺序中位于麻脸巫婆之后 → 紧跟其后注入步骤
        kind = "first" if self.night_no == 1 else "other"
        sheet = [st["key"] for st in NIGHT_ORDER[self.script_id][kind]]
        if char in sheet and "pithag" in sheet and sheet.index(char) > sheet.index("pithag"):
            pithag_i = next((i for i, st in enumerate(self.night_steps) if st["key"] == "pithag"), None)
            if pithag_i is not None and not any(st["key"] == char for st in self.night_steps):
                r = self.roles[char]
                self.night_steps.insert(pithag_i + 1, {"key": char, "name": r["name"],
                                                       "hint": r["ability"], "_pithag": True})

    def _apply_cerenovus(self, seat: int) -> None:
        """洗脑师疯狂自动生效:目标被疯狂(宣称自己是所选善良角色),手机即时通知;
        重新提交 → 旧目标解除、新目标生效(说书人可随时手动清除)。"""
        entry = self.night_choices.get(str(self.night_no), {}).get(str(seat))
        if entry is None or entry.get("role") != "cerenovus":
            return
        char, target = entry["char"], entry["targets"][0]
        prev = entry.get("prev_target")
        if prev is not None and prev != target:  # 改选:解除上一个目标的疯狂
            cur = set(self.seat_markers.get(prev, ()))
            cur.discard("mad")
            if cur:
                self.seat_markers[prev] = list(cur)
            else:
                self.seat_markers.pop(prev, None)
            self.mad_about.pop(prev, None)
        entry["prev_target"] = target
        cur = set(self.seat_markers.get(target, ()))
        cur.add("mad")
        self.seat_markers[target] = list(cur)
        self.mad_about[target] = char
        entry["applied"] = True
        entry.pop("invalid", None)

    def revert_pithag(self, seat: int) -> None:
        """说书人撤销已生效的麻脸巫婆变身(容错):恢复角色、移除注入步骤与「死亡由说书人决定」标记。"""
        entry = self.night_choices.get(str(self.night_no), {}).get(str(seat))
        if entry is None or not entry.get("applied"):
            raise ValueError("没有已生效的变身可撤销")
        char, target, prev = entry["char"], entry["targets"][0], entry.get("from")
        p = self.seats.get(target)
        if prev:
            if p is not None:
                p.role_id = prev
                self.seat_role_changes.pop(target, None)
            self.seat_roles[target] = prev
        self.night_steps = [st for st in self.night_steps
                            if not (st["key"] == char and st.get("_pithag"))]
        if self.roles[char]["team"] == DEMON:
            self.night_kills.get(str(self.night_no), {}).pop("arbitrary", None)
        entry["applied"] = False
        entry.pop("invalid", None)
        self.save()

    def reply_night_choice(self, seat: int, text: str, role: str | None = None) -> None:
        """说书人电子回复玩家夜里的选择(占卜师:有/无恶魔等);无选择也可直接发信息(教父首夜等)。
        空座(人未齐测试)同样可收回复。"""
        if self.phase != "night":
            raise ValueError("夜晚才能回复")
        if not 1 <= seat <= self.player_count or self._seat_real_role(seat) is None:
            raise ValueError("座位无效")
        entry = self.night_choices.setdefault(str(self.night_no), {}).get(str(seat))
        if entry is None:
            entry = {"role": role or "info", "targets": [], "reply": None}
            self.night_choices[str(self.night_no)][str(seat)] = entry
        entry["reply"] = (text or "").strip()[:100]
        self.save()

    # ---- 占卜师宿敌(红鲱鱼) ----

    def set_fortuneteller_red(self, seat: int | None) -> None:
        """占卜师宿敌:说书人私下标记一名善良玩家,占卜师查他总被当作恶魔(只有说书人知道)。"""
        present = ({p.role_id for p in self.players.values() if p.role_id}
                   | set(self.seat_roles.values()))
        if "fortuneteller" not in present:
            raise ValueError("本局没有占卜师,不需要标记宿敌")
        if seat is None:
            self.fortuneteller_red = None
            self.save()
            return
        if not 1 <= seat <= self.player_count:
            raise ValueError("座位无效")
        rid = self._seat_real_role(seat)
        if not rid:
            raise ValueError("该座位没有角色")
        team = self.roles[rid]["team"]
        if team not in (TOWNSFOLK, OUTSIDER):
            raise ValueError("宿敌必须是善良玩家")
        if rid == "fortuneteller":
            raise ValueError("宿敌不能是占卜师本人")
        self.fortuneteller_red = seat
        self.save()

    def set_day_stage(self, stage: str) -> None:
        """说书人切换白天子阶段:talk 公聊私聊 / nom 提名阶段(控节奏)。提名进行中不能退回公聊。"""
        if self.phase != "day":
            raise ValueError("现在是夜晚,不能切换白天阶段")
        if stage not in ("talk", "nom"):
            raise ValueError("白天阶段只能是 talk/nom")
        if stage == "talk" and self.current:
            raise ValueError("有进行中的提名,先结票才能回到公聊私聊")
        self.day_stage = stage
        self.save()

    # ---- 提名 / 投票 / 处决 ----

    def start_nomination(self, nominator: int | str, nominee: int | str) -> None:
        if self.phase != "day":
            raise ValueError("白天才能发起提名")
        if self.day_stage != "nom":
            raise ValueError("还没到提名阶段,等说书人宣布")
        if self.current:
            raise ValueError("已有进行中的提名,先宣布结果")
        np_, nt_ = self._target(nominator)
        if np_ is None and nt_ is None:
            if isinstance(nominator, int) and self._seat_real_role(nominator) is not None:
                if not self._seat_alive(nominator):
                    raise ValueError("死亡玩家不能发起提名")
            else:
                raise ValueError("提名者需已入座、是旅行者,或是有预发角色的空座")
        if nt_ is not None and not nt_["alive"]:
            raise ValueError("死亡旅行者不能发起提名")
        if np_ is not None and not np_.alive:
            raise ValueError("死亡玩家不能发起提名")
        np2, nt2 = self._target(nominee)
        if np2 is None and nt2 is None:
            if not (isinstance(nominee, int) and self._seat_real_role(nominee) is not None):
                raise ValueError("被提名者需已入座、是旅行者,或是有预发角色的空座")
        if nt2 is not None and nt2["exiled"]:
            raise ValueError("已流放的旅行者已离开小镇,不能再被提名")
        # 提名规则:每人每天只能发起一次提名、只能被提名一次;死者不能发起但可以被提名;可以提名自己
        todays = [n for n in self.nominations if n["day"] == self.day_no]
        if any(n["nominator"] == nominator for n in todays):
            raise ValueError("今天已发起过提名,每天只能发起一次")
        if any(n["nominee"] == nominee for n in todays):
            raise ValueError("今天已被提名过,每天只能被提名一次")
        self.current = {"nominator": nominator, "nominee": nominee, "votes": []}
        self.save()

    def toggle_vote(self, target: int | str) -> None:
        if not self.current:
            raise ValueError("没有进行中的提名")
        player, traveler = self._target(target)
        # 空座角色同样可投票(以说书人标记的生死为准,而不是是否在座)
        if player is None and traveler is None:
            if not (isinstance(target, int) and self._seat_real_role(target) is not None):
                raise ValueError("投票者需已入座、是旅行者,或是有预发角色的空座")
        votes = self.current["votes"]
        if target in votes:
            votes.remove(target)
            if target in self.current_dead_votes:  # 死票是本次提名交出的(尚未结算):取消举手归还死票
                self.current_dead_votes.discard(target)
                if player is not None:
                    player.dead_vote_used = False
                elif traveler is not None:
                    traveler["dead_vote_used"] = False
                else:
                    self.seat_dead_vote.pop(target, None)
        else:
            alive = (player.alive if player is not None
                     else traveler["alive"] if traveler is not None
                     else self._seat_alive(target))
            if not alive:
                used = (player.dead_vote_used if player is not None
                        else traveler["dead_vote_used"] if traveler is not None
                        else self.seat_dead_vote.get(target, False))
                if used:
                    raise ValueError("该玩家已交出过死亡票,每名死者整局只能投一票")
                if player is not None:
                    player.dead_vote_used = True
                elif traveler is not None:
                    traveler["dead_vote_used"] = True
                else:
                    self.seat_dead_vote[target] = True
                self.current_dead_votes.add(target)
            votes.append(target)
            votes.sort(key=lambda v: (isinstance(v, str), v))  # 座位号在前,旅行者 id 在后
        self.save()

    def player_nominate(self, player_id: str, nominee: int | str) -> None:
        """玩家手机发起提名:提名者必须是本人(座位或旅行者),其余校验复用 start_nomination。"""
        me = self.players[player_id]
        t = self.traveler_of(player_id)
        if t is not None:
            nominator: int | str = t["id"]
        else:
            if me.seat is None:
                raise ValueError("你还没有入座")
            nominator = me.seat
        self.start_nomination(nominator, nominee)

    def player_vote(self, player_id: str) -> None:
        """玩家手机举手/放下:只能投自己(座位或旅行者),死票规则与说书人代记一致。"""
        me = self.players[player_id]
        t = self.traveler_of(player_id)
        if t is not None:
            target: int | str = t["id"]
        else:
            if me.seat is None:
                raise ValueError("你还没有入座")
            target = me.seat
        self.toggle_vote(target)

    def resolve_nomination(self, passed: bool) -> None:
        """结票:通过则被提名者上处决台(待处决);旅行者通过则当场流放(官方:流放不等到天黑)。
        处决要等天黑时统一结算:当天待处决者中票数最多者被处决。"""
        if not self.current:
            raise ValueError("没有进行中的提名")
        rec = {**self.current, "day": self.day_no, "passed": passed, "executed": False}
        self.nominations.append(rec)
        self.current_dead_votes.clear()  # 结算后死票不可再收回
        if passed:
            player, traveler = self._target(self.current["nominee"])
            if traveler is not None:
                traveler["alive"] = False
                traveler["exiled"] = True  # 旅行者被投票通过 = 流放,当场生效
                traveler["died_day"] = self.day_no
                rec["executed"] = True
        self.current = None
        self.save()

    def _end_day_execution(self) -> None:
        """天黑时结算处决:今天通过(待处决)的座位提名中票数最多者被处决;平票则无人被处决。"""
        todays = [n for n in self.nominations
                  if n["day"] == self.day_no and n["passed"] and isinstance(n["nominee"], int)]
        if not todays:
            return
        max_votes = max(len(n["votes"]) for n in todays)
        winners = [n for n in todays if len(n["votes"]) == max_votes]
        if len(winners) != 1:
            return  # 平票:无人被处决
        nominee = winners[0]["nominee"]
        player = self.seats.get(nominee)
        if player is not None:
            player.alive = False
            player.died_day = self.day_no  # 白天结束时的处决:当天当场公开
        elif nominee in self.seat_roles and self.seat_alive.get(nominee, True):
            self.seat_alive[nominee] = False  # 空座同样可被处决
            self.seat_dead_day[nominee] = self.day_no
        winners[0]["executed"] = True

    # ---- 状态操作 ----

    def toggle_alive(self, player_id: str) -> None:
        if player_id in self.players:
            p = self.players[player_id]
            p.alive = not p.alive
            if p.alive:  # 复活重置死票:再次死亡会获得新的死票
                p.dead_vote_used = False
                self.current_dead_votes.discard(p.seat)
            # 死亡公开的天数:夜里死=天亮那天(night_no),白天死=当天(day_no),复活清空
            p.died_day = (self.night_no if self.phase == "night" else self.day_no) if not p.alive else None
            self.save()

    def toggle_seat_alive(self, seat: int) -> None:
        """说书人按座位标记生死(空座同样可以):以说书人标记为准,而不是是否在座。"""
        if not 1 <= seat <= self.player_count or self._seat_real_role(seat) is None:
            raise ValueError("该座位没有角色")
        p = self.seats.get(seat)
        if p is not None:
            self.toggle_alive(p.id)
            return
        cur = self.seat_alive.get(seat, True)
        if cur:  # 标记死亡
            self.seat_alive[seat] = False
            self.seat_dead_day[seat] = self.day_no if self.phase == "day" else self.night_no
        else:  # 复活
            self.seat_alive.pop(seat, None)
            self.seat_dead_day.pop(seat, None)
            self.seat_dead_vote.pop(seat, None)
        self.save()

    def set_fake(self, seat: int, role_id: str | None,
                 minions: list[int] | None = None, bluffs: list[str] | None = None) -> None:
        """认知覆盖:标记该座位玩家看到的假角色(酒鬼看到镇民/疯子以为自己是恶魔)。
        疯子还带假爪牙座位与 3 个伪装(说书人选,不一定是真的)。None 清除全部标记。"""
        if not 1 <= seat <= self.player_count:
            raise ValueError(f"座位需在 1~{self.player_count} 之间")
        p = self.seats.get(seat)
        real = p.role_id if p is not None else self.seat_roles.get(seat)
        if role_id is not None:
            if real not in FAKE_POOLS:
                raise ValueError("该座位的角色没有认知覆盖(仅酒鬼/疯子)")
            if role_id not in self.roles or self.roles[role_id]["team"] not in FAKE_POOLS[real]:
                raise ValueError("伪造身份需属于该角色允许的阵营")
        if role_id is None:
            self.seat_fakes.pop(seat, None)
            self.lunatic_minions.pop(seat, None)
            self.lunatic_bluffs.pop(seat, None)
        else:
            self.seat_fakes[seat] = role_id
            # 疯子额外信息按增量更新:不给该字段就保留已存值(夜晚逐项设置友好),给了就校验替换
            if real == "lunatic":
                if minions is not None:
                    if (not minions or any(not isinstance(m, int) or not 1 <= m <= self.player_count
                                           or m == seat for m in minions)
                            or len(set(minions)) != len(minions)):
                        raise ValueError("疯子须指定至少一个假爪牙座位(不含自己)")
                    self.lunatic_minions[seat] = list(minions)
                if bluffs is not None:
                    if (len(bluffs) != 3 or len(set(bluffs)) != 3
                            or any(b not in self.roles or self.roles[b]["team"] not in self._bluff_teams()
                                   for b in bluffs)):
                        raise ValueError("疯子的伪装须为 3 个不重复的好角色(允许与在场角色相同)")
                    self.lunatic_bluffs[seat] = list(bluffs)
        if self.phase == "night":
            self._begin_night()  # 夜晚中改认知覆盖 → 重算步骤表(假角色步骤随之增减)
        self.save()

    def set_marker(self, seat: int, marker: str, on: bool, role: str | None = None,
                   team: str | None = None, about: str | None = None) -> None:
        """说书人标记:该座位玩家中毒/醉酒/疯狂/角色转变/阵营转变(角色/阵营转变会告知玩家本人)。
        角色转变需附上「变成哪个角色」;阵营转变需附上「新阵营 good/evil」;
        疯狂需附上「疯狂内容」(善良角色,被疯狂者会被告知),均由说书人选择。"""
        if not 1 <= seat <= self.player_count:
            raise ValueError(f"座位需在 1~{self.player_count} 之间")
        if marker not in MARKERS:
            raise ValueError(f"未知标记 {marker}")
        if marker == "role-change":  # 带数据的标记单独存,角标显示新角色
            if on:
                if role is None or role not in self.roles:
                    raise ValueError("角色转变需选择要变成的角色")
                self.seat_role_changes[seat] = role
            else:
                self.seat_role_changes.pop(seat, None)
            self.save()
            return
        if marker == "team-change":  # 带数据的标记:说书人选新阵营,角标/玩家提示按阵营配色
            if on:
                if team not in ("good", "evil"):
                    raise ValueError("阵营转变需选择新阵营(善良/邪恶)")
                self.seat_team_changes[seat] = team
            else:
                self.seat_team_changes.pop(seat, None)
            self.save()
            return
        if marker == "mad":  # 疯狂带内容:被疯狂者疯狂宣称自己是某善良角色(手机会被告知)
            if on:
                if about is None or about not in self.roles:
                    raise ValueError("疯狂标记需选择疯狂内容(角色)")
                if self.roles[about]["team"] not in (TOWNSFOLK, OUTSIDER):
                    raise ValueError("疯狂宣称必须是善良角色")
                self.mad_about[seat] = about
            else:
                self.mad_about.pop(seat, None)
        cur = set(self.seat_markers.get(seat, ()))
        if on:
            cur.add(marker)
        else:
            cur.discard(marker)
        if cur:
            self.seat_markers[seat] = sorted(cur)
        else:
            self.seat_markers.pop(seat, None)
        self.save()

    # ---- 视图 ----

    def _team_seats(self, team: str) -> list[dict]:
        """某阵营的座位名单(在座或空座预发都列出):会面步骤指向恶魔/爪牙用。"""
        out = []
        for i in range(1, self.player_count + 1):
            p = self.seats.get(i)
            rid = p.role_id if p is not None else None
            if rid is None:
                rid = self.seat_roles.get(i)
            if rid and self.roles[rid]["team"] == team:
                out.append({"seat": i, "name": p.name if p is not None else None,
                            "role": self.roles[rid]})
        return out

    def _role_seats(self, rid: str) -> list[dict]:
        """某角色的座位名单(在座或空座预发都列出):疯子等特定角色指向用。"""
        out = []
        for i in range(1, self.player_count + 1):
            p = self.seats.get(i)
            r = p.role_id if p is not None else None
            if r is None:
                r = self.seat_roles.get(i)
            if r == rid:
                out.append({"seat": i, "name": p.name if p is not None else None})
        return out

    def _seat_real_role(self, seat: int) -> str | None:
        """座位的真实角色 id(在座玩家持有,或空座预发)。"""
        p = self.seats.get(seat)
        return p.role_id if p is not None else self.seat_roles.get(seat)

    def _seat_alive(self, seat: int) -> bool:
        """座位生死(以说书人标记为准,而不是是否在座):已入座看玩家,空座看座位级标记。"""
        p = self.seats.get(seat)
        if p is not None:
            return p.alive
        return self.seat_alive.get(seat, True)

    def _seat_slots(self, st_view: bool, my_id: str | None = None) -> list[dict]:
        seat_of = self.seats
        slots = []
        for i in range(1, self.player_count + 1):
            p = seat_of.get(i)
            if p is None:
                slot = {"seat": i, "player": None}
                if st_view and i in self.seat_roles:  # 空座上的预发身份,说书人可见
                    slot["assigned_role"] = self.roles[self.seat_roles[i]]
                if st_view and i in self.seat_roles:  # 空座生死:以说书人标记为准
                    slot["alive"] = self.seat_alive.get(i, True)
                if st_view and i in self.seat_fakes:  # 空座也能先标记认知覆盖
                    slot["fake_role"] = self.roles[self.seat_fakes[i]]
                if st_view and i in self.seat_markers:  # 空座同样挂状态标记(测试/控制)
                    slot["markers"] = self.seat_markers[i]
                if st_view and i in self.mad_about:  # 空座的疯狂内容
                    slot["mad_about"] = self.roles[self.mad_about[i]]
                if st_view and i in self.seat_role_changes:  # 空座也能标记角色转变
                    slot["role_change"] = self.roles[self.seat_role_changes[i]]
                if st_view and i in self.seat_team_changes:  # 空座也能标记阵营转变
                    slot["team_change"] = self.seat_team_changes[i]
                slots.append(slot)
                continue
            entry = p.storyteller(self.roles) if st_view else p.public()
            slot = {"seat": i, "player": entry}
            # 夜里死的人天亮才公开:夜晚阶段对所有玩家(含死者本人)伪装成还活着——
            # 玩家手机常扣在桌面上,座位骷髅会提前暴露死者;死者夜里由说书人当面告知
            if (not st_view and self.phase == "night" and not p.alive
                    and p.died_day == self.night_no):
                entry["alive"] = True
            if not p.alive and not p.dead_vote_used:  # 死票还没交出:骷髅旁 🗳 常驻(公开信息)
                slot["dead_vote_left"] = True
            if st_view and i in self.seat_fakes:  # 认知覆盖标记,说书人可见
                slot["fake_role"] = self.roles[self.seat_fakes[i]]
            if st_view and i in self.seat_markers:  # 状态标记,仅说书人可见
                slot["markers"] = self.seat_markers[i]
            if st_view and i in self.mad_about:  # 疯狂内容:疯狂宣称的角色,仅说书人可见
                slot["mad_about"] = self.roles[self.mad_about[i]]
            if st_view and i in self.seat_role_changes:  # 角色转变:变成哪个角色,说书人可见
                slot["role_change"] = self.roles[self.seat_role_changes[i]]
            if st_view and i in self.seat_team_changes:  # 阵营转变:新阵营,说书人可见
                slot["team_change"] = self.seat_team_changes[i]
            if my_id is not None:  # is_me 属于座位槽位层,不属于 player
                slot["is_me"] = p.id == my_id
            slots.append(slot)
        return slots

    def _public_progress(self) -> dict:
        """白天/夜晚进度(玩家与说书人都可见):含白天子阶段(公聊私聊/提名)。"""
        return {"phase": self.phase, "night_no": self.night_no, "day_no": self.day_no,
                "day_stage": self.day_stage}

    def _step_reached(self, key: str) -> bool:
        """夜晚是否已推进到 key 步骤(信息一旦给出不可收回,之后一直可见)。"""
        if self.status != "playing":
            return False
        if self.night_no > 1 or self.phase == "day":
            return True  # 第 2 夜起 / 白天:首夜会面早已发生
        return any(s["key"] == key for s in self.night_steps[:self.night_idx + 1])

    def player_view(self, player_id: str) -> dict:
        me = self.players[player_id]
        fake_id = self.seat_fakes.get(me.seat) if me.seat is not None else None
        started = self.status == "playing"
        me_traveler = self.traveler_of(player_id)  # 旅行者:角色/阵营存在旅行者槽位,不在 me.role_id
        view = {
            "status": self.status,
            "script": SCRIPTS[self.script_id]["name"],
            "player_count": self.player_count,
            # 官方配比(公开信息)。实际调整(男爵 +2 外来者等)绝不告知玩家
            "composition": list(COMPOSITION[self.player_count]),
            # 哨兵在场(公开,方向保密):玩家只知外来者可能 +1 或 −1
            "sentinel": self.sentinel != 0,
            **self._public_progress(),
            # 提名/投票是公开信息,实时推给玩家(举手、票型、处决)
            "nominations": self.nominations,
            "current": self.current,
            # 开局前不揭示身份:说书人开始游戏玩家才拿到角色(旅行者的角色等说书人指派)
            "me": me.public(),
            "me_wish": me.wish,  # 自己的许愿(仅本人与说书人可见)
            # 旅行者公开信息:谁加入了、什么角色(官方要求宣告),但阵营保密
            "travelers_public": [{"id": t["id"], "name": t["name"], "alive": t["alive"],
                                  "exiled": t["exiled"],
                                  "role": TRAVELER_BY_ID[t["role_id"]] if t["role_id"] else None}
                                 for t in self.travelers],
            "room_code": self.room_code,  # 玩家卡显示当前房间号
            "seats": self._seat_slots(st_view=False, my_id=player_id),
        }
        if me_traveler is not None:
            # 旅行者条目(不含 player_id)+ 已指派角色 + 阵营(官方:旅行者本人知道自己的阵营)
            view["traveler"] = {k: v for k, v in me_traveler.items() if k != "player_id"}
            if me_traveler["role_id"]:
                view["traveler"]["role"] = TRAVELER_BY_ID[me_traveler["role_id"]]
                view["me"]["role"] = TRAVELER_BY_ID[me_traveler["role_id"]]
        elif started:
            view["me"] = me.private(self.roles, fake_id)
        if not started:
            return view
        # 夜里死的人天亮才公开:死者本人的卡夜里也先不显示死亡(手机在桌上会被旁人看到骷髅/死亡提示)
        if (self.phase == "night" and me.seat is not None and not me.alive
                and me.died_day == self.night_no):
            view["me"]["alive"] = True
        if (me_traveler is not None and self.phase == "night" and not me_traveler["alive"]
                and me_traveler["died_day"] == self.night_no):
            view["traveler"]["alive"] = True  # 旅行者夜里死:本人卡同样天亮前不显示
        # 公开的死亡名单(按天排序):夜里死的人天亮才进名单;前端按天分组换行显示
        deaths = []
        for p in self.players.values():
            if p.seat is None or p.alive or p.died_day is None:
                continue
            if self.phase == "night" and p.died_day == self.night_no:
                continue  # 今夜刚死:天亮才公开
            deaths.append({"seat": p.seat, "name": p.name, "day": p.died_day})
        for t in self.travelers:
            if t["alive"] or t["died_day"] is None:
                continue
            if self.phase == "night" and t["died_day"] == self.night_no:
                continue  # 今夜刚死:天亮才公开
            deaths.append({"seat": t["id"], "name": t["name"], "day": t["died_day"],
                           "exiled": t["exiled"]})
        for i in range(1, self.player_count + 1):  # 空座死亡同样进名单(以说书人标记为准)
            if i in self.seats or i not in self.seat_roles:
                continue
            if self.seat_alive.get(i, True) or i not in self.seat_dead_day:
                continue
            if self.phase == "night" and self.seat_dead_day[i] == self.night_no:
                continue
            deaths.append({"seat": i, "name": self.roles[self.seat_roles[i]]["name"],
                           "day": self.seat_dead_day[i], "empty": True})
        deaths.sort(key=lambda d: (d["day"], str(d["seat"])))
        view["deaths"] = deaths
        # 邪恶旅行者:加入时由说书人告知恶魔是谁(官方规则,爪牙不告知)
        if me_traveler is not None and me_traveler["align"] == "evil":
            view["demon_seats"] = [{"seat": d["seat"], "name": d["name"]}
                                   for d in self._team_seats(DEMON)]
        if me_traveler is not None:
            return view  # 旅行者没有座位,后面全是座位玩家的会面/转变逻辑
        # 夜晚唤醒(瓦釜雷鸣手机交互,先只开放这一板):ST 走到对应步骤时,该玩家手机点亮
        if (self.script_id == "wafu-leiming" and self.phase == "night"
                and me.seat is not None and self.night_steps):
            cur = self.night_steps[self.night_idx]
            real_rid = me.role_id
            real_team = self.roles[real_rid]["team"] if real_rid else None
            wake = None
            if me.alive:
                if real_team == DEMON and cur["key"] == real_rid:
                    wake = {"action": "kill"}
                elif real_rid == "lunatic" and (cur["key"] == "lunatic" or cur.get("fake_for") == me.seat):
                    wake = {"action": "kill", "lunatic": True}  # 疯子以为自己是恶魔,演戏选择
                elif (real_rid in NIGHT_ACTIONS and cur["key"] == real_rid
                      and not (NIGHT_ACTIONS[real_rid].get("info_first") and self.night_no == 1)):
                    wake = {"action": "pick", "count": NIGHT_ACTIONS[real_rid]["count"]}
                    if NIGHT_ACTIONS[real_rid].get("grimoire"):
                        wake["grimoire"] = True  # 寡妇首夜:手机查看魔典(仅此夜、仅此步)
                    if NIGHT_ACTIONS[real_rid].get("char"):
                        # 麻脸巫婆:全角色池(不知道谁在场);洗脑师:只给善良角色(疯狂宣称)
                        pool = [r for r in self.roles.values()]
                        if NIGHT_ACTIONS[real_rid].get("good_char"):
                            pool = [r for r in pool if r["team"] in (TOWNSFOLK, OUTSIDER)]
                        wake["char"] = True
                        wake["chars"] = [{"id": r["id"], "name": r["name"], "team": r["team"]}
                                         for r in pool]
                elif (real_rid in FAKE_POOLS and cur.get("fake_for") == me.seat
                      and cur["key"] in NIGHT_ACTIONS):
                    wake = {"action": "pick", "count": NIGHT_ACTIONS[cur["key"]]["count"]}  # 酒鬼假身份行动
            elif real_rid == "ravenkeeper" and me.died_day == self.night_no and cur["key"] == "ravenkeeper":
                wake = {"action": "pick", "count": 1}  # 守鸦人死于今夜:被唤醒指认
            if wake is not None:
                if wake["action"] == "kill":
                    wake["targets"] = [s for s in self.seats if self.seats[s].alive]
                    entry = self.night_kills.get(str(self.night_no))
                    if entry:
                        chosen = entry.get("lunatic_seat") if real_rid == "lunatic" else entry.get("seat")
                        if chosen is not None:
                            view["my_kill"] = chosen
                else:
                    wake["targets"] = sorted(self.seats)  # 选人交互:所有入座玩家可选(含死者)
                view["night_wake"] = wake
                if wake.get("grimoire"):
                    # 寡妇首夜查看魔典:全部座位的真实角色与旅行者(仅此夜、仅此步,睡下后不可再看)
                    view["grimoire"] = {
                        "seats": [{"seat": s,
                                   "name": p.name if (p := self.seats.get(s)) else None,
                                   "alive": p.alive if (p := self.seats.get(s)) else None,
                                   "role": self.roles[self.seat_roles[s]] if s in self.seat_roles else None}
                                  for s in range(1, self.player_count + 1)],
                        "travelers": [{"id": t["id"], "name": t["name"], "alive": t["alive"],
                                       "align": t["align"],
                                       "role": TRAVELER_BY_ID[t["role_id"]] if t["role_id"] else None}
                                      for t in self.travelers],
                    }
            # 自己的夜晚选择与说书人回复(夜里随时可见)
            choice = self.night_choices.get(str(self.night_no), {}).get(str(me.seat))
            if choice is not None:
                view["night_choice"] = choice
            # 恶魔得知疯子刀了谁(官方:恶魔知道疯子是谁,也知道他每夜的选择)
            entry = self.night_kills.get(str(self.night_no))
            if real_team == DEMON and entry and entry.get("lunatic_seat") is not None:
                view["lunatic_kill"] = entry["lunatic_seat"]
        team = self.roles[me.role_id]["team"] if me.role_id else None
        # 角色转变/阵营转变:必须告诉玩家本人(手机卡显示提醒),其他标记仅说书人可见
        if me.seat is not None:
            if me.seat in self.seat_role_changes:
                view["role_changed"] = self.roles[self.seat_role_changes[me.seat]]
            if me.seat in self.seat_team_changes:
                view["team_changed"] = self.seat_team_changes[me.seat]
            if me.seat in self.mad_about:
                # 疯狂通知:被疯狂者必须被告知(疯狂宣称自己是该角色,直到说书人解除,否则可能被处决)
                view["my_mad"] = {"role": self.roles[self.mad_about[me.seat]]}
        lunatic_seats = self._role_seats("lunatic")  # 真疯子:恶魔与爪牙都须知道他是谁
        # 爪牙会面:所有爪牙同时醒来——知道恶魔是谁、谁是疯子,也彼此看见对方(官方规则)
        if team == MINION and self._step_reached("minioninfo"):
            view["demon_seats"] = [{"seat": d["seat"], "name": d["name"]}
                                   for d in self._team_seats(DEMON)]
            view["minion_seats"] = [{"seat": m["seat"], "name": m["name"]}
                                    for m in self._team_seats(MINION)]
            if lunatic_seats:
                view["lunatic_seats"] = [{"seat": l["seat"], "name": l["name"]} for l in lunatic_seats]
        # 恶魔会面:爪牙是谁 + 三个伪装,推进到该步骤才揭晓(按真实身份判断,酒鬼假镇民不触发)
        if team == DEMON and self._step_reached("demoninfo"):
            view["minion_seats"] = [{"seat": m["seat"], "name": m["name"]}
                                    for m in self._team_seats(MINION)]
            if lunatic_seats:
                view["lunatic_seats"] = [{"seat": l["seat"], "name": l["name"]} for l in lunatic_seats]
            if self.bluffs:
                view["bluffs"] = [self.roles[rid] for rid in self.bluffs]
        # 疯子自己:以为自己是恶魔——爪牙与伪装都是说书人选的(不一定是真的),疯子步骤/爪牙会面推进后揭晓
        if me.role_id == "lunatic" and (self._step_reached("lunatic") or self._step_reached("minioninfo")):
            fakes = self.lunatic_minions.get(me.seat, [])
            bluffs = self.lunatic_bluffs.get(me.seat, [])
            if fakes:
                view["minion_seats"] = [{"seat": s, "name": self.seats[s].name if s in self.seats else None}
                                        for s in fakes]
            if bluffs:
                view["bluffs"] = [self.roles[rid] for rid in bluffs]
        return view

    def storyteller_view(self) -> dict:
        # 处决门槛:存活玩家(不含旅行者)的一半及以上,向上取整;空座同样按说书人标记的生死计
        seated_alive = sum(1 for p in self.players.values() if p.seat is not None and p.alive)
        alive_count = seated_alive + sum(
            1 for i in range(1, self.player_count + 1)
            if i not in self.seats and i in self.seat_roles and self.seat_alive.get(i, True))
        total_players = sum(1 for p in self.players.values() if p.seat is not None) + len(self.travelers)
        return {
            "status": self.status,
            "script": self.script_id,
            "player_count": self.player_count,
            "scripts": [{"id": sid, "name": s["name"], "en": s["en"],
                         "min": s.get("min_players", 5)}
                        for sid, s in SCRIPTS.items()],
            # 手动发身份用:当前板子的角色表 + 基础配比 + 调整角色
            "roles": SCRIPTS[self.script_id]["roles"],
            "composition": list(COMPOSITION[self.player_count]),
            "adjust_roles": {rid: list(ROLE_ADJUSTMENTS[rid])
                             for rid in SCRIPT_ADJUST_ROLES.get(self.script_id, ())},
            "seat_roles": {str(seat): rid for seat, rid in self.seat_roles.items()},
            "seats": self._seat_slots(st_view=True),
            **self._public_progress(),
            "night": {"steps": self.night_steps, "idx": self.night_idx},
            "nominations": self.nominations,
            "current": self.current,
            "alive_count": alive_count,
            "quorum": (alive_count + 1) // 2,  # 处决所需票数:存活玩家(不含旅行者)一半及以上
            # 旅行者:流放票数 = 全体玩家(含死者)总数的一半;旅行者不算配板,加入/流放不限时刻
            "travelers": self.travelers,
            "traveler_roles": TRAVELERS,
            "traveler_recommended": TRAVELER_RECOMMENDED.get(self.script_id, None),  # None=社区板子,全部可选
            "total_players": total_players,
            "exile_quorum": (total_players + 1) // 2,
            # 人未齐开局:每个座位都有身份(在座持有或空座预发)即可强制开始
            "can_start": self.status == "lobby" and all(
                (self.seats.get(i) is not None and self.seats[i].role_id)
                or i in self.seat_roles for i in range(1, self.player_count + 1)),
            "bluffs": [self.roles[rid] for rid in self.bluffs],  # 恶魔的三个伪装(说书人可见)
            "fake_pools": FAKE_POOLS,  # 认知覆盖类角色 → 假身份可取阵营(手动面板渲染选择器用)
            "sentinel": self.sentinel,  # 哨兵:+1/−1/2(不变)/0(关),说书人可见
            # 入夜会面:告诉爪牙谁是恶魔、告诉恶魔谁是爪牙(空座预发也列出)
            "demon_seats": self._team_seats(DEMON),
            "minion_seats": self._team_seats(MINION),
            "lunatic_seats": self._role_seats("lunatic"),  # 真疯子座位:恶魔/爪牙会面时须一并指认
            "lunatic_minions": {str(s): ms for s, ms in self.lunatic_minions.items()},  # 疯子以为的爪牙
            "lunatic_bluffs": {str(s): [self.roles[rid] for rid in bs]
                               for s, bs in self.lunatic_bluffs.items()},  # 疯子的伪装(说书人选,不一定是真的)
            # 认知覆盖待定:发牌后说书人尚未选定假身份的座位(玩家卡先别给看)
            "fakes_pending": [{"seat": i, "role": self.roles[rr]}
                              for i in range(1, self.player_count + 1)
                              if (rr := self._seat_real_role(i)) in FAKE_POOLS and i not in self.seat_fakes],
            "saved_at": self.saved_at,
            "room_code": self.room_code,  # 房间号:说书人可改,玩家加入须匹配
            "night_kills": self.night_kills,  # 夜晚刀人:恶魔/疯子的手机选择(说书人可见)
            "night_choices": self.night_choices,  # 夜晚信息交互:各座位选择与说书人回复
            "night_actions": NIGHT_ACTIONS,  # 夜晚行动配置(前端代操作面板用)
            "fortuneteller_red": self.fortuneteller_red,  # 占卜师宿敌(红鲱鱼):只有说书人知道
            # 已加入的玩家(含未入座):许愿仅说书人可见,配板/手动发身份时参考
            "players": [{"id": p.id, "name": p.name, "seat": p.seat, "alive": p.alive,
                         "wish": p.wish} for p in self.players.values()],
        }
