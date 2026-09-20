"""Preview-first, transaction-scoped Pit-Hag transformations."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from ...night_order import night_positions
from ..models import EventRecord
from ..queue import NightStep

if TYPE_CHECKING:
    from ..service import NightService


@dataclass
class PitHagPreview:
    id: str
    actor_seat: int
    target_seat: int
    old_character: str
    new_character: str
    alignment: str
    in_play_conflict: bool
    relative_order: str
    future_step_changes: list[dict[str, Any]]
    immediate_start_knowing: bool
    creates_demon: bool
    demon_consequences: list[str]
    status: str = "pending"
    warnings: list[str] = field(default_factory=list)
    event_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PitHagPreview":
        return cls(**value)


class PitHagHandler:
    def __init__(self, night: "NightService") -> None:
        self.night = night

    def _positions(self) -> tuple[dict[str, int], int]:
        kind = "first" if self.night.queue.night_no == 1 else "other"
        positions = night_positions(self.night.pack.id, kind)
        return positions, positions.get("pithag", -1)

    def preview(self, actor: int, target: int, character: str) -> PitHagPreview:
        actor_state = self.night.state.seat(actor)
        target_state = self.night.state.seat(target)
        if actor_state.character_id != "pithag":
            raise ValueError("actor is not Pit-Hag")
        if target_state.character_id is None:
            raise ValueError("target seat has no character")
        if character not in self.night.pack.character_by_id:
            raise ValueError("new character is not in this script")
        conflict = any(seat.character_id == character
                       for seat in self.night.state.seats.values())
        spec = self.night.pack.character_by_id[character]
        positions, pit_hag_position = self._positions()
        character_position = positions.get(character)
        start_knowing = spec.night.first_trigger == "start-knowing"
        if start_knowing:
            relative = "immediate_start_knowing"
        elif character_position is None:
            relative = "passive_or_no_action"
        elif character_position > pit_hag_position:
            relative = "later_this_night"
        else:
            relative = "next_night"
        changes = [{"kind": "remove_unexecuted", "character": target_state.character_id,
                    "seat": target}]
        if start_knowing:
            changes.append({"kind": "insert_immediate_start_knowing",
                            "character": character, "seat": target})
        if relative == "later_this_night":
            changes.append({"kind": "insert_standard_action",
                            "character": character, "seat": target})
        elif relative == "next_night":
            changes.append({"kind": "defer_standard_action",
                            "character": character, "seat": target})
        creates_demon = spec.team == "demon"
        consequences = []
        if creates_demon:
            consequences = [
                "all_deaths_this_night_are_storyteller_arbitrary",
                "created_demon_has_no_normal_kill_choice_this_night",
                "passive_and_non_kill_ability_parts_start_immediately",
                "demon_kill_only_triggers_do_not_fire_for_arbitrary_deaths",
            ]
        warnings = []
        if conflict:
            warnings.append("character_already_in_play_silent_failure")
        if character in {"drunk", "lunatic"}:
            warnings.append("cognitive_override_must_be_assigned")
        preview = PitHagPreview(
            id=uuid4().hex,
            actor_seat=actor,
            target_seat=target,
            old_character=target_state.character_id,
            new_character=character,
            alignment=target_state.alignment,
            in_play_conflict=conflict,
            relative_order=relative,
            future_step_changes=changes,
            immediate_start_knowing=start_knowing,
            creates_demon=creates_demon,
            demon_consequences=consequences,
            warnings=warnings,
        )
        self.night.state.pending_transformations[preview.id] = preview.to_dict()
        return preview

    def _no_dashii_neighbors(self, source: int) -> list[int]:
        occupied = sorted((seat for seat in self.night.state.seats.values()
                           if seat.character_id), key=lambda seat: seat.seat)
        indexes = {seat.seat: index for index, seat in enumerate(occupied)}
        if source not in indexes:
            return []
        result = []
        origin = indexes[source]
        for direction in (-1, 1):
            for distance in range(1, len(occupied)):
                seat = occupied[(origin + direction * distance) % len(occupied)]
                spec = self.night.pack.character_by_id.get(seat.character_id or "")
                if spec and spec.team == "townsfolk":
                    result.append(seat.seat)
                    break
        return list(dict.fromkeys(result))

    def confirm(self, preview_id: str) -> EventRecord:
        try:
            stored = self.night.state.pending_transformations[preview_id]
        except KeyError as exc:
            raise KeyError(preview_id) from exc
        preview = PitHagPreview.from_dict(stored)
        if preview.status != "pending":
            raise ValueError("Pit-Hag preview is no longer pending")
        target = self.night.state.seat(preview.target_seat)
        if target.character_id != preview.old_character:
            raise ValueError("target character changed; preview is stale")
        transaction_id = uuid4().hex
        if preview.in_play_conflict:
            event = self.night.journal.append(
                "pit_hag_silent_failure",
                {"preview_id": preview.id, "actor_seat": preview.actor_seat,
                 "target_seat": preview.target_seat,
                 "character": preview.new_character},
                {"op": "batch", "operations": [
                    {"op": "set",
                     "path": ["pending_transformations", preview.id, "status"],
                     "value": "pending"},
                    {"op": "set",
                     "path": ["pending_transformations", preview.id, "event_id"],
                     "value": None},
                ]},
                transaction_id=transaction_id,
            )
            self.night.state.pending_transformations[preview.id]["event_id"] = event.id
            stored["status"] = "silent_failure"
            return event

        sourced_effects = [
            effect for effect in self.night.state.effect_records.values()
            if effect.source_seat == preview.target_seat
            and effect.source_character == preview.old_character
            and effect.state != "ended"
        ]
        sourced_mad_about = {
            effect.target_seat: self.night.state.seat(effect.target_seat).mad_about
            for effect in sourced_effects if effect.type == "mad"
        }
        no_dashii_targets = (self._no_dashii_neighbors(preview.target_seat)
                              if preview.new_character == "nodashii" else [])
        no_dashii_effects = {seat: uuid4().hex for seat in no_dashii_targets}
        inverse_operations = [
            {"op": "set", "path": ["seats", preview.target_seat, "character_id"],
             "value": preview.old_character},
            {"op": "set", "path": ["seats", preview.target_seat, "alignment"],
             "value": preview.alignment},
            {"op": "set", "path": ["seats", preview.target_seat, "ability_state"],
             "value": deepcopy(target.ability_state)},
            {"op": "set", "path": ["seats", preview.actor_seat, "ability_state"],
             "value": deepcopy(self.night.state.seat(preview.actor_seat).ability_state)},
            {"op": "set", "path": ["seats", preview.target_seat,
                                     "perceived_character_id"],
             "value": target.perceived_character_id},
            {"op": "set", "path": ["seats", preview.target_seat, "role_change_notice"],
             "value": target.role_change_notice},
            {"op": "set", "path": ["pending_transformations", preview.id, "status"],
             "value": "pending"},
            {"op": "set", "path": ["pending_transformations", preview.id, "event_id"],
             "value": None},
            *({"op": "restore_effect", "effect": effect.to_dict()}
              for effect in sourced_effects),
            *({"op": "set", "path": ["seats", seat, "mad_about"],
               "value": value}
              for seat, value in sourced_mad_about.items()),
            *({"op": "end_effect", "effect_id": effect_id}
              for effect_id in no_dashii_effects.values()),
        ]
        event = self.night.journal.append(
            "pit_hag_transformation",
            {"preview_id": preview.id, "actor_seat": preview.actor_seat,
             "target_seat": preview.target_seat,
             "from": preview.old_character, "to": preview.new_character,
             "alignment_before": preview.alignment,
             "alignment_after": preview.alignment,
             "creates_demon": preview.creates_demon},
            {"op": "batch", "operations": inverse_operations},
            transaction_id=transaction_id,
        )
        target.character_id = preview.new_character
        target.perceived_character_id = None
        target.role_change_notice = preview.new_character
        for effect in sourced_effects:
            self.night.effects.transition(effect.id, "ended", "source_character_changed",
                                          trigger="source_lost")
            effect.transitions[-1]["source_event"] = event.id
            if effect.type == "mad":
                target_state = self.night.state.seat(effect.target_seat)
                if target_state.mad_about == effect.payload.get("claimed_character"):
                    target_state.mad_about = None
        for seat, effect_id in no_dashii_effects.items():
            self.night.effects.apply(
                "poisoned",
                seat,
                source_event=event.id,
                source_seat=preview.target_seat,
                source_character="nodashii",
                payload={"no_dashii_neighbor": True},
                lifetime_policy={"kind": "while_source_has_ability",
                                 "suspend_with_source": True,
                                 "end_on_source_loss": True},
                effect_id=effect_id,
            )
        stored["status"] = "confirmed"
        stored["event_id"] = event.id
        if preview.creates_demon:
            ability = target.ability_state.setdefault(preview.new_character, {})
            ability["created_demon_no_kill_night"] = self.night.queue.night_no
            pit_hag_state = self.night.state.seat(preview.actor_seat).ability_state.setdefault(
                "pithag", {},
            )
            nights = pit_hag_state.setdefault("arbitrary_death_nights", [])
            if self.night.queue.night_no not in nights:
                nights.append(self.night.queue.night_no)
            pit_hag_state["arbitrary_death_source"] = {
                "seat": preview.actor_seat,
                "character": "pithag",
                "event_id": event.id,
            }

        self.night.queue.rebuild_suffix(event.id)
        created_step = next((step for step in self.night.queue.steps
                             if step.actor_seat == preview.target_seat
                             and step.character_id == preview.new_character
                             and step.status == "upcoming"), None)
        if created_step and preview.relative_order == "later_this_night":
            created_step.trigger = "created"
            if event.id not in created_step.depends_on:
                created_step.depends_on.append(event.id)
        if created_step and preview.creates_demon:
            created_step.status = "skipped"
            created_step.skip_reason = "created_demon_no_kill_this_night"
        if preview.immediate_start_knowing:
            current = self.night.queue.current
            order = (current.order + 1) if current else 1
            spec = self.night.pack.character_by_id[preview.new_character]
            immediate = NightStep(
                id=f"night:{self.night.queue.night_no}:created-start:{event.id}",
                actor_seat=preview.target_seat,
                character_id=preview.new_character,
                perceived_as=None,
                trigger="start-knowing",
                order=order,
                required_fields=self.night.queue._required_fields(spec),
                depends_on=[event.id],
                source={"created_by": "pithag", "created_event": event.id},
                name=self.night.pack.locale.get(spec.name_key, spec.english_name),
                reminder=self.night.pack.locale.get(spec.ability_key, ""),
            )
            self.night.queue.steps.append(immediate)
            self.night.queue.steps.sort(key=lambda step: (step.order, step.actor_seat or 0,
                                                           step.id))
        return event
