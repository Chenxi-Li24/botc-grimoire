"""Balloonist version rules and immutable, recipient-bound night messages."""

from __future__ import annotations

from copy import deepcopy

from ..night.models import timestamp
from ..scripts.travelers import ROLE_BY_ID as TRAVELER_BY_ID


def _allowed_types(version: str, previous: str | None,
                   used: set[str], options: list[str]) -> list[str]:
    if version == "new":
        return [item for item in options if item != previous]
    return [item for item in options if item not in used]


class BalloonistMixin:
    def _balloonist_impairments(self, actor_seat: int) -> tuple[list[dict], list[str]]:
        effects = [effect.to_dict() for effect in
                   self.night.effects.active_for_seat(actor_seat)]
        reasons = [effect["type"] for effect in effects
                   if effect["type"] in ("poisoned", "drunk", "information_override")]
        if self.seat_state(actor_seat).character_id == "drunk":
            reasons.append("drunk")
        if any(seat.character_id == "vortox" and seat.alive
               for seat in self.seat_states.values()):
            reasons.append("vortox_forced_false")
        return effects, list(dict.fromkeys(reasons))

    def skip_exhausted_balloonist_steps(self) -> None:
        if self.balloonist_version != "old":
            return
        for step in self.night.queue.steps:
            if (step.status == "upcoming" and step.actor_seat is not None
                    and step.source.get("ability_character") == "balloonist"
                    and self.balloonist_context(step.actor_seat)["exhausted"]):
                step.status = "skipped"
                step.skip_reason = "balloonist_types_exhausted"

    def balloonist_role_view(self, role: dict) -> dict:
        if role["id"] != "balloonist" or self.balloonist_version is None:
            return role
        label = "新版" if self.balloonist_version == "new" else "旧版"
        ability = ("每个夜晚，你会得知一名玩家的编号；其角色类型与上一晚所示不同。"
                   if self.balloonist_version == "new" else
                   "每个夜晚，你会得知一名玩家的编号；其角色类型此前未展示过。四类用尽后不再获得信息。")
        return {**role, "name": f"气球驾驶员（{label}）", "ability": ability}

    def balloonist_night_workflow(self) -> dict:
        workflow = self.night.projection()
        if self.balloonist_version is None:
            return workflow
        label = "新版" if self.balloonist_version == "new" else "旧版"
        reminder = ("每夜指向一名玩家，其本次登记类型与上一次有效信息不同。"
                    if self.balloonist_version == "new" else
                    "依次指向未展示过登记类型的玩家；类型用尽后停止。")
        for step in workflow["steps"]:
            if step["source"].get("ability_character") == "balloonist":
                step["name"] = f"气球驾驶员（{label}）"
                step["reminder"] = reminder
        current = workflow.get("current_task")
        if current and current["source"].get("ability_character") == "balloonist":
            current["name"] = f"气球驾驶员（{label}）"
            current["reminder"] = reminder
        return workflow

    @staticmethod
    def balloonist_version_from_save(payload: dict) -> str | None:
        version = payload.get("balloonist_version")
        return version if version in ("new", "old") else None

    def _balloonist_target(self, target: int | str) -> dict:
        if isinstance(target, int) and not isinstance(target, bool):
            state = self.seat_state(target)
            role_id = state.character_id
            if role_id is None or role_id not in self.roles:
                raise ValueError("目标座位尚无角色")
            role = self.roles[role_id]
            options = {
                "recluse": ["outsider", "minion", "demon"],
                "spy": ["minion", "townsfolk", "outsider"],
            }.get(role_id, [role["team"]])
            return {"target": target, "target_label": f"{target}号",
                    "real_role": role_id, "real_role_name": role["name"],
                    "real_type": role["team"], "options": options}
        if isinstance(target, str):
            traveler = next((item for item in self.travelers if item["id"] == target), None)
            if traveler is None or traveler.get("role_id") not in TRAVELER_BY_ID:
                raise ValueError("旅行者不存在或尚未配置角色")
            return {"target": target,
                    "target_label": f"旅行者 {traveler['name']}（{target}）",
                    "real_role": traveler["role_id"],
                    "real_role_name": TRAVELER_BY_ID[traveler["role_id"]]["name"],
                    "real_type": "traveler", "options": ["traveler"]}
        raise ValueError("目标必须是座位号或旅行者标识")

    def _balloonist_active_by_night(self, actor_seat: int) -> dict[int, dict]:
        event_states = {event.id: event.state for event in self.journal_events}
        effective: dict[int, dict] = {}
        for record in self.balloonist_events:
            if (record["actor_seat"] == actor_seat
                    and event_states.get(record["event_id"]) == "active"):
                effective[record["night_no"]] = record
        return effective

    def balloonist_context(self, actor_seat: int) -> dict:
        if self.balloonist_version not in ("new", "old"):
            return {"version": None, "previous_type": None, "used_types": [],
                    "candidates": [], "manual_adjudication_required": True,
                    "exhausted": False, "impairments": []}
        effective = self._balloonist_active_by_night(actor_seat)
        prior = [record for night, record in effective.items() if night < self.night_no]
        prior.sort(key=lambda item: item["night_no"])
        previous = prior[-1]["registered_type"] if prior else None
        used = {record["registered_type"] for record in prior}
        targets = []
        for seat in sorted(self.seat_states):
            if self.seat_state(seat).character_id:
                targets.append(self._balloonist_target(seat))
        for traveler in self.travelers:
            if traveler.get("role_id") in TRAVELER_BY_ID:
                targets.append(self._balloonist_target(traveler["id"]))
        candidates = [{**target, "rule_compliant_types": _allowed_types(
            self.balloonist_version, previous, used, target["options"])}
                      for target in targets]
        normal_candidates = [target for target in candidates if target["rule_compliant_types"]]
        exhausted = (self.balloonist_version == "old" and bool(prior)
                     and not normal_candidates)
        _, impairments = self._balloonist_impairments(actor_seat)
        candidates = ([] if exhausted else candidates if impairments else normal_candidates)
        candidates = [{**target, "allowed_types": (
            target["options"] if impairments else target["rule_compliant_types"])}
                      for target in candidates]
        return {"version": self.balloonist_version, "previous_type": previous,
                "used_types": sorted(used), "candidates": candidates,
                "manual_adjudication_required": not candidates and not exhausted,
                "exhausted": exhausted, "impairments": impairments}

    def preview_balloonist(self, step_id: str, target: int | str, *,
                           registered_type: str | None = None,
                           registered_role: str | None = None,
                           truthful: bool | None = None) -> dict:
        if self.balloonist_version not in ("new", "old"):
            raise ValueError("旧局没有气球驾驶员版本；请继续手动执行，不补造历史")
        if self.status != "playing" or self.phase != "night":
            raise ValueError("只能在夜晚发送气球驾驶员信息")
        step = self.night.step(step_id)
        if (step.id != self.night.queue.current_step_id or step.actor_seat is None
                or step.source.get("ability_character") != "balloonist"
                or step.status not in ("upcoming", "current")):
            raise ValueError("当前步骤不是气球驾驶员")
        target_info = self._balloonist_target(target)
        role_id = target_info["real_role"]
        if role_id in ("recluse", "spy") and registered_type is None:
            raise ValueError("陌客或间谍必须明确选择本次登记类型")
        registration = registered_type or target_info["real_type"]
        if registration not in target_info["options"]:
            raise ValueError("该角色不能登记为所选类型")
        if role_id not in ("recluse", "spy") and registered_role not in (None, role_id):
            raise ValueError("普通角色只能按真实角色登记")
        if registration == target_info["real_type"] and registered_role is None:
            registered_role = role_id
        if registered_role is not None:
            role = (TRAVELER_BY_ID.get(registered_role) if registration == "traveler"
                    else self.roles.get(registered_role))
            if role is None or role["team"] != registration:
                raise ValueError("登记角色与登记类型不一致")
        else:
            raise ValueError("选择不同登记类型时必须指定登记角色")
        context = self.balloonist_context(step.actor_seat)
        allowed = _allowed_types(self.balloonist_version, context["previous_type"],
                                 set(context["used_types"]), [registration])
        rule_compliant = bool(allowed)
        effect_snapshot, impairments = self._balloonist_impairments(step.actor_seat)
        impaired = bool(impairments)
        if not rule_compliant and not impaired:
            raise ValueError("目标登记类型不符合当前版本的夜间类型顺序")
        if impaired and truthful is None:
            raise ValueError("信息受影响时必须明确标记本次信息真假")
        if not rule_compliant and truthful is not False:
            raise ValueError("违反正常类型顺序的信息必须标为错误")
        if "vortox_forced_false" in impairments and truthful is not False:
            raise ValueError("涡流影响下气球驾驶员信息必须标为错误")
        if not impaired and truthful is False:
            raise ValueError("正常信息不能标为错误")
        return {**target_info, "night_no": self.night_no,
                "actor_seat": step.actor_seat,
                "recipient_player_id": self.seat_state(step.actor_seat).claimed_by,
                "registered_role": registered_role,
                "registered_type": registration,
                "registration_reason": (
                    f"{role_id}_registration" if role_id in ("recluse", "spy")
                    else "real_role"),
                "effect_snapshot": effect_snapshot,
                "impairments": list(dict.fromkeys(impairments)),
                "rule_compliant": rule_compliant,
                "truthful": True if truthful is None else truthful,
                "step_id": step_id}

    def send_balloonist(self, step_id: str, target: int | str, *,
                        registered_type: str | None = None,
                        registered_role: str | None = None,
                        truthful: bool | None = None,
                        correction_of: str | None = None) -> dict:
        preview = self.preview_balloonist(
            step_id, target, registered_type=registered_type,
            registered_role=registered_role, truthful=truthful,
        )
        current = self._balloonist_active_by_night(preview["actor_seat"]).get(self.night_no)
        if current and correction_of != current["event_id"]:
            raise ValueError("本夜信息已发送；更正须引用原信息")
        if not current and correction_of is not None:
            raise ValueError("没有可更正的本夜信息")
        event = self.journal.append(
            "balloonist_information",
            {"actor_seat": preview["actor_seat"], "night_no": self.night_no,
             "target": target, "registered_type": preview["registered_type"],
             "step_id": step_id,
             "correction_of": correction_of},
            {"op": "noop"},
            depends_on=[correction_of] if correction_of else [],
        )
        record = {**preview, "event_id": event.id,
                  "sent_at": timestamp(), "correction_of": correction_of}
        self.balloonist_events.append(deepcopy(record))
        self.night.record_fields(step_id, {"balloonist_sent": event.id})
        return record

    def balloonist_storyteller_history(self) -> list[dict]:
        states = {event.id: event.state for event in self.journal_events}
        return [{**deepcopy(record), "retracted": states.get(record["event_id"]) == "undone"}
                for record in self.balloonist_events]

    def bind_balloonist_claim(self, seat: int, player_id: str) -> None:
        for record in self.balloonist_events:
            if record["actor_seat"] == seat and record["recipient_player_id"] is None:
                record["recipient_player_id"] = player_id

    def balloonist_player_history(self, player_id: str) -> list[dict]:
        states = {event.id: event.state for event in self.journal_events}
        return [{"night_no": record["night_no"], "target": record["target"],
                 "target_label": record["target_label"],
                 "retracted": states.get(record["event_id"]) == "undone"}
                for record in self.balloonist_events
                if record["recipient_player_id"] == player_id]
