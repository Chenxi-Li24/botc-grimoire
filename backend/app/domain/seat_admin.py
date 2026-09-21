"""Storyteller-controlled life, fake role, and marker changes."""

from __future__ import annotations

import secrets
from ..roles import DEMON, MINION, OUTSIDER, TOWNSFOLK
from .constants import FAKE_POOLS, MARKERS


class SeatAdministrationMixin:
    def toggle_alive(self, player_id: str) -> None:
        if player_id in self.players:
            p = self.players[player_id]
            if p.seat is None:
                raise ValueError("玩家还没有入座")
            state = self.seat_state(p.seat)
            state.alive = not state.alive
            state.public_alive = (True if not state.alive and self.phase == "night"
                                  else state.alive)
            if state.alive:  # 复活重置死票:再次死亡会获得新的死票
                state.dead_vote_used = False
                self.current_dead_votes.discard(p.seat)
            # 死亡公开的天数:夜里死=天亮那天(night_no),白天死=当天(day_no),复活清空
            state.died_day = ((self.night_no if self.phase == "night" else self.day_no)
                              if not state.alive else None)
            state.died_at = (f"{self.phase}:{state.died_day}:storyteller"
                             if not state.alive else None)
            self._rebuild_night_queue()
            self.save()


    def toggle_seat_alive(self, seat: int) -> None:
        """说书人按座位标记生死(空座同样可以):以说书人标记为准,而不是是否在座。"""
        if not 1 <= seat <= self.player_count or self._seat_real_role(seat) is None:
            raise ValueError("该座位没有角色")
        state = self.seat_state(seat)
        if state.alive:  # 标记死亡
            state.alive = False
            state.public_alive = self.phase == "night"
            state.died_day = self.day_no if self.phase == "day" else self.night_no
            state.died_at = f"{self.phase}:{state.died_day}:storyteller"
            self._log(seat, "death", {"by": "st"})
        else:  # 复活
            state.alive = True
            state.public_alive = True
            state.died_day = None
            state.died_at = None
            state.dead_vote_used = False
        self._rebuild_night_queue()
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
                prev = self._seat_real_role(seat)
                self.seat_states[seat].ability_state["legacy_role_change"] = {"from": prev}
                self.seat_roles[seat] = role
                self.seat_role_changes[seat] = role
                # 传刀识别:爪牙 → 恶魔
                pass_demon = bool(prev and self.roles[prev]["team"] == MINION
                                  and self.roles[role]["team"] == DEMON)
                self._log(seat, "role_change", {"to": role, "from": prev,
                                                "pass_demon": pass_demon})
            else:
                self.seat_role_changes.pop(seat, None)
            self._rebuild_night_queue()
            self.save()
            return
        if marker == "team-change":  # 带数据的标记:说书人选新阵营,角标/玩家提示按阵营配色
            if on:
                if team not in ("good", "evil"):
                    raise ValueError("阵营转变需选择新阵营(善良/邪恶)")
                self.seat_team_changes[seat] = team
                self._log(seat, "team_change", {"team": team})
            else:
                self.seat_team_changes.pop(seat, None)
            self._rebuild_night_queue()
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
        if marker in ("poisoned", "drunk", "mad"):
            replacement_dependencies: list[str] = []
            current_effects = [
                effect for effect in self.effects.current_for_seat(seat)
                if effect.type == marker and effect.payload.get("legacy_marker")
            ]
            if (on and marker == "mad" and current_effects
                    and any(effect.payload.get("about") != about
                            for effect in current_effects)):
                for effect in current_effects:
                    replacement_event = self.journal.append(
                        "legacy_effect_replaced",
                        {"seat": seat, "effect_id": effect.id, "effect_type": marker},
                        {"op": "restore_effect", "effect": effect.to_dict()},
                        depends_on=([effect.source_event]
                                    if any(item.id == effect.source_event
                                           for item in self.journal.records) else []),
                    )
                    replacement_dependencies.append(replacement_event.id)
                    self.effects.transition(effect.id, "ended", "choice_replaced")
                current_effects = []
            if on and not current_effects:
                effect_id = secrets.token_hex(16)
                event = self.journal.append(
                    "legacy_effect_applied",
                    {"seat": seat, "effect_type": marker, "about": about},
                    {"op": "end_effect", "effect_id": effect_id},
                    depends_on=replacement_dependencies,
                )
                self.effects.apply(
                    marker,
                    seat,
                    source_event=event.id,
                    payload={"legacy_marker": True, "about": about},
                    lifetime_policy={"kind": "manual"},
                    effect_id=effect_id,
                )
            elif not on:
                for effect in current_effects:
                    self.journal.append(
                        "legacy_effect_ended",
                        {"seat": seat, "effect_id": effect.id, "effect_type": marker},
                        {"op": "restore_effect", "effect": effect.to_dict()},
                        depends_on=([effect.source_event]
                                    if any(item.id == effect.source_event
                                           for item in self.journal.records) else []),
                    )
                    self.effects.transition(effect.id, "ended", "storyteller_removed")
        cur = set(self.seat_markers.get(seat, ()))
        if on:
            cur.add(marker)
        else:
            cur.discard(marker)
        if marker in ("poisoned", "drunk"):  # 错误信息判定依赖中毒/醉酒的时间线
            self._log(seat, "marker", {"marker": marker, "on": on})
        if cur:
            self.seat_markers[seat] = sorted(cur)
        else:
            self.seat_markers.pop(seat, None)
        self.save()
