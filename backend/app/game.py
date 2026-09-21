"""游戏状态管理(单局):说书人配置板子/人数,玩家选环形座位入座。

v1 完整版新增:
- 昼夜阶段(phase: night/day)与夜晚流程助手(按 NIGHT_ORDER 逐步推进)
- 状态标记(中毒/醉酒/疯狂,仅说书人可见)
- 白天提名→投票→处决
- JSON 自动存档:每次变更即写盘,进程重启自动恢复
"""

import random
import secrets
import time
from collections.abc import MutableMapping
from pathlib import Path

from .application.projections import ProjectionMixin
from .domain.player import Player
from .domain.lobby import LobbyMixin
from .domain.balloonist import BalloonistMixin
from .domain.legacy_night import LegacyNightMixin
from .domain.nomination import NominationMixin
from .domain.review import ReviewMixin
from .domain.chat import ChatMixin
from .domain.inference import InferenceMixin
from .domain.seat_admin import SeatAdministrationMixin
from .infrastructure.persistence import read_snapshot, write_snapshot
from .night.effects import EffectLedger
from .night.journal import EventJournal
from .night.models import timestamp
from .night.service import NightService
from .roles import DEMON, MINION, SCRIPTS, SCRIPT_PACKS
from .scripts.travelers import (DUSK_ORDER as TRAVELER_DUSK,
                                ROLE_BY_ID as TRAVELER_BY_ID)
from .save_codec import decode_save, encode_save
from .state import GameState, PlayerAccount, SeatState

SAVE_PATH = Path(__file__).resolve().parent.parent / "data" / "game.json"




class _SeatFieldMap(MutableMapping):
    """Legacy mapping facade whose only storage is canonical SeatState."""

    def __init__(self, manager, field_name, missing, on_set=None):
        self.manager = manager
        self.field_name = field_name
        self.missing = missing
        self.on_set = on_set

    def _value(self, seat):
        return getattr(self.manager.seat_state(int(seat)), self.field_name)

    def __getitem__(self, seat):
        value = self._value(seat)
        if self.missing(value):
            raise KeyError(seat)
        return value

    def __setitem__(self, seat, value):
        state = self.manager.seat_state(int(seat))
        setattr(state, self.field_name, value)
        if self.on_set:
            self.on_set(state, value)

    def __delitem__(self, seat):
        state = self.manager.seat_state(int(seat))
        value = getattr(state, self.field_name)
        if self.missing(value):
            raise KeyError(seat)
        if isinstance(value, list):
            replacement = []
        elif isinstance(value, bool):
            replacement = not value
        else:
            replacement = None
        setattr(state, self.field_name, replacement)
        if self.on_set:
            self.on_set(state, replacement)

    def __iter__(self):
        return (seat for seat in self.manager.seat_states
                if not self.missing(self._value(seat)))

    def __len__(self):
        return sum(1 for _ in self)


