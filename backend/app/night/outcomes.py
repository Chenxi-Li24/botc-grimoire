"""Storyteller adjudication for choices that may cause confidential outcomes."""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from uuid import uuid4

from ..catalog import ScriptPack
from ..state import GameState
from .effects import EffectLedger
from .journal import EventJournal
from .models import PendingOutcome, timestamp
from .queue import NightQueue


class OutcomeConflict(RuntimeError):
    pass


class OutcomeAdjudicator:
    RESOLUTIONS = {
        "secret_death", "no_death", "delayed", "redirected",
        "transformation", "choice_only",
    }
    PROTECTION_TYPES = {
        "protected", "death_immunity", "monk_protection", "innkeeper_protection",
        "sailor_safe", "tea_lady_safe", "devils_advocate_protection",
    }
    INCAPACITY_TYPES = {"poisoned", "drunk"}

    def __init__(self, state: GameState, pack: ScriptPack, journal: EventJournal,
                 effects: EffectLedger, queue: NightQueue) -> None:
        self.state = state
        self.pack = pack
        self.journal = journal
        self.effects = effects
        self.queue = queue

    def get(self, outcome_id: str) -> PendingOutcome:
        try:
            return self.state.pending_outcomes[outcome_id]
        except KeyError as exc:
            raise KeyError(outcome_id) from exc

    def _hints(self, source_seat: int | None, source_character: str,
               selected_seats: list[int], metadata: dict[str, Any]) -> list[dict]:
        hints: list[dict] = []
        if source_seat is not None:
            for effect in self.effects.active_for_seat(source_seat):
                if effect.type in self.INCAPACITY_TYPES:
                    hints.append({
                        "kind": "source_incapacity",
                        "seat": source_seat,
                        "effect_id": effect.id,
                        "effect_type": effect.type,
                    })
        for target in selected_seats:
            seat = self.state.seat(target)
            if not seat.alive:
                hints.append({"kind": "already_dead", "seat": target,
                              "death_event": seat.died_at})
            for effect in self.effects.active_for_seat(target):
                if (effect.type in self.PROTECTION_TYPES
                        or effect.payload.get("prevents_death")):
                    hints.append({
                        "kind": "protection",
                        "seat": target,
                        "effect_id": effect.id,
                        "effect_type": effect.type,
                        "source_seat": effect.source_seat,
                    })
            ability = seat.ability_state.get(seat.character_id or "", {})
            if ability.get("death_replacement"):
                hints.append({"kind": "replacement", "seat": target,
                              "rule": ability["death_replacement"]})
            if seat.character_id == "soldier" and metadata.get("is_demon_attack"):
                hints.append({"kind": "special_character", "seat": target,
                              "character_id": "soldier", "rule": "demon_immune"})
            if seat.character_id == "mayor" and metadata.get("is_demon_attack"):
                hints.append({"kind": "special_character", "seat": target,
                              "character_id": "mayor", "rule": "possible_redirect"})
        if metadata.get("arbitrary"):
            hints.append({"kind": "storyteller_arbitrary_death"})
        return hints

    def create(self, *, source_event: str, source_seat: int | None,
               source_character: str, selected_seats: list[int],
               metadata: dict[str, Any] | None = None) -> PendingOutcome:
        selected = list(dict.fromkeys(int(seat) for seat in selected_seats))
        for seat in selected:
            self.state.seat(seat)
        meta = deepcopy(metadata or {})
        outcome_id = uuid4().hex
        known = {event.id for event in self.journal.records}
        created = self.journal.append(
            "pending_outcome_created",
            {"outcome_id": outcome_id, "source_seat": source_seat,
             "source_character": source_character, "selected_seats": selected},
            {"op": "delete", "path": ["pending_outcomes", outcome_id]},
            depends_on=[source_event] if source_event in known else [],
        )
        outcome = PendingOutcome(
            id=outcome_id,
            source_event=source_event,
            source_seat=source_seat,
            source_character=source_character,
            selected_seats=selected,
            hints=self._hints(source_seat, source_character, selected, meta),
            created_event=created.id,
            metadata=meta,
        )
        self.state.pending_outcomes[outcome.id] = outcome
        return outcome

    @staticmethod
    def _restore_operations(outcome: PendingOutcome,
                            state: GameState) -> list[dict[str, Any]]:
        operations: list[dict[str, Any]] = [
            {"op": "set", "path": ["pending_outcomes", outcome.id, "resolution"],
             "value": outcome.resolution},
            {"op": "set", "path": ["pending_outcomes", outcome.id, "affected_seats"],
             "value": list(outcome.affected_seats)},
            {"op": "set", "path": ["pending_outcomes", outcome.id, "resolution_event"],
             "value": outcome.resolution_event},
            {"op": "set", "path": ["pending_outcomes", outcome.id, "status"],
             "value": outcome.status},
            {"op": "set", "path": ["pending_outcomes", outcome.id, "resolved_at"],
             "value": outcome.resolved_at},
            {"op": "set", "path": ["pending_outcomes", outcome.id, "metadata"],
             "value": deepcopy(outcome.metadata)},
        ]
        return operations

    def resolve(self, outcome_id: str, resolution: str, *,
                affected_seats: list[int] | None = None,
                details: dict[str, Any] | None = None) -> PendingOutcome:
        if resolution not in self.RESOLUTIONS:
            raise ValueError(f"unsupported outcome resolution: {resolution}")
        outcome = self.get(outcome_id)
        if outcome.status != "pending":
            raise OutcomeConflict("outcome has already been resolved")
        details = deepcopy(details or {})
        affected = list(dict.fromkeys(int(seat) for seat in (affected_seats or ())))
        if resolution == "secret_death" and not affected:
            affected = list(outcome.selected_seats)
        if resolution == "redirected" and not affected:
            raise ValueError("redirected outcome requires affected_seats")
        if resolution not in {"secret_death", "redirected", "transformation"} and affected:
            raise ValueError(f"{resolution} cannot have affected seats")
        for seat in affected:
            self.state.seat(seat)

        inverse = self._restore_operations(outcome, self.state)
        sourced_effects: dict[int, list] = {}
        if resolution in {"secret_death", "redirected"}:
            for seat_number in affected:
                seat = self.state.seat(seat_number)
                sourced_effects[seat_number] = [
                    effect for effect in self.state.effect_records.values()
                    if effect.source_seat == seat_number
                    and effect.source_character == seat.character_id
                    and effect.state != "ended"
                ]
                inverse.extend([
                    {"op": "set", "path": ["seats", seat_number, "alive"],
                     "value": seat.alive},
                    {"op": "set", "path": ["seats", seat_number, "public_alive"],
                     "value": seat.public_alive},
                    {"op": "set", "path": ["seats", seat_number, "died_at"],
                     "value": seat.died_at},
                    {"op": "set", "path": ["seats", seat_number, "died_day"],
                     "value": seat.died_day},
                    {"op": "set", "path": ["seats", seat_number, "death_record"],
                     "value": deepcopy(seat.death_record)},
                    *({"op": "restore_effect", "effect": effect.to_dict()}
                      for effect in sourced_effects[seat_number]),
                    *({"op": "set",
                       "path": ["seats", effect.target_seat, "mad_about"],
                       "value": self.state.seat(effect.target_seat).mad_about}
                      for effect in sourced_effects[seat_number]
                      if effect.type == "mad"),
                ])
        transformations = details.get("transformations", []) if resolution == "transformation" else []
        if resolution == "transformation" and not transformations:
            raise ValueError("transformation outcome requires transformations")
        for item in transformations:
            seat_number = int(item["seat"])
            seat = self.state.seat(seat_number)
            if item.get("character_id") not in self.pack.character_by_id:
                raise ValueError("transformation character is not in this script")
            inverse.extend([
                {"op": "set", "path": ["seats", seat_number, "character_id"],
                 "value": seat.character_id},
                {"op": "set", "path": ["seats", seat_number, "alignment"],
                 "value": seat.alignment},
            ])
            if seat_number not in affected:
                affected.append(seat_number)

        event_id = uuid4().hex
        resolution_event = self.journal.append(
            "outcome_resolved",
            {"outcome_id": outcome.id, "resolution": resolution,
             "affected_seats": affected, "details": details},
            {"op": "batch", "operations": inverse},
            depends_on=[outcome.created_event] if outcome.created_event else [],
            event_id=event_id,
        )
        resolved_at = timestamp()
        is_demon_attack = bool(details.get(
            "is_demon_attack", outcome.metadata.get("is_demon_attack", False)
        ))
        arbitrary = bool(details.get("arbitrary", outcome.metadata.get("arbitrary", False)))
        if resolution in {"secret_death", "redirected"}:
            for seat_number in affected:
                seat = self.state.seat(seat_number)
                was_alive = seat.alive
                seat.alive = False
                seat.public_alive = True if was_alive else seat.public_alive
                seat.died_day = self.queue.night_no
                seat.died_at = resolution_event.id
                seat.death_record = {
                    "event_id": resolution_event.id,
                    "outcome_id": outcome.id,
                    "source_event": outcome.metadata.get(
                        "death_source_event", outcome.source_event),
                    "source_seat": outcome.metadata.get(
                        "death_source_seat", outcome.source_seat),
                    "source_character": outcome.metadata.get(
                        "death_source_character", outcome.source_character),
                    "ability": outcome.metadata.get("ability", outcome.source_character),
                    "phase": "night",
                    "night_no": self.queue.night_no,
                    "step_id": outcome.metadata.get("step_id"),
                    "is_demon_attack": is_demon_attack,
                    "arbitrary": arbitrary,
                    "selected_seats": list(outcome.selected_seats),
                    "redirected_from": (list(outcome.selected_seats)
                                        if resolution == "redirected" else []),
                    "prevented_or_replaced": details.get("prevented_or_replaced", []),
                    "resolved_at": resolved_at,
                }
                changed_effects = self.effects.advance(
                    "source_death",
                    source_seat=seat_number,
                    source_character=seat.character_id,
                    source_active=False,
                    permanent=True,
                    reason="source_died",
                )
                for effect in changed_effects:
                    effect.transitions[-1]["source_event"] = resolution_event.id
                    if effect.type == "mad" and effect.state == "ended":
                        target_state = self.state.seat(effect.target_seat)
                        if target_state.mad_about == effect.payload.get(
                            "claimed_character"
                        ):
                            target_state.mad_about = None
        for item in transformations:
            seat = self.state.seat(int(item["seat"]))
            seat.character_id = item["character_id"]
            if item.get("alignment") in {"good", "evil"}:
                seat.alignment = item["alignment"]

        outcome.resolution = resolution
        outcome.affected_seats = affected
        outcome.resolution_event = resolution_event.id
        outcome.status = "resolved"
        outcome.resolved_at = resolved_at
        outcome.metadata.update(details)
        self.queue.rebuild_suffix(resolution_event.id)
        return outcome

    def publish_dawn(self) -> dict[str, Any]:
        deaths = [seat for seat in self.state.seats.values()
                  if (not seat.alive and seat.public_alive
                      and seat.died_day == self.queue.night_no)]
        inverse = [
            {"op": "set", "path": ["seats", seat.seat, "public_alive"],
             "value": seat.public_alive}
            for seat in deaths
        ]
        dependencies = list(dict.fromkeys(
            seat.died_at for seat in deaths if seat.died_at
        ))
        known = {event.id for event in self.journal.records}
        event = self.journal.append(
            "dawn_publication",
            {"night_no": self.queue.night_no,
             "deaths": [{"seat": seat.seat} for seat in deaths]},
            {"op": "batch", "operations": inverse},
            depends_on=[event_id for event_id in dependencies if event_id in known],
        )
        for seat in deaths:
            seat.public_alive = False
        # Effects advance on semantic triggers. Dusk-bound effects intentionally remain
        # through the following day and are advanced when the next dusk begins.
        self.effects.advance("dawn")
        return {"event_id": event.id, "night_no": self.queue.night_no,
                "deaths": [{"seat": seat.seat} for seat in deaths]}

    def projection(self) -> dict[str, Any]:
        return {
            "pending": [outcome.to_dict() for outcome in self.state.pending_outcomes.values()
                        if outcome.status == "pending"],
            "history": [outcome.to_dict() for outcome in self.state.pending_outcomes.values()],
        }
