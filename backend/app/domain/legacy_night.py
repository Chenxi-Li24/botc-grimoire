"""Compatibility commands for the established night APIs."""

from __future__ import annotations

from ..night_order import NIGHT_ORDER
from ..roles import DEMON, OUTSIDER, TOWNSFOLK
from ..scripts.travelers import (DUSK_ORDER as TRAVELER_DUSK,
                                ROLE_BY_ID as TRAVELER_BY_ID)
from ..scripts.wafu_leiming import NIGHT_ACTIONS
from .constants import FAKE_POOLS


class LegacyNightMixin:
    def _begin_night(self) -> None:
        """进入夜晚:按本夜在场角色组装步骤表(酒鬼的假角色作为附加步骤)。"""
        rebuild_existing = (
            hasattr(self, "night")
            and self.phase == "night"
            and self.night.queue.night_no == self.night_no
        )
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
        if rebuild_existing:
            self.night.rebuild()
        else:
            self._bind_night_service()


    def _sync_legacy_night_index(self) -> None:
        current = self.night.queue.current
        if current is None:
            return
        ability = current.source.get("ability_character", current.character_id)
        for index, legacy in enumerate(self.night_steps):
            if legacy.get("key") != ability:
                continue
            fake_for = legacy.get("fake_for")
            if fake_for is not None and fake_for != current.actor_seat:
                continue
            self.night_idx = index
            return


    def navigate_night(self, *, direction: str | None = None,
                       step_id: str | None = None,
                       force_token: str | None = None):
        if self.winner:
            raise ValueError("本局已结束,先撤销结算")
        if self.phase != "night":
            raise ValueError("现在是白天,没有夜晚步骤")
        if step_id is not None:
            result = self.night.navigate(step_id=step_id)
        else:
            result = self.night.navigate(
                direction=direction,
                force=force_token is not None,
                force_token=force_token,
            )
        self._sync_legacy_night_index()
        if result.at_end and not result.blocked:
            self._apply_night_kills()  # 迁移期兼容仍由旧手机入口提交的刀人
            self.night.publish_dawn()
            self.phase = "day"
            self.day_no += 1
            self.day_stage = "talk"
        return result


    def night_goto(self, idx: int) -> None:
        if self.phase != "night":
            raise ValueError("现在是白天,没有夜晚步骤")
        if not 0 <= idx < len(self.night_steps):
            raise ValueError(f"步骤需在 0~{len(self.night_steps) - 1} 之间")
        legacy = self.night_steps[idx]
        key = legacy.get("key")
        fake_for = legacy.get("fake_for")
        step = next((item for item in self.night.queue.steps
                     if item.source.get("ability_character", item.character_id) == key
                     and (fake_for is None or item.actor_seat == fake_for)), None)
        if step is None:
            raise ValueError("旧版步骤已不在当前动态夜序中")
        self.navigate_night(step_id=step.id)
        self.save()


    def night_next(self) -> None:
        result = self.navigate_night(direction="next")
        if result.blocked:
            result = self.navigate_night(
                direction="next", force_token=result.force_token,
            )
        self.save()


    def night_prev(self) -> None:
        self.navigate_night(direction="previous")
        self.save()


    def end_day(self) -> None:
        if self.winner:
            raise ValueError("本局已结束,先撤销结算")
        if self.phase != "day":
            raise ValueError("现在是夜晚,不能结束白天")
        self._end_day_execution()  # 白天结束:结算处决(最多票者死,平票无人死)
        self.recall_chats()  # 天黑:私聊即焚,全部关闭
        self.effects.advance("dusk")  # 结束“持续到黄昏”的中毒/疯狂等语义时限
        self.night_no += 1
        self._begin_night()
        self.save()


    def submit_night_kill(self, player_id: str, seat: int) -> None:
        """恶魔手机选择刀杀目标(夜晚任意时刻可改,天亮自动执行);疯子同样可选(演戏,不生效)。"""
        if self.script_id != "wafu-leiming":
            raise ValueError("该板子暂未开放手机刀人")
        me = self.players[player_id]
        if me.seat is None:
            raise ValueError("你还没有入座")
        self.submit_night_kill_seat(me.seat, seat)


    def submit_night_kill_seat(self, seat: int, target: int) -> None:
        """说书人按座位代操作刀人(空座角色也可,便于测试人未齐开局;本局结束后封冻)。"""
        if self.winner:
            raise ValueError("本局已结束,先撤销结算")
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
        self._log(seat, "lunatic_kill" if rid == "lunatic" else "kill", {"target": target, "role": rid})
        self.save()


    def _apply_night_kills(self) -> None:
        """天亮时执行恶魔刀人:died_day=夜号,与既有「夜里死天亮公开」规则一致。
        麻脸巫婆创造了恶魔 → 本夜死亡由说书人决定,跳过自动执行(说书人手动标记)。
        空座同样可被刀死(以座位级生死标记为准)。"""
        entry = self.night_kills.get(str(self.night_no))
        if not entry or entry.get("seat") is None:
            return
        if entry.get("arbitrary") or self.night._arbitrary_death_source() is not None:
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
        """说书人按座位代操作夜晚选人(空座角色也可,便于测试人未齐开局;本局结束后封冻)。"""
        if self.winner:
            raise ValueError("本局已结束,先撤销结算")
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
                self._apply_pithag(seat)  # 旧入口适配:通过新事务处理器确认
            elif eff == "cerenovus":
                self._apply_cerenovus(seat)  # 旧入口适配:写入可溯源疯狂效果
        elif eff == "widow" and targets:
            effect = self.night.apply_widow(seat, targets[0])
            entry["effect_id"] = effect.id
            entry["applied"] = True
        self._log(seat, "choice", {"role": eff, "targets": sorted(targets),
                                   "char": entry.get("char")})
        self.save()


    def _apply_pithag(self, seat: int) -> None:
        """Legacy submission adapter for the canonical preview/confirm transaction."""
        entry = self.night_choices.get(str(self.night_no), {}).get(str(seat))
        if entry is None or entry.get("role") != "pithag" or entry.get("applied"):
            return
        char, target = entry["char"], entry["targets"][0]
        preview = self.night.preview_pit_hag(seat, target, char)
        event = self.night.confirm_pit_hag_preview(preview.id)
        entry["preview_id"] = preview.id
        entry["event_id"] = event.id
        entry["from"] = preview.old_character
        entry["applied"] = event.kind == "pit_hag_transformation"
        if not entry["applied"]:
            entry["invalid"] = True
        self._log(seat, ("transform" if entry["applied"] else "transform_invalid"),
                  {"target": target, "char": char, "from": preview.old_character})


    def _apply_cerenovus(self, seat: int) -> None:
        """Legacy submission adapter for sourced Cerenovus madness."""
        entry = self.night_choices.get(str(self.night_no), {}).get(str(seat))
        if entry is None or entry.get("role") != "cerenovus":
            return
        char, target = entry["char"], entry["targets"][0]
        effect = self.night.apply_cerenovus(seat, target, char)
        entry["prev_target"] = target
        entry["effect_id"] = effect.id
        entry["applied"] = True
        entry.pop("invalid", None)
        self._log(seat, "mad", {"target": target, "char": char})


    def revert_pithag(self, seat: int) -> None:
        """说书人撤销已生效的麻脸巫婆变身(容错):恢复角色、移除注入步骤与「死亡由说书人决定」标记。"""
        canonical = next((event for event in reversed(self.journal_events)
                          if event.state == "active"
                          and event.kind == "pit_hag_transformation"
                          and event.payload.get("actor_seat") == seat), None)
        if canonical is not None:
            self.night.undo(canonical.id, confirm=True)
            entry = self.night_choices.get(str(self.night_no), {}).get(str(seat))
            if entry is not None and entry.get("event_id") == canonical.id:
                entry["applied"] = False
            self.save()
            return
        entry = self.night_choices.get(str(self.night_no), {}).get(str(seat))
        if entry is None or not entry.get("applied"):
            raise ValueError("没有已生效的变身可撤销")
        char, target, prev = entry["char"], entry["targets"][0], entry.get("from")
        if prev:
            self.seat_roles[target] = prev
            self.seat_role_changes.pop(target, None)
            self._rebuild_night_queue()
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
        self._log(seat, "reply", {"text": entry["reply"]})
        self.save()


    def set_fortuneteller_red(self, seat: int | None) -> None:
        """占卜师宿敌:说书人私下标记一名善良玩家,占卜师查他总被当作恶魔(只有说书人知道)。"""
        present = ({p.role_id for p in self.players.values() if p.role_id}
                   | set(self.seat_roles.values()))
        if "fortuneteller" not in present:
            raise ValueError("本局没有占卜师,不需要标记宿敌")
        if seat is None:
            self.fortuneteller_red = None
            for holder in self._role_seats("fortuneteller"):
                self.night.abilities.set_fortune_teller_red_herring(holder["seat"], None)
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
        for holder in self._role_seats("fortuneteller"):
            self.night.abilities.set_fortune_teller_red_herring(holder["seat"], seat)
        self.save()
