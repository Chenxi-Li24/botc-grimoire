"""Reusable handlers for sourced, timed poison and madness effects."""

from __future__ import annotations

from copy import deepcopy
from typing import TYPE_CHECKING
from uuid import uuid4

from ..models import EffectRecord

if TYPE_CHECKING:
    from ..service import NightService


class StatusRoleHandlers:
    def __init__(self, night: "NightService") -> None:
        self.night = night

    def _validate_source(self, source: int, character: str) -> None:
        holder = self.night.state.seat(source)
        if holder.character_id != character:
            raise ValueError(f"source seat is not {character}")

    def _validate_target(self, target: int) -> None:
        if self.night.state.seat(target).character_id is None:
            raise ValueError("target seat has no character")

    def _apply(self, effect_type: str, source: int, target: int, *,
               source_character: str, payload: dict,
               lifetime_policy: dict,
               depends_on: list[str] | None = None,
               inverse_operations: list[dict] | None = None,
               transaction_id: str | None = None) -> EffectRecord:
        effect_id = uuid4().hex
        event = self.night.journal.append(
            f"{source_character}_effect_applied",
            {"source_seat": source, "target_seat": target,
             "effect_type": effect_type, "payload": payload},
            {"op": "batch", "operations": [
                {"op": "end_effect", "effect_id": effect_id},
                *(inverse_operations or []),
            ]},
            depends_on=depends_on or [],
            transaction_id=transaction_id,
        )
        effect = self.night.effects.apply(
            effect_type,
            target,
            source_event=event.id,
            source_seat=source,
            source_character=source_character,
            payload=payload,
            lifetime_policy=lifetime_policy,
            effect_id=effect_id,
        )
        return effect

    def apply_poisoner(self, source: int, target: int) -> EffectRecord:
        self._validate_source(source, "poisoner")
        self._validate_target(target)
        return self._apply(
            "poisoned", source, target,
            source_character="poisoner",
            payload={"chosen_night": self.night.queue.night_no},
            lifetime_policy={
                "kind": "until_dusk",
                "suspend_with_source": True,
                "end_on_source_loss": True,
                "expected_end": f"dusk_after_day_{self.night.queue.night_no}",
            },
        )

    def apply_widow(self, source: int, target: int) -> EffectRecord:
        self._validate_source(source, "widow")
        self._validate_target(target)
        return self._apply(
            "poisoned", source, target,
            source_character="widow",
            payload={"chosen_night": self.night.queue.night_no,
                     "widow_poison": True},
            lifetime_policy={
                "kind": "while_source_has_ability",
                "suspend_with_source": True,
                "end_on_source_loss": True,
            },
        )

    def apply_cerenovus(self, source: int, target: int,
                        claimed_character: str) -> EffectRecord:
        self._validate_source(source, "cerenovus")
        self._validate_target(target)
        if claimed_character not in self.night.pack.character_by_id:
            raise ValueError("claimed character is not in this script")
        team = self.night.pack.character_by_id[claimed_character].team
        if team not in {"townsfolk", "outsider"}:
            raise ValueError("Cerenovus madness must name a good character")
        previous = [
            effect for effect in self.night.state.effect_records.values()
            if effect.type == "mad" and effect.source_seat == source
            and effect.source_character == "cerenovus"
            and effect.state != "ended"
        ]
        replacement_events = []
        transaction_id = uuid4().hex
        for effect in previous:
            target_state = self.night.state.seat(effect.target_seat)
            replacement = self.night.journal.append(
                "cerenovus_effect_replaced",
                {"effect_id": effect.id, "source_seat": source,
                 "target_seat": target},
                {"op": "batch", "operations": [
                    {"op": "restore_effect", "effect": effect.to_dict()},
                    {"op": "set",
                     "path": ["seats", effect.target_seat, "mad_about"],
                     "value": target_state.mad_about},
                ]},
                depends_on=[effect.source_event],
                transaction_id=transaction_id,
            )
            replacement_events.append(replacement.id)
            self.night.effects.transition(effect.id, "ended", "replaced_by_next_choice",
                                          trigger="next_choice")
            target_state.mad_about = None
        target_state = self.night.state.seat(target)
        previous_mad_about = target_state.mad_about
        effect = self._apply(
            "mad", source, target,
            source_character="cerenovus",
            payload={"claimed_character": claimed_character,
                     "chosen_night": self.night.queue.night_no,
                     "replaces": [effect.id for effect in previous]},
            lifetime_policy={"kind": "until_next_choice",
                             "expected_end": "next_cerenovus_choice",
                             "suspend_with_source": True,
                             "end_on_source_loss": True},
            depends_on=replacement_events,
            inverse_operations=[
                {"op": "set", "path": ["seats", target, "mad_about"],
                 "value": previous_mad_about},
            ],
            transaction_id=transaction_id,
        )
        target_state.mad_about = claimed_character
        return effect

    def set_source_ability(self, source: int, *, active: bool,
                           permanent: bool = False) -> list[EffectRecord]:
        holder = self.night.state.seat(source)
        source_character = holder.character_id
        if source_character is None:
            raise ValueError("source seat has no character")
        ability = holder.ability_state.setdefault(source_character, {})
        previous_ability = deepcopy(ability)
        before = [effect.to_dict() for effect in self.night.state.effect_records.values()
                  if effect.source_seat == source and effect.state != "ended"]
        mad_about_before = {
            effect.target_seat: self.night.state.seat(effect.target_seat).mad_about
            for effect in self.night.state.effect_records.values()
            if effect.source_seat == source and effect.state != "ended"
            and effect.type == "mad"
        }
        event = self.night.journal.append(
            "source_ability_changed",
            {"source_seat": source, "source_character": source_character,
             "active": active, "permanent": permanent},
            {"op": "batch", "operations": [
                {"op": "set",
                 "path": ["seats", source, "ability_state", source_character],
                 "value": previous_ability},
                *({"op": "restore_effect", "effect": effect} for effect in before),
                *({"op": "set", "path": ["seats", seat, "mad_about"],
                   "value": value}
                  for seat, value in mad_about_before.items()),
            ]},
        )
        ability["active"] = bool(active)
        if permanent:
            ability["lost_permanently"] = not active
        elif active:
            ability.pop("lost_permanently", None)
        changed = self.night.effects.advance(
            "source_active" if active else "source_lost" if permanent else "source_inactive",
            source_seat=source,
            source_character=source_character,
            source_active=active,
            permanent=permanent,
            reason=("source_ability_restored" if active else
                    "source_lost_permanently" if permanent else
                    "source_temporarily_incapacitated"),
        )
        for effect in changed:
            effect.transitions[-1]["source_event"] = event.id
            if effect.type == "mad" and effect.state == "ended":
                target_state = self.night.state.seat(effect.target_seat)
                if target_state.mad_about == effect.payload.get("claimed_character"):
                    target_state.mad_about = None
        return changed
