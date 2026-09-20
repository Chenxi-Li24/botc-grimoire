"""Sourced, historical status effects with semantic lifetimes."""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4

from ..state import GameState
from .models import EffectRecord, timestamp


class EffectLedger:
    VALID_STATES = {"active", "suspended", "ended"}
    LIFETIMES = {
        "until_dusk", "until_next_choice", "while_source_has_ability",
        "round_count", "game_long", "manual",
    }

    def __init__(self, state: GameState) -> None:
        self.state = state

    def get(self, effect_id: str) -> EffectRecord:
        try:
            return self.state.effect_records[effect_id]
        except KeyError as exc:
            raise KeyError(effect_id) from exc

    def apply(self, effect_type: str, target_seat: int, *, source_event: str,
              source_seat: int | None = None, source_character: str | None = None,
              payload: dict[str, Any] | None = None,
              lifetime_policy: dict[str, Any] | None = None,
              effect_id: str | None = None) -> EffectRecord:
        self.state.seat(target_seat)
        policy = deepcopy(lifetime_policy or {"kind": "manual"})
        kind = policy.get("kind")
        if kind not in self.LIFETIMES:
            raise ValueError(f"unsupported effect lifetime: {kind}")
        if kind == "round_count" and int(policy.get("remaining", 0)) < 1:
            raise ValueError("round_count lifetime needs a positive remaining count")
        effect = EffectRecord(
            id=effect_id or uuid4().hex,
            type=effect_type,
            target_seat=target_seat,
            source_seat=source_seat,
            source_character=source_character,
            source_event=source_event,
            payload=deepcopy(payload or {}),
            lifetime_policy=policy,
            state="active",
            transitions=[{"at": timestamp(), "from": None, "to": "active",
                          "reason": "applied"}],
            expected_end=policy.get("expected_end") or self._expected_end(policy),
        )
        if effect.id in self.state.effect_records:
            raise ValueError(f"duplicate effect id: {effect.id}")
        self.state.effect_records[effect.id] = effect
        self.state.seat(target_seat).effect_ids.append(effect.id)
        return effect

    @staticmethod
    def _expected_end(policy: dict[str, Any]) -> str | None:
        kind = policy.get("kind")
        labels = {
            "until_dusk": "next_dusk",
            "until_next_choice": "next_applicable_choice",
            "while_source_has_ability": "source_loses_ability_permanently",
            "game_long": "game_end",
            "manual": None,
        }
        if kind == "round_count":
            return f"after_{policy.get('remaining')}_{policy.get('trigger', 'round')}"
        return labels.get(kind)

    def transition(self, effect_id: str, state: str, reason: str, *,
                   trigger: str | None = None) -> EffectRecord:
        if state not in self.VALID_STATES:
            raise ValueError(f"invalid effect state: {state}")
        effect = self.get(effect_id)
        if effect.state == state:
            return effect
        if effect.state == "ended":
            raise ValueError("ended effects cannot transition")
        if effect.state == "active" and state not in {"suspended", "ended"}:
            raise ValueError("active effect can only suspend or end")
        if effect.state == "suspended" and state not in {"active", "ended"}:
            raise ValueError("suspended effect can only resume or end")
        previous = effect.state
        effect.state = state
        effect.transitions.append({"at": timestamp(), "from": previous, "to": state,
                                   "reason": reason, "trigger": trigger})
        seat = self.state.seat(effect.target_seat)
        if state == "ended" and effect.id in seat.effect_ids:
            seat.effect_ids.remove(effect.id)
        elif state != "ended" and effect.id not in seat.effect_ids:
            seat.effect_ids.append(effect.id)
        return effect

    def advance(self, trigger: str, *, source_seat: int | None = None,
                source_active: bool | None = None, permanent: bool = False,
                reason: str | None = None) -> list[EffectRecord]:
        changed: list[EffectRecord] = []
        for effect in list(self.state.effect_records.values()):
            if effect.state == "ended":
                continue
            if source_seat is not None and effect.source_seat != source_seat:
                continue
            policy = effect.lifetime_policy
            kind = policy.get("kind")

            source_trigger = source_active is not None or trigger in {
                "source_inactive", "source_active", "source_lost", "source_death",
            }
            if source_trigger:
                active = source_active if source_active is not None else trigger == "source_active"
                terminal = permanent or trigger in {"source_lost", "source_death"}
                follows_source = (kind == "while_source_has_ability"
                                  or policy.get("suspend_with_source")
                                  or policy.get("end_on_source_loss"))
                if not follows_source:
                    continue
                if terminal and policy.get("end_on_source_loss", True):
                    changed.append(self.transition(
                        effect.id, "ended", reason or "source_lost_permanently", trigger=trigger,
                    ))
                elif not active and effect.state == "active":
                    changed.append(self.transition(
                        effect.id, "suspended", reason or "source_ability_inactive", trigger=trigger,
                    ))
                elif active and effect.state == "suspended":
                    changed.append(self.transition(
                        effect.id, "active", reason or "source_ability_restored", trigger=trigger,
                    ))
                continue

            if kind == "until_dusk" and trigger == "dusk":
                changed.append(self.transition(effect.id, "ended", reason or "reached_dusk",
                                               trigger=trigger))
            elif kind == "until_next_choice" and trigger == "next_choice":
                changed.append(self.transition(effect.id, "ended", reason or "replaced_by_choice",
                                               trigger=trigger))
            elif kind == "round_count" and trigger == policy.get("trigger", "round"):
                policy["remaining"] = int(policy["remaining"]) - 1
                if policy["remaining"] <= 0:
                    changed.append(self.transition(effect.id, "ended", reason or "rounds_elapsed",
                                                   trigger=trigger))
                else:
                    effect.transitions.append({"at": timestamp(), "from": effect.state,
                                               "to": effect.state, "reason": "round_advanced",
                                               "trigger": trigger,
                                               "remaining": policy["remaining"]})
                    changed.append(effect)
            elif kind == "game_long" and trigger == "game_end":
                changed.append(self.transition(effect.id, "ended", reason or "game_ended",
                                               trigger=trigger))
        return changed

    def current_for_seat(self, seat: int) -> list[EffectRecord]:
        return [effect for effect in self.state.effect_records.values()
                if effect.target_seat == seat and effect.state != "ended"]

    def active_for_seat(self, seat: int) -> list[EffectRecord]:
        return [effect for effect in self.current_for_seat(seat) if effect.state == "active"]

    def history_for_seat(self, seat: int) -> list[EffectRecord]:
        return [effect for effect in self.state.effect_records.values()
                if effect.target_seat == seat]

    def projection(self, seat: int) -> dict[str, list[dict[str, Any]]]:
        current = self.current_for_seat(seat)
        history = self.history_for_seat(seat)
        return {
            "badges": [{"id": item.id, "type": item.type, "state": item.state,
                        "source_seat": item.source_seat,
                        "source_character": item.source_character,
                        "expected_end": item.expected_end}
                       for item in current],
            "history": [item.to_dict() for item in history],
        }
