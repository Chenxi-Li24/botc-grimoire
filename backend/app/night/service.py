"""Night workflow coordinator; navigation is separate from action mutation."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any
from uuid import uuid4

from ..catalog import ScriptPack
from ..state import GameState
from .ability_state import AbilityStateStore
from .effects import EffectLedger
from .handlers import PitHagHandler, PitHagPreview, StatusRoleHandlers
from .information import InformationDelivery, InformationDraft, InformationEngine
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
        self.abilities = AbilityStateStore(state)
        for seat in state.seats.values():
            if seat.character_id:
                self.abilities.set(seat.seat, "current_night", night_no, "_system")
        self.information = InformationEngine(
            state, pack, journal, effects, self.abilities,
        )
        self.pit_hag = PitHagHandler(self)
        self.status_roles = StatusRoleHandlers(self)

    def record_fields(self, step_id: str, values: dict[str, Any]) -> NightStep:
        step = next((item for item in self.queue.steps if item.id == step_id), None)
        if step is None:
            raise NavigationConflict("stale_step", "夜晚步骤已变化", {"step_id": step_id})
        step.values.update(values)
        self._force_tokens.pop(step_id, None)
        return step

    def _missing(self, step: NightStep) -> list[str]:
        missing = []
        for field_name in step.required_fields:
            value = step.values.get(field_name)
            if value is None or value == "" or value == []:
                missing.append(field_name)
        for outcome in self.state.pending_outcomes.values():
            if (outcome.status == "pending"
                    and outcome.metadata.get("step_id") == step.id):
                missing.append(f"outcome:{outcome.id}")
        selection_events = {
            event.id for event in self.journal.records
            if event.payload.get("step_id") == step.id
        }
        for draft in self.state.information_drafts.values():
            if draft.status == "pending" and draft.source_event in selection_events:
                missing.append(f"information:{draft.id}")
        for preview in self.state.pending_transformations.values():
            if (preview.get("status") == "pending"
                    and preview.get("actor_seat") == step.actor_seat
                    and step.character_id == "pithag"):
                missing.append(f"pit_hag:{preview['id']}")
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
                if step.actor_seat is not None and not step.values.get("_wake_recorded"):
                    self.abilities.record_wake(
                        step.actor_seat, self.queue.night_no, step.id,
                        reason=step.trigger,
                    )
                    step.values["_wake_recorded"] = True
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

    def _validate_targets(self, step: NightStep,
                          selected_seats: list[int]) -> list[int]:
        selected = [int(seat) for seat in selected_seats]
        ability_id = step.source.get("ability_character", step.character_id)
        character = self.pack.character_by_id.get(ability_id)
        selection = character.selection if character else None
        if selection and selection.players != len(selected):
            raise NavigationConflict(
                "invalid_target_count",
                f"该行动需要选择 {selection.players} 名玩家",
                {"required": selection.players, "received": len(selected)},
            )
        if (not selection or selection.distinct_players) and len(set(selected)) != len(selected):
            raise NavigationConflict("duplicate_targets", "不能重复选择同一座位")
        for target in selected:
            try:
                holder = self.state.seat(target)
            except KeyError as exc:
                raise NavigationConflict(
                    "invalid_target", "目标座位无效", {"seat": target},
                ) from exc
            if holder.character_id is None:
                raise NavigationConflict(
                    "empty_target", "目标座位尚未配置角色", {"seat": target},
                )
            if selection and not selection.allow_self and target == step.actor_seat:
                raise NavigationConflict(
                    "self_target_forbidden", "该角色不能选择自己", {"seat": target},
                )
            if selection and selection.alive_only and not holder.alive:
                raise NavigationConflict(
                    "target_must_be_alive", "该行动只能选择存活玩家", {"seat": target},
                )
        return selected

    def select_outcome(self, step_id: str, selected_seats: list[int]) -> PendingOutcome:
        step = next((item for item in self.queue.steps if item.id == step_id), None)
        if step is None:
            raise NavigationConflict("stale_step", "夜晚步骤已变化", {"step_id": step_id})
        if step.actor_seat is None:
            raise NavigationConflict("invalid_actor", "该步骤没有行动座位")
        selected = self._validate_targets(step, selected_seats)
        self.record_fields(step_id, {"targets": selected})
        dependencies = [item for item in step.depends_on
                        if any(event.id == item for event in self.journal.records)]
        selection = self.journal.append(
            "action_selection",
            {"step_id": step.id, "source_seat": step.actor_seat,
             "source_character": step.character_id,
             "selected_seats": selected},
            {"op": "noop"},
            depends_on=dependencies,
        )
        character = self.pack.character_by_id.get(step.character_id)
        is_demon_attack = bool(character and character.team == "demon")
        arbitrary_source = self._arbitrary_death_source()
        arbitrary = arbitrary_source is not None
        return self.outcomes.create(
            source_event=selection.id,
            source_seat=step.actor_seat,
            source_character=step.character_id,
            selected_seats=selected,
            metadata={
                "step_id": step.id,
                "night_no": self.queue.night_no,
                "ability": step.perceived_as or step.character_id,
                "is_demon_attack": is_demon_attack and not arbitrary,
                "lunatic_choice": step.character_id == "lunatic",
                "arbitrary": arbitrary,
                **({
                    "death_source_seat": arbitrary_source["seat"],
                    "death_source_character": arbitrary_source["character"],
                    "death_source_event": arbitrary_source["event_id"],
                } if arbitrary_source else {}),
            },
        )

    def _arbitrary_death_source(self) -> dict[str, Any] | None:
        for seat in self.state.seats.values():
            pit_hag = seat.ability_state.get("pithag", {})
            if self.queue.night_no in pit_hag.get("arbitrary_death_nights", ()):
                source = pit_hag.get("arbitrary_death_source")
                if source:
                    return source
        return None

    def create_arbitrary_death(self, selected_seats: list[int]) -> PendingOutcome:
        source = self._arbitrary_death_source()
        if source is None:
            raise NavigationConflict(
                "arbitrary_death_unavailable",
                "本夜没有麻脸巫婆创造恶魔所产生的任意死亡",
            )
        selected = [int(seat) for seat in selected_seats]
        if not selected:
            raise NavigationConflict("missing_targets", "任意死亡至少需要一个目标")
        if len(set(selected)) != len(selected):
            raise NavigationConflict("duplicate_targets", "不能重复选择同一座位")
        for target in selected:
            try:
                holder = self.state.seat(target)
            except KeyError as exc:
                raise NavigationConflict(
                    "invalid_target", "目标座位无效", {"seat": target},
                ) from exc
            if holder.character_id is None:
                raise NavigationConflict(
                    "empty_target", "目标座位尚未配置角色", {"seat": target},
                )
        event = self.journal.append(
            "pit_hag_arbitrary_death_selection",
            {"source_seat": source["seat"],
             "source_character": source["character"],
             "selected_seats": selected,
             "night_no": self.queue.night_no},
            {"op": "noop"},
            depends_on=[source["event_id"]],
        )
        return self.outcomes.create(
            source_event=event.id,
            source_seat=source["seat"],
            source_character=source["character"],
            selected_seats=selected,
            metadata={
                "night_no": self.queue.night_no,
                "ability": "pithag_created_demon",
                "is_demon_attack": False,
                "arbitrary": True,
                "death_source_seat": source["seat"],
                "death_source_character": source["character"],
                "death_source_event": source["event_id"],
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

    def prepare_information(self, actor_seat: int, targets: list[int] | None = None, *,
                            registrations: list[dict] | None = None,
                            source_event: str | None = None) -> InformationDraft | InformationDelivery:
        return self.information.prepare(
            actor_seat,
            targets,
            registrations=registrations,
            source_event=source_event,
        )

    def deliver_information(self, draft_id: str, delivered_result: Any, **kwargs) -> InformationDelivery:
        return self.information.deliver(draft_id, delivered_result, **kwargs)

    def correct_information(self, delivery_id: str, claims: list[dict], reason: str) -> dict:
        return self.information.correct(delivery_id, claims, reason)

    def preview_pit_hag(self, actor: int, target: int,
                        character: str) -> PitHagPreview:
        return self.pit_hag.preview(actor, target, character)

    def confirm_pit_hag_preview(self, preview_id: str):
        return self.pit_hag.confirm(preview_id)

    def confirm_pit_hag(self, actor: int, target: int, character: str):
        preview = self.preview_pit_hag(actor, target, character)
        return self.confirm_pit_hag_preview(preview.id)

    def apply_poisoner(self, source: int, target: int):
        return self.status_roles.apply_poisoner(source, target)

    def apply_widow(self, source: int, target: int):
        return self.status_roles.apply_widow(source, target)

    def apply_cerenovus(self, source: int, target: int,
                        claimed_character: str):
        return self.status_roles.apply_cerenovus(source, target, claimed_character)

    def set_source_ability(self, source: int, *, active: bool,
                           permanent: bool = False):
        return self.status_roles.set_source_ability(
            source, active=active, permanent=permanent,
        )

    def deliver_test_information(self, actor: int,
                                 depends_on: list[str] | None = None) -> InformationDelivery:
        prepared = self.prepare_information(
            actor,
            source_event=(depends_on or [None])[-1],
        )
        if isinstance(prepared, InformationDelivery):
            return prepared
        result = prepared.true_result
        claims = [{"label": "test_result", "value": result, "truthful": True}]
        return self.deliver_information(prepared.id, result, claims=claims)

    def inject_inverse_failure(self, event_id: str) -> None:
        self.journal.inject_inverse_failure(event_id)

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
        projection["current_task"] = (
            self.queue.current.to_dict(current=True) if self.queue.current else None
        )
        projection["outcomes"] = self.outcomes.projection()
        projection["information"] = self.information.projection()
        projection["transformations"] = {
            "pending": [item for item in self.state.pending_transformations.values()
                        if item.get("status") == "pending"],
            "history": list(self.state.pending_transformations.values()),
        }
        all_effects = list(self.state.effect_records.values())
        projection["effects"] = {
            "current": [effect.to_dict() for effect in all_effects
                        if effect.state != "ended"],
            "history": [effect.to_dict() for effect in all_effects],
        }
        projection["seat_context"] = [
            {
                "seat": seat.seat,
                "claimed_by": seat.claimed_by,
                "character_id": seat.character_id,
                "perceived_character_id": seat.perceived_character_id,
                "alignment": seat.alignment,
                "alive": seat.alive,
                "public_alive": seat.public_alive,
                "secret_dead": not seat.alive and seat.public_alive,
                "effect_ids": list(seat.effect_ids),
            }
            for seat in sorted(self.state.seats.values(), key=lambda item: item.seat)
            if seat.character_id is not None
        ]
        undo_previews = []
        for event in reversed(self.journal.records[-20:]):
            if event.state != "active":
                continue
            preview = self.journal.undo(event.id, confirm=False)
            undo_previews.append({
                "event_id": event.id,
                "kind": event.kind,
                "created_at": event.created_at,
                "event_ids": preview.event_ids,
                "events": preview.events,
                "retractions": preview.retractions,
            })
        projection["undo_previews"] = undo_previews
        projection["context"] = {"lunatic_choices": self._lunatic_context()}
        return projection
