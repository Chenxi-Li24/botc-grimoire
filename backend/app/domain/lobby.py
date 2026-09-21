"""Lobby configuration, seating, traveler setup, and role assignment."""

from __future__ import annotations

import random
import secrets
from collections import Counter

from ..roles import (COMPOSITION, DEMON, MINION, OUTSIDER, SCRIPTS,
                     SCRIPT_ADJUST_ROLES, ROLE_ADJUSTMENTS, TOWNSFOLK)
from ..scripts.travelers import ROLE_BY_ID as TRAVELER_BY_ID
from .constants import FAKE_POOLS
from .player import Player
from ..state import SeatState


class LobbyMixin:
    def configure(self, script_id: str, player_count: int) -> None:
        if script_id not in SCRIPTS:
            raise ValueError("未知脚本")
        min_players = SCRIPTS[script_id].get("min_players", 5)
        max_players = SCRIPTS[script_id].get("max_players", 15)
        if not min_players <= player_count <= max_players:
            raise ValueError(f"人数需在 {min_players}~{max_players} 之间")
        if self.status == "playing" or self.winner is not None:
            self.game_id = secrets.token_hex(16)
            self.players.clear()
        self.script_id = script_id
        self.player_count = player_count
        for p in self.players.values():  # 改配置 → 清空座位与角色,玩家重新入座
            p.seat = None
            p.bind(None)
        self.seat_states = {
            seat: SeatState(seat=seat) for seat in range(1, player_count + 1)
        }
        self.journal_events = []
        self.effect_records = {}
        self.pending_outcomes = {}
        self.information_drafts = {}
        self.information_deliveries = {}
        self.information_notices = []
        self.pending_transformations = {}
        self._bind_night_ledgers()
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
        self.winner = None  # 结算状态随配置清空
        self.events = []  # 复盘日志随配置清空(换板子=新局)
        self.event_seq = 0
        self.inference_events = []  # 新局必须清掉上一局所有玩家的私有推测
        self.inference_seq = 0
        self.chats = []  # 私聊清空(换板子=新局)
        self.chat_seq = 0
        self.status = "lobby"
        self._bind_night_service()
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
        if me.seat is not None and me.seat != seat:
            previous = self.seat_state(me.seat)
            if previous.claimed_by == player_id:
                previous.claimed_by = None
        me.seat = seat
        state = self.seat_state(seat)
        state.claimed_by = player_id
        me.bind(state)
        self._rebuild_night_queue()
        if (self.status == "lobby" and self.seat_roles
                and len(self.seats) == self.player_count):
            self.status = "playing"  # 预发身份全部入座 → 自动开局
            self._begin_night()
        self.save()


    def remove_player(self, player_id: str) -> None:
        if player_id not in self.players:
            return
        player = self.players[player_id]
        if player.seat is not None:
            state = self.seat_state(player.seat)
            if state.claimed_by == player_id:
                state.claimed_by = None
        player.bind(None)
        del self.players[player_id]  # 只释放账号认领;角色与局内状态留在座位
        self._rebuild_night_queue()
        self.save()


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
        self._log(None, "traveler_join", {"name": t["name"]})
        self._rebuild_night_queue()
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
        self._rebuild_night_queue()
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
        self._log(None, "traveler_assign", {"name": t["name"], "role": role_id, "align": t["align"]})
        self._rebuild_night_queue()
        self.save()


    def exile_traveler(self, traveler_id: str, exiled: bool) -> None:
        """流放/撤销流放:白天投票流放,或说书人随时执行(早退玩家)。流放当场公开。"""
        t = self._traveler(traveler_id)
        t["exiled"] = exiled
        t["alive"] = not exiled
        t["died_day"] = (self.day_no if self.phase == "day" else self.night_no) if exiled else None
        if exiled:
            self._log(None, "traveler_exile", {"name": t["name"]})
        self._rebuild_night_queue()
        self.save()


    def toggle_traveler_alive(self, traveler_id: str) -> None:
        """旅行者生/死标记(恶魔夜袭等);夜里死天亮才公开(与座位玩家同规则)。"""
        t = self._traveler(traveler_id)
        if t["exiled"]:
            raise ValueError("已流放:先撤销流放才能改动生死")
        t["alive"] = not t["alive"]
        t["died_day"] = None if t["alive"] else (self.day_no if self.phase == "day" else self.night_no)
        self._rebuild_night_queue()
        self.save()


    def _target(self, target: int | str) -> tuple[Player | None, dict | None]:
        """提名/投票目标:座位 int → (玩家,None);"t1" 字符串 → (None,旅行者)。"""
        if isinstance(target, int):
            return self.seats.get(target), None
        return None, next((t for t in self.travelers if t["id"] == target), None)


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
            self.seat_roles[seat] = rid  # 角色始终挂在座位,玩家账号只负责认领
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


    def _bluff_teams(self) -> tuple[str, ...]:
        """伪装可取的好角色阵营:暗流涌动限镇民,其余脚本镇民+外来者。"""
        return (TOWNSFOLK,) if self.script_id == "trouble-brewing" else (TOWNSFOLK, OUTSIDER)


    def _pick_bluffs(self, present: set[str]) -> list[str]:
        """从不在场的好角色里随机抽三个伪装。"""
        pool = [r["id"] for r in self.roles.values()
                if r["team"] in self._bluff_teams() and r["id"] not in present]
        return random.sample(pool, min(3, len(pool)))