class GameManager(LobbyMixin, BalloonistMixin, LegacyNightMixin, NominationMixin, ReviewMixin,
                  ChatMixin, SeatAdministrationMixin, InferenceMixin, ProjectionMixin):
    """一局游戏的全部状态;每次变更自动存档,重启自动恢复。"""

    def __init__(self) -> None:
        self.script_id: str = "trouble-brewing"  # 说书人可配置
        self.player_count: int = 6
        self.reset()
        self._restore_autosave()  # 进程重启 → 恢复上次存档(若有)

    def reset(self) -> None:
        # 注意:reset 不写盘 → 误重置可用「读档」撤销;开始新局的第一次变更会覆盖存档
        self.game_id = secrets.token_hex(16)
        self.players: dict[str, Player] = {}
        self.seat_states: dict[int, SeatState] = {
            seat: SeatState(seat=seat) for seat in range(1, self.player_count + 1)
        }
        self.status: str = "lobby"  # lobby | playing
        self.current_dead_votes: set[int] = set()  # 当前提名中交出的死票座位(结算即清空;未结算时取消举手可归还)
        self.lunatic_minions: dict[int, list[int]] = {}  # 疯子:座位号 → 疯子以为的爪牙座位(说书人选,不一定是真爪牙)
        self.lunatic_bluffs: dict[int, list[str]] = {}  # 疯子:座位号 → 说书人给疯子的 3 个伪装(不一定是恶魔的真伪装)
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
        self.balloonist_version: str | None = None
        self.balloonist_outsider_delta: int | None = None
        self.balloonist_events: list[dict] = []
        self.room_code: str = f"{random.randrange(10000):04d}"  # 房间号:4 位数字,说书人可改,玩家凭名字+房号加入
        self.winner: str | None = None  # 结算:good/evil 获胜(说书人宣布游戏结束),None = 未结束
        self.fabled: list[str] = []  # 传奇角色(公开):在场的 Fabled id 列表,说书人勾选
        self.chats: list[dict] = []  # 白天私聊(说书人留档存档;玩家端天黑即焚;重置清空)
        self.chat_seq: int = 0  # 消息自增序号(后加入者按 joined_seq 过滤历史)
        self.events: list[dict] = []  # 复盘事件日志:[{seq, phase, n, seat, type, data}] 追加式,只对新打的局有效
        self.event_seq: int = 0
        self.inference_events: list[dict] = []  # 玩家私有推测，与真实游戏事件隔离
        self.inference_seq: int = 0
        self.journal_events = []  # 新夜晚引擎:可撤销、带依赖的不可变事件
        self.effect_records = {}  # 新夜晚引擎:含来源、生命周期与完整历史的状态效果
        self.pending_outcomes = {}  # 选择与结果分离;等待说书人裁定或已裁定的夜晚结果
        self.information_drafts = {}
        self.information_deliveries = {}
        self.information_notices = []
        self.pending_transformations = {}
        self.saved_at: float | None = None
        self._legacy_save_backup_pending: bool = False
        self._bind_night_ledgers()
        self._bind_night_service()

    @property
    def roles(self) -> dict:
        return {r["id"]: r for r in SCRIPTS[self.script_id]["roles"]}

    @property
    def seats(self) -> dict[int, Player]:
        return {p.seat: p for p in self.players.values() if p.seat is not None}

    def seat_state(self, seat: int) -> SeatState:
        if not 1 <= int(seat) <= self.player_count:
            raise KeyError(seat)
        seat = int(seat)
        if seat not in self.seat_states:
            self.seat_states[seat] = SeatState(seat=seat)
        return self.seat_states[seat]

    def _replace_seat_map(self, field_name, values, empty_value, on_set=None) -> None:
        for state in self.seat_states.values():
            setattr(state, field_name, empty_value() if callable(empty_value) else empty_value)
            if on_set:
                on_set(state, getattr(state, field_name))
        view = _SeatFieldMap(self, field_name, lambda value: False, on_set)
        for seat, value in (values or {}).items():
            view[int(seat)] = value

    def _character_changed(self, state: SeatState, character_id: str | None) -> None:
        if state.team_change_notice is not None:
            return
        role = self.roles.get(character_id) if character_id else None
        state.alignment = "evil" if role and role["team"] in (MINION, DEMON) else "good"

    def _team_notice_changed(self, state: SeatState, team: str | None) -> None:
        if team in ("good", "evil"):
            state.alignment = team
        elif state.character_id:
            self._character_changed(state, state.character_id)

    @property
    def seat_roles(self):
        return _SeatFieldMap(self, "character_id", lambda value: value is None,
                             self._character_changed)

    @seat_roles.setter
    def seat_roles(self, values):
        self._replace_seat_map("character_id", values, None, self._character_changed)

    @property
    def seat_fakes(self):
        return _SeatFieldMap(self, "perceived_character_id", lambda value: value is None)

    @seat_fakes.setter
    def seat_fakes(self, values):
        self._replace_seat_map("perceived_character_id", values, None)

    @property
    def seat_markers(self):
        return _SeatFieldMap(self, "legacy_markers", lambda value: not value)

    @seat_markers.setter
    def seat_markers(self, values):
        self._replace_seat_map("legacy_markers", values, list)

    @property
    def mad_about(self):
        return _SeatFieldMap(self, "mad_about", lambda value: value is None)

    @mad_about.setter
    def mad_about(self, values):
        self._replace_seat_map("mad_about", values, None)

    @property
    def seat_alive(self):
        return _SeatFieldMap(self, "alive", lambda value: value is True)

    @seat_alive.setter
    def seat_alive(self, values):
        self._replace_seat_map("alive", values, True)

    @property
    def seat_dead_day(self):
        return _SeatFieldMap(self, "died_day", lambda value: value is None)

    @seat_dead_day.setter
    def seat_dead_day(self, values):
        self._replace_seat_map("died_day", values, None)

    @property
    def seat_dead_vote(self):
        return _SeatFieldMap(self, "dead_vote_used", lambda value: value is False)

    @seat_dead_vote.setter
    def seat_dead_vote(self, values):
        self._replace_seat_map("dead_vote_used", values, False)

    @property
    def seat_role_changes(self):
        return _SeatFieldMap(self, "role_change_notice", lambda value: value is None)

    @seat_role_changes.setter
    def seat_role_changes(self, values):
        self._replace_seat_map("role_change_notice", values, None)

    @property
    def seat_team_changes(self):
        return _SeatFieldMap(self, "team_change_notice", lambda value: value is None,
                             self._team_notice_changed)

    @seat_team_changes.setter
    def seat_team_changes(self, values):
        self._replace_seat_map("team_change_notice", values, None,
                               self._team_notice_changed)

    def _canonical_state(self) -> GameState:
        return GameState(
            player_count=self.player_count,
            players={player_id: PlayerAccount(
                id=player.id, name=player.name, seat=player.seat, wish=player.wish,
                account_id=player.account_id,
            ) for player_id, player in self.players.items()},
            seats=self.seat_states,
            event_records=self.journal_events,
            effect_records=self.effect_records,
            pending_outcomes=self.pending_outcomes,
            information_drafts=self.information_drafts,
            information_deliveries=self.information_deliveries,
            information_notices=self.information_notices,
            pending_transformations=self.pending_transformations,
        )

    def _bind_night_ledgers(self) -> None:
        core = self._canonical_state()
        self.journal = EventJournal(core)
        self.effects = EffectLedger(core)

    def _traveler_night_actions(self) -> list[dict]:
        actions = []
        for role_id in TRAVELER_DUSK:
            holders = [traveler for traveler in self.travelers
                       if traveler["role_id"] == role_id and traveler["alive"]]
            if not holders:
                continue
            if role_id == "apprentice" and not any(
                traveler["joined_no"] == self.night_no
                if traveler["joined_phase"] == "night"
                else traveler["joined_no"] + 1 == self.night_no
                for traveler in holders
            ):
                continue
            role = TRAVELER_BY_ID[role_id]
            actions.append({
                "character_id": role_id,
                "traveler_ids": [traveler["id"] for traveler in holders],
                "name": f"🎒 {role['name']}",
                "reminder": role["ability"],
                "required_fields": ["acknowledged"],
            })
        return actions

    def _bind_night_service(self, restored_queue: dict | None = None) -> None:
        self.night = NightService(
            self.journal.state,
            SCRIPT_PACKS[self.script_id],
            self.night_no,
            self.journal,
            self.effects,
            traveler_actions=self._traveler_night_actions(),
            restored_queue=restored_queue,
        )
        self.skip_exhausted_balloonist_steps()

    def _rebuild_night_queue(self, cause_event_id: str | None = None) -> None:
        if self.phase == "night" and hasattr(self, "night"):
            self.night.queue.traveler_actions = self._traveler_night_actions()
            self.night.rebuild(cause_event_id)
            self.skip_exhausted_balloonist_steps()

    def _migrate_legacy_effects(self) -> None:
        """Expose pre-ledger markers as sourced manual effects without losing history."""
        for state in self.seat_states.values():
            for marker in state.legacy_markers:
                exists = any(
                    effect.target_seat == state.seat
                    and effect.type == marker
                    and effect.payload.get("legacy_marker")
                    for effect in self.effect_records.values()
                )
                if exists:
                    continue
                self.effects.apply(
                    marker,
                    state.seat,
                    source_event="migration:legacy_marker",
                    payload={"legacy_marker": True, "migrated": True,
                             "about": state.mad_about if marker == "mad" else None},
                    lifetime_policy={"kind": "manual"},
                )

    def _bind_players_to_seats(self) -> None:
        for state in self.seat_states.values():
            state.claimed_by = None
        for player in self.players.values():
            if player.seat is None:
                player.bind(None)
                continue
            state = self.seat_state(player.seat)
            state.claimed_by = player.id
            player.bind(state)

    def mark_private_deliveries_delivered(self, player_id: str) -> bool:
        """Record observable websocket delivery without requiring player acknowledgement."""
        player = self.players.get(player_id)
        if player is None or player.seat is None:
            return False
        active_events = {event.id for event in self.journal_events
                         if event.state == "active"}
        delivered_at = timestamp()
        changed = False
        for delivery in self.information_deliveries.values():
            if (delivery.actor_seat == player.seat
                    and delivery.source_event in active_events
                    and delivery.delivered_at is None):
                delivery.delivered_at = delivered_at
                changed = True
        return changed

    # ---- 复盘事件日志 ----

    def _log(self, seat: int | None, etype: str, data: dict | None = None) -> None:
        """追加复盘事件(终局后供结算复盘页按时间线展示)。"""
        self.event_seq += 1
        self.events.append({
            "seq": self.event_seq,
            "phase": self.phase,
            "n": self.day_no if self.phase == "day" else self.night_no,
            "seat": seat,
            "type": etype,
            "data": data or {},
        })

    # ---- 存档 ----

    def save_payload(self) -> dict:
        """Build the complete serializable payload without touching disk."""
        payload = encode_save(self._canonical_state())
        payload.update({
            "game_id": self.game_id,
            "status": self.status, "script_id": self.script_id,
            "lunatic_minions": self.lunatic_minions, "lunatic_bluffs": self.lunatic_bluffs,
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
            "balloonist_version": self.balloonist_version,
            "balloonist_outsider_delta": self.balloonist_outsider_delta,
            "balloonist_events": self.balloonist_events,
            "winner": self.winner, "fabled": self.fabled,
            "chats": self.chats, "chat_seq": self.chat_seq,
            "events": self.events, "event_seq": self.event_seq,
            "inference_events": self.inference_events, "inference_seq": self.inference_seq,
            "night_queue_state": self.night.dump(),
        })
        return payload

    def save(self) -> None:
        """任何状态变更后调用:原子写盘(临时文件 + os.replace)。"""
        payload = self.save_payload()
        write_snapshot(SAVE_PATH, payload, backup_legacy=self._legacy_save_backup_pending)
        self._legacy_save_backup_pending = False
        self.saved_at = time.time()

    def _restore_autosave(self) -> None:
        try:
            d = read_snapshot(SAVE_PATH)
            if d is None:
                return
            legacy_save = d.get("schema_version") != 2
            script_id = d.get("script_id", "trouble-brewing")
            if script_id not in SCRIPT_PACKS:
                raise ValueError("unknown saved script")
            core = decode_save(d, SCRIPT_PACKS[script_id])
            self.script_id = script_id
            self.player_count = core.player_count
            self.seat_states = core.seats
            self.journal_events = core.event_records
            self.effect_records = core.effect_records
            self.pending_outcomes = core.pending_outcomes
            self.information_drafts = core.information_drafts
            self.information_deliveries = core.information_deliveries
            self.information_notices = core.information_notices
            self.pending_transformations = core.pending_transformations
            self.players = {pid: Player(id=account.id, name=account.name,
                                        seat=account.seat, wish=account.wish,
                                        account_id=account.account_id)
                            for pid, account in core.players.items()}
            self._bind_players_to_seats()
            self._bind_night_ledgers()
            self._migrate_legacy_effects()
            for key in ("status", "phase", "night_no",
                        "day_no", "night_steps", "night_idx", "nominations",
                        "current", "bluffs"):
                setattr(self, key, d[key])
            self.day_stage = d.get("day_stage", "talk")  # 旧存档没有白天子阶段 → 默认公聊
            self.sentinel = d.get("sentinel", 0)  # 旧存档没有哨兵字段 → 默认关
            self.balloonist_version = self.balloonist_version_from_save(d)
            self.balloonist_outsider_delta = (
                d.get("balloonist_outsider_delta") if self.balloonist_version else None
            )
            self.balloonist_events = list(d.get("balloonist_events", ()))
            self.winner = d.get("winner")  # 旧存档没有结算 → None
            self.fabled = d.get("fabled", [])  # 旧存档没有传奇角色 → 空
            self.events = d.get("events", [])  # 旧存档没有复盘日志 → 空
            self.event_seq = d.get("event_seq", 0)
            self.inference_events = d.get("inference_events", [])
            self.inference_seq = d.get("inference_seq", 0)
            self.chat_seq = d.get("chat_seq", 0)
            def _norm(w):
                return int(w) if isinstance(w, str) and w.isdigit() else w
            self.chats = []
            for c in d.get("chats", []):  # JSON 把 int 键转成了 str,这里还原
                c["members"] = {_norm(k): v for k, v in c.get("members", {}).items()}
                c["invites"] = {_norm(k): v for k, v in c.get("invites", {}).items()}
                c["join_requests"] = {_norm(k): v for k, v in c.get("join_requests", {}).items()}
                for m in c.get("messages", []):
                    m["from"] = _norm(m["from"])
                self.chats.append(c)
            self.room_code = d.get("room_code") or f"{random.randrange(10000):04d}"  # 旧存档没有房间号 → 现生成
            self.game_id = d.get("game_id", self.game_id)
            self.lunatic_minions = {int(k): v for k, v in d.get("lunatic_minions", {}).items()}
            self.lunatic_bluffs = {int(k): v for k, v in d.get("lunatic_bluffs", {}).items()}
            # 死票座位/旅行者 id 存档时统一转 str,读档时数字座位还原为 int(旅行者 id 保持 "t1" 字符串)
            self.current_dead_votes = {int(x) if isinstance(x, str) and x.isdigit() else x
                                       for x in d.get("current_dead_votes", [])}
            self.travelers = d.get("travelers", [])  # 旧存档没有旅行者 → 空
            self.night_kills = d.get("night_kills", {})  # 旧存档没有夜晚刀人 → 空
            self.night_choices = d.get("night_choices", {})  # 旧存档没有夜晚信息交互 → 空
            self.fortuneteller_red = d.get("fortuneteller_red")  # 旧存档没有宿敌 → None
            self._bind_night_service(d.get("night_queue_state"))
            if self.fortuneteller_red is not None:
                for holder in self._role_seats("fortuneteller"):
                    self.night.abilities.set_fortune_teller_red_herring(
                        holder["seat"], self.fortuneteller_red,
                    )
            self._legacy_save_backup_pending = legacy_save
            self.saved_at = time.time()
        except (KeyError, TypeError, ValueError):
            pass  # 存档损坏 → 用干净状态开局

    def load(self) -> None:
        """说书人手动读档:放弃当前内存状态,从磁盘恢复。"""
        self.script_id = "trouble-brewing"
        self.player_count = 6
        self.reset()
        self._restore_autosave()
