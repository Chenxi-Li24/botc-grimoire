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

    def _apply(self, effect_type: str, source: int, target: int, *,
               source_character: str, payload: dict,
               lifetime_policy: dict,
               depends_on: list[str] | None = None) -> EffectRecord:
        effect_id = uuid4().hex
        event = self.night.journal.append(
            f"{source_character}_effect_applied",
            {"source_seat": source, "target_seat": target,
             "effect_type": effect_type, "payload": payload},
            {"op": "end_effect", "effect_id": effect_id},
            depends_on=depends_on or [],
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
        for effect in previous:
            replacement = self.night.journal.append(
                "cerenovus_effect_replaced",
                {"effect_id": effect.id, "source_seat": source,
                 "target_seat": target},
                {"op": "restore_effect", "effect": effect.to_dict()},
                depends_on=[effect.source_event],
            )
            replacement_events.append(replacement.id)
            self.night.effects.transition(effect.id, "ended", "replaced_by_next_choice",
                                          trigger="next_choice")
        return self._apply(
            "mad", source, target,
            source_character="cerenovus",
            payload={"claimed_character": claimed_character,
                     "chosen_night": self.night.queue.night_no,
                     "replaces": [effect.id for effect in previous]},
            lifetime_policy={"kind": "until_next_choice",
                             "expected_end": "next_cerenovus_choice"},
            depends_on=replacement_events,
        )

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
        event = self.night.journal.append(
            "source_ability_changed",
            {"source_seat": source, "source_character": source_character,
             "active": active, "permanent": permanent},
            {"op": "batch", "operations": [
                {"op": "set",
                 "path": ["seats", source, "ability_state", source_character],
                 "value": previous_ability},
                *({"op": "restore_effect", "effect": effect} for effect in before),
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
        return changed
