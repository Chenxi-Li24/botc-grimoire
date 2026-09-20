"""Night workflow coordinator; navigation is separate from action mutation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from uuid import uuid4

from ..catalog import ScriptPack
from ..state import GameState
from .effects import EffectLedger
from .journal import EventJournal
from .models import PendingOutcome
from .outcomes import OutcomeAdjudicator
from .queue import NightQueue, NightStep


class NavigationConflict(RuntimeError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


@dataclass
class NavigationResult:
    current_step_id: str | None
    blocked: bool = False
    omissions: list[str] | None = None
    force_token: str | None = None
    forced_event_id: str | None = None
    at_end: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class NightService:
    def __init__(self, state: GameState, pack: ScriptPack, night_no: int,
                 journal: EventJournal, effects: EffectLedger,
                 traveler_actions: list[dict[str, Any]] | None = None,
                 restored_queue: dict[str, Any] | None = None) -> None:
        self.state = state
        self.pack = pack
        self.journal = journal
        self.effects = effects
        self.queue = NightQueue(state, pack, night_no, traveler_actions)
        self._force_tokens: dict[str, dict[str, Any]] = {}
        if restored_queue:
            self.queue.restore(restored_queue)
        else:
            self.queue.build()
        self.outcomes = OutcomeAdjudicator(
            state, pack, journal, effects, self.queue,
        )

    def record_fields(self, step_id: str, values: dict[str, Any]) -> NightStep:
        step = next((item for item in self.queue.steps if item.id == step_id), None)
        if step is None:
            raise NavigationConflict("stale_step", "夜晚步骤已变化", {"step_id": step_id})
        step.values.update(values)
        self._force_tokens.pop(step_id, None)
        return step

    @staticmethod
    def _missing(step: NightStep) -> list[str]:
        missing = []
        for field_name in step.required_fields:
            value = step.values.get(field_name)
            if value is None or value == "" or value == []:
                missing.append(field_name)
        return missing

    def _index(self, step_id: str | None) -> int:
        if step_id is None:
            raise NavigationConflict("empty_queue", "本夜没有可执行步骤")
        try:
            return next(index for index, item in enumerate(self.queue.steps)
                        if item.id == step_id)
        except StopIteration as exc:
            raise NavigationConflict("stale_step", "夜晚步骤已变化",
                                     {"step_id": step_id}) from exc

    def navigate(self, step_id: str | None = None, direction: str | None = None,
                 force: bool = False, force_token: str | None = None) -> NavigationResult:
        if step_id is not None:
            self._index(step_id)
            self.queue.current_step_id = step_id
            return NavigationResult(current_step_id=step_id)
        if direction not in {"previous", "next"}:
            raise NavigationConflict("invalid_direction", "方向必须是 previous 或 next")
        index = self._index(self.queue.current_step_id)
        if direction == "previous":
            if index == 0:
                raise NavigationConflict("at_start", "已经是本夜第一步")
            self.queue.current_step_id = self.queue.steps[index - 1].id
            return NavigationResult(current_step_id=self.queue.current_step_id)

        step = self.queue.steps[index]
        if step.status == "upcoming":
            missing = self._missing(step)
            if missing:
                armed = self._force_tokens.get(step.id)
                if not force:
                    token = uuid4().hex
                    self._force_tokens[step.id] = {"token": token, "missing": missing}
                    return NavigationResult(
                        current_step_id=step.id,
                        blocked=True,
                        omissions=missing,
                        force_token=token,
                    )
                if (armed is None or force_token != armed["token"]
                        or armed["missing"] != missing):
                    raise NavigationConflict("expired_force_token", "强制继续确认已失效",
                                             {"step_id": step.id, "omissions": missing})
                known = {event.id for event in self.journal.records}
                event = self.journal.append(
                    "forced_skip",
                    {"step_id": step.id, "omissions": missing,
                     "actor_seat": step.actor_seat,
                     "character_id": step.character_id},
                    {"op": "noop"},
                    depends_on=[item for item in step.depends_on if item in known],
                )
                step.status = "skipped"
                step.skip_reason = "forced"
                self._force_tokens.pop(step.id, None)
                forced_event_id = event.id
            else:
                step.status = "completed"
                forced_event_id = None
        else:
            forced_event_id = None

        if index + 1 >= len(self.queue.steps):
            return NavigationResult(current_step_id=step.id,
                                    forced_event_id=forced_event_id, at_end=True)
        self.queue.current_step_id = self.queue.steps[index + 1].id
        return NavigationResult(current_step_id=self.queue.current_step_id,
                                forced_event_id=forced_event_id)

    def rebuild(self, cause_event_id: str | None = None) -> list[NightStep]:
        return self.queue.rebuild_suffix(cause_event_id)

    def select_outcome(self, step_id: str, selected_seats: list[int]) -> PendingOutcome:
        step = next((item for item in self.queue.steps if item.id == step_id), None)
        if step is None:
            raise NavigationConflict("stale_step", "夜晚步骤已变化", {"step_id": step_id})
        if step.actor_seat is None:
            raise NavigationConflict("invalid_actor", "该步骤没有行动座位")
        self.record_fields(step_id, {"targets": list(selected_seats)})
        dependencies = [item for item in step.depends_on
                        if any(event.id == item for event in self.journal.records)]
        selection = self.journal.append(
            "action_selection",
            {"step_id": step.id, "source_seat": step.actor_seat,
             "source_character": step.character_id,
             "selected_seats": list(selected_seats)},
            {"op": "noop"},
            depends_on=dependencies,
        )
        character = self.pack.character_by_id.get(step.character_id)
        is_demon_attack = bool(character and character.team == "demon")
        return self.outcomes.create(
            source_event=selection.id,
            source_seat=step.actor_seat,
            source_character=step.character_id,
            selected_seats=selected_seats,
            metadata={
                "step_id": step.id,
                "night_no": self.queue.night_no,
                "ability": step.perceived_as or step.character_id,
                "is_demon_attack": is_demon_attack,
                "lunatic_choice": step.character_id == "lunatic",
            },
        )

    def resolve_outcome(self, outcome_id: str, resolution: str, **kwargs) -> PendingOutcome:
        return self.outcomes.resolve(outcome_id, resolution, **kwargs)

    def resolve_test_attack(self, source: int, target: int,
                            resolution: str = "secret_death") -> PendingOutcome:
        character_id = self.state.seat(source).character_id
        if character_id is None:
            raise ValueError("source seat has no character")
        try:
            step = self.queue.step_for(source, character_id)
        except KeyError:
            step = NightStep(
                id=f"test:{self.queue.night_no}:{source}:{character_id}",
                actor_seat=source,
                character_id=character_id,
                perceived_as=self.state.seat(source).perceived_character_id,
                trigger="normal",
                order=0,
            )
            self.queue.steps.append(step)
        outcome = self.select_outcome(step.id, [target])
        chosen_resolution = "choice_only" if character_id == "lunatic" else resolution
        return self.resolve_outcome(outcome.id, chosen_resolution)

    def publish_dawn(self) -> dict[str, Any]:
        return self.outcomes.publish_dawn()

    def undo(self, event_id: str, confirm: bool = False):
        preview = self.journal.undo(event_id, confirm=confirm)
        if confirm:
            for undone_id in preview.event_ids:
                event = self.journal.get(undone_id)
                step_id = event.payload.get("step_id")
                step = next((item for item in self.queue.steps if item.id == step_id), None)
                if step is None:
                    continue
                if event.kind == "action_selection":
                    step.values.pop("targets", None)
                    step.status = "undone"
                    step.skip_reason = "event_undone"
                elif event.kind == "forced_skip" and step.skip_reason == "forced":
                    step.status = "undone"
                    step.skip_reason = "event_undone"
            self.queue.rebuild_suffix()
        return preview

    def _lunatic_context(self) -> list[dict[str, Any]]:
        return [
            {"lunatic_seat": outcome.source_seat,
             "target_seats": list(outcome.selected_seats),
             "outcome_id": outcome.id}
            for outcome in self.state.pending_outcomes.values()
            if (outcome.status == "resolved"
                and outcome.resolution == "choice_only"
                and outcome.source_character == "lunatic"
                and outcome.metadata.get("night_no") == self.queue.night_no)
        ]

    def dump(self) -> dict[str, Any]:
        return self.queue.dump()

    def projection(self) -> dict[str, Any]:
        projection = self.queue.projection()
        projection["outcomes"] = self.outcomes.projection()
        projection["context"] = {"lunatic_choices": self._lunatic_context()}
        return projection
