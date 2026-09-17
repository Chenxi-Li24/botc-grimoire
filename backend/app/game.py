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

SAVE_PATH = Path(__file__).resolve().parent.parent / "data" / "game.json"

MARKERS = ("poisoned", "drunk", "mad")  # 说书人标记:中毒/醉酒/疯狂
MARKER_LABELS = {"poisoned": "中毒", "drunk": "醉酒", "mad": "疯狂"}


@dataclass
class Player:
    id: str
    name: str
    seat: int | None = None
    role_id: str | None = None
    alive: bool = True

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
        self.seat_fakes: dict[int, str] = {}  # 认知覆盖:座位号 → 玩家看到的假角色 id(酒鬼)
        self.seat_markers: dict[int, list] = {}  # 状态标记:座位号 → [poisoned/drunk/mad]
        self.phase: str | None = None  # None(大厅)| "night" | "day"
        self.night_no: int = 1  # 当前是第几夜(1 起)
        self.day_no: int = 0  # 当前是第几天(第一次天亮置 1)
        self.night_steps: list[dict] = []  # 本夜步骤 [{key,name,hint,fake_for?}]
        self.night_idx: int = 0  # 当前走到第几步
        self.nominations: list[dict] = []  # 提名历史 [{day,nominator,nominee,votes,executed}]
        self.current: dict | None = None  # 进行中的提名 {nominator,nominee,votes}
        self.bluffs: list[str] = []  # 恶魔的三个伪装:不在场的好角色 id(开局时抽取)
        self.sentinel: int = 0  # 哨兵(神职角色):0=关 / +1 / -1 / 2=在场但不调整
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
                              "role_id": p.role_id, "alive": p.alive}
                        for pid, p in self.players.items()},
            "status": self.status, "script_id": self.script_id,
            "player_count": self.player_count,
            "seat_roles": self.seat_roles, "seat_fakes": self.seat_fakes,
            "seat_markers": self.seat_markers,
            "phase": self.phase, "night_no": self.night_no, "day_no": self.day_no,
            "night_steps": self.night_steps, "night_idx": self.night_idx,
            "nominations": self.nominations, "current": self.current,
            "bluffs": self.bluffs, "sentinel": self.sentinel,
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
            self.players = {pid: Player(**p) for pid, p in d["players"].items()}
            for key in ("status", "script_id", "player_count", "seat_roles",
                        "seat_fakes", "seat_markers", "phase", "night_no",
                        "day_no", "night_steps", "night_idx", "nominations",
                        "current", "bluffs"):
                setattr(self, key, d[key])
            self.sentinel = d.get("sentinel", 0)  # 旧存档没有哨兵字段 → 默认关
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
        self.seat_roles = {}  # 预发身份一并清空
        self.seat_fakes = {}  # 认知覆盖一并清空
        self.seat_markers = {}  # 状态标记一并清空
        self.phase = None
        self.night_no, self.day_no = 1, 0
        self.night_steps, self.night_idx = [], 0
        self.nominations, self.current = [], None
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

    # ---- 玩家进出 ----

    def add_player(self, name: str) -> Player:
        player = Player(id=secrets.token_hex(4), name=name.strip()[:20])
        self.players[player.id] = player
        self.save()
        return player

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

        pool = random.sample(by_team[DEMON], comp[3])
        pool += random.sample(by_team[MINION], comp[2])
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
        self.status = "playing"
        self._begin_night()  # 发完角色 → 第一夜开始
        self.save()
        by_seat = sorted(self.players.values(), key=lambda p: p.seat)
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

    def assign_manual(self, assignments: list[dict], bluffs: list[str] | None = None) -> list[dict]:
        """说书人手动发身份:为每个座位指定角色。

        硬校验:恶魔恰 1 名、爪牙至少 1 名;镇民/外来者配比只作提示(教父 ±1 等由说书人决定)。
        无需等玩家入座:身份先挂在座位上,玩家入座时自动继承;全员入座后自动开局。
        伪装在配版时就选好:bluffs 给 3 个不在场好角色;不给则自动抽取。
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
        self.seat_roles = dict(picked)  # 身份挂在座位上,没人入座也可以先发
        for seat, player in seat_of.items():  # 已入座的玩家当场继承
            player.role_id = picked[seat]
        if len(seat_of) == self.player_count:
            self.status = "playing"  # 全员已入座 → 立即开局;否则等 sit() 补满自动开局
            self._begin_night()
        self.save()
        by_seat = sorted(self.players.values(), key=lambda p: p.seat)
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
        steps: list[dict] = []
        for st in sheet:
            key = st["key"]
            if key in ("dusk", "dawn", "minioninfo", "demoninfo") or key in present:
                steps.append(dict(st))
            for seat in fake_by_role.get(key, []):  # 酒鬼扮演该角色:附加一步,标注座位
                steps.append({**st, "fake_for": seat})
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
            self.phase = "day"
            self.day_no += 1
        self.save()

    def night_prev(self) -> None:
        if self.phase != "night" or self.night_idx <= 0:
            raise ValueError("已经在第一步,不能后退")
        self.night_idx -= 1
        self.save()

    def end_day(self) -> None:
        if self.phase != "day":
            raise ValueError("现在是夜晚,不能结束白天")
        self.night_no += 1
        self._begin_night()
        self.save()

    # ---- 提名 / 投票 / 处决 ----

    def start_nomination(self, nominator_seat: int, nominee_seat: int) -> None:
        if self.phase != "day":
            raise ValueError("白天才能发起提名")
        if self.current:
            raise ValueError("已有进行中的提名,先宣布结果")
        seat_of = self.seats
        if nominator_seat not in seat_of or nominee_seat not in seat_of:
            raise ValueError("提名者与被提名者都需已入座")
        if nominator_seat == nominee_seat:
            raise ValueError("不能提名自己")
        self.current = {"nominator": nominator_seat, "nominee": nominee_seat, "votes": []}
        self.save()

    def toggle_vote(self, seat: int) -> None:
        if not self.current:
            raise ValueError("没有进行中的提名")
        if not 1 <= seat <= self.player_count or seat not in self.seats:
            raise ValueError(f"座位 {seat} 无玩家")
        votes = self.current["votes"]
        if seat in votes:
            votes.remove(seat)
        else:
            votes.append(seat)
            votes.sort()
        self.save()

    def resolve_nomination(self, executed: bool) -> None:
        """宣布本次提名结果;处决则被提名者死亡。"""
        if not self.current:
            raise ValueError("没有进行中的提名")
        rec = {**self.current, "day": self.day_no, "executed": executed}
        self.nominations.append(rec)
        if executed:
            player = self.seats.get(self.current["nominee"])
            if player:
                player.alive = False
        self.current = None
        self.save()

    # ---- 状态操作 ----

    def toggle_alive(self, player_id: str) -> None:
        if player_id in self.players:
            self.players[player_id].alive = not self.players[player_id].alive
            self.save()

    def set_fake(self, seat: int, role_id: str | None) -> None:
        """认知覆盖:标记该座位玩家「实际是酒鬼,但看到的是 role_id 角色」。None 清除标记。"""
        if not 1 <= seat <= self.player_count:
            raise ValueError(f"座位需在 1~{self.player_count} 之间")
        if role_id is not None and role_id not in self.roles:
            raise ValueError(f"角色 {role_id} 不属于当前板子")
        if role_id is None:
            self.seat_fakes.pop(seat, None)
        else:
            self.seat_fakes[seat] = role_id
        if self.phase == "night":
            self._begin_night()  # 夜晚中改认知覆盖 → 重算步骤表(假角色步骤随之增减)
        self.save()

    def set_marker(self, seat: int, marker: str, on: bool) -> None:
        """说书人标记:该座位玩家中毒/醉酒/疯狂。仅说书人可见,玩家无感知。"""
        if not 1 <= seat <= self.player_count:
            raise ValueError(f"座位需在 1~{self.player_count} 之间")
        if marker not in MARKERS:
            raise ValueError(f"未知标记 {marker}")
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

    def _seat_slots(self, st_view: bool, my_id: str | None = None) -> list[dict]:
        seat_of = self.seats
        slots = []
        for i in range(1, self.player_count + 1):
            p = seat_of.get(i)
            if p is None:
                slot = {"seat": i, "player": None}
                if st_view and i in self.seat_roles:  # 空座上的预发身份,说书人可见
                    slot["assigned_role"] = self.roles[self.seat_roles[i]]
                if st_view and i in self.seat_fakes:  # 空座也能先标记认知覆盖
                    slot["fake_role"] = self.roles[self.seat_fakes[i]]
                slots.append(slot)
                continue
            entry = p.storyteller(self.roles) if st_view else p.public()
            slot = {"seat": i, "player": entry}
            if st_view and i in self.seat_fakes:  # 认知覆盖标记,说书人可见
                slot["fake_role"] = self.roles[self.seat_fakes[i]]
            if st_view and i in self.seat_markers:  # 状态标记,仅说书人可见
                slot["markers"] = self.seat_markers[i]
            if my_id is not None:  # is_me 属于座位槽位层,不属于 player
                slot["is_me"] = p.id == my_id
            slots.append(slot)
        return slots

    def _public_progress(self) -> dict:
        """白天/夜晚进度(玩家与说书人都可见)。"""
        return {"phase": self.phase, "night_no": self.night_no, "day_no": self.day_no}

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
            # 开局前不揭示身份:说书人开始游戏玩家才拿到角色
            "me": me.private(self.roles, fake_id) if started else me.public(),
            "seats": self._seat_slots(st_view=False, my_id=player_id),
        }
        if not started:
            return view
        team = self.roles[me.role_id]["team"] if me.role_id else None
        # 爪牙会面:恶魔是谁,推进到该步骤才揭晓
        if team == MINION and self._step_reached("minioninfo"):
            view["demon_seats"] = [{"seat": d["seat"], "name": d["name"]}
                                   for d in self._team_seats(DEMON)]
        # 恶魔会面:爪牙是谁 + 三个伪装,推进到该步骤才揭晓(按真实身份判断,酒鬼假镇民不触发)
        if team == DEMON and self._step_reached("demoninfo"):
            view["minion_seats"] = [{"seat": m["seat"], "name": m["name"]}
                                    for m in self._team_seats(MINION)]
            if self.bluffs:
                view["bluffs"] = [self.roles[rid] for rid in self.bluffs]
        return view

    def storyteller_view(self) -> dict:
        alive_count = sum(1 for p in self.players.values() if p.alive)
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
            "quorum": alive_count // 2 + 1,  # 处决所需票数(存活玩家半数以上;死者投票由说书人掌握)
            # 人未齐开局:每个座位都有身份(在座持有或空座预发)即可强制开始
            "can_start": self.status == "lobby" and all(
                (self.seats.get(i) is not None and self.seats[i].role_id)
                or i in self.seat_roles for i in range(1, self.player_count + 1)),
            "bluffs": [self.roles[rid] for rid in self.bluffs],  # 恶魔的三个伪装(说书人可见)
            "sentinel": self.sentinel,  # 哨兵:+1/−1/2(不变)/0(关),说书人可见
            # 入夜会面:告诉爪牙谁是恶魔、告诉恶魔谁是爪牙(空座预发也列出)
            "demon_seats": self._team_seats(DEMON),
            "minion_seats": self._team_seats(MINION),
            "saved_at": self.saved_at,
        }
