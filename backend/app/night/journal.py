"""Immutable event journal with dependency-aware atomic undo."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable
from uuid import uuid4

from ..state import GameState
from .models import EventRecord, timestamp


class UndoConflict(RuntimeError):
    """Raised when an undo closure cannot be reversed in full."""


@dataclass(frozen=True)
class UndoPreview:
    event_ids: list[str]
    events: list[dict[str, Any]]
    retractions: list[str]


InverseHandler = Callable[[GameState, EventRecord, dict[str, Any]], None]


class EventJournal:
    def __init__(self, state: GameState,
                 inverse_handlers: dict[str, InverseHandler] | None = None) -> None:
        self.state = state
        self.inverse_handlers = inverse_handlers or {}
        self._injected_inverse_failures: set[str] = set()

    def inject_inverse_failure(self, event_id: str) -> None:
        """Arm a transient failure without mutating the persisted event ledger."""
        self.get(event_id)
        self._injected_inverse_failures.add(event_id)

    @property
    def records(self) -> list[EventRecord]:
        return self.state.event_records

    def get(self, event_id: str) -> EventRecord:
        event = next((item for item in self.records if item.id == event_id), None)
        if event is None:
            raise KeyError(event_id)
        return event

    def append(self, kind: str, payload: dict[str, Any] | None = None,
               inverse: dict[str, Any] | None = None,
               depends_on: list[str] | None = None,
               transaction_id: str | None = None,
               event_id: str | None = None) -> EventRecord:
        dependencies = list(dict.fromkeys(depends_on or ()))
        known = {event.id for event in self.records}
        missing = [event_id for event_id in dependencies if event_id not in known]
        if missing:
            raise ValueError(f"unknown event dependencies: {', '.join(missing)}")
        record = EventRecord(
            id=event_id or uuid4().hex,
            kind=kind,
            payload=deepcopy(payload or {}),
            inverse=deepcopy(inverse or {"op": "noop"}),
            depends_on=dependencies,
            transaction_id=transaction_id or uuid4().hex,
        )
        if any(item.id == record.id for item in self.records):
            raise ValueError(f"duplicate event id: {record.id}")
        self.records.append(record)
        return record

    def _undo_closure(self, event_id: str) -> set[str]:
        root = self.get(event_id)
        if root.state != "active":
            raise UndoConflict("event is not active")
        active = {event.id: event for event in self.records if event.state == "active"}
        closure = {event.id for event in active.values()
                   if event.transaction_id == root.transaction_id}
        closure.add(root.id)
        changed = True
        while changed:
            changed = False
            transactions = {active[item].transaction_id for item in closure if item in active}
            for event in active.values():
                if (event.id not in closure
                        and (event.transaction_id in transactions
                             or any(parent in closure for parent in event.depends_on))):
                    closure.add(event.id)
                    changed = True
        return closure

    def _reverse_topological(self, closure: set[str]) -> list[EventRecord]:
        by_id = {event.id: event for event in self.records if event.id in closure}
        visited: set[str] = set()
        visiting: set[str] = set()
        ordered: list[EventRecord] = []

        def visit(event: EventRecord) -> None:
            if event.id in visited:
                return
            if event.id in visiting:
                raise UndoConflict("event dependency cycle")
            visiting.add(event.id)
            for parent in event.depends_on:
                if parent in by_id:
                    visit(by_id[parent])
            visiting.remove(event.id)
            visited.add(event.id)
            ordered.append(event)

        for event in self.records:
            if event.id in by_id:
                visit(event)
        return list(reversed(ordered))

    @staticmethod
    def _path_parent(state: GameState, path: list[Any]) -> tuple[Any, Any]:
        if not path:
            raise UndoConflict("inverse path cannot be empty")
        node: Any = state
        for key in path[:-1]:
            if isinstance(node, dict):
                lookup = int(key) if isinstance(key, str) and key.isdigit() and int(key) in node else key
                node = node[lookup]
            else:
                node = getattr(node, key)
        return node, path[-1]

    @classmethod
    def _set_path(cls, state: GameState, path: list[Any], value: Any) -> None:
        parent, key = cls._path_parent(state, path)
        if isinstance(parent, dict):
            lookup = int(key) if isinstance(key, str) and key.isdigit() else key
            parent[lookup] = deepcopy(value)
        else:
            setattr(parent, key, deepcopy(value))

    @classmethod
    def _delete_path(cls, state: GameState, path: list[Any]) -> None:
        parent, key = cls._path_parent(state, path)
        if isinstance(parent, dict):
            lookup = int(key) if isinstance(key, str) and key.isdigit() else key
            del parent[lookup]
        else:
            setattr(parent, key, None)

    def _apply_inverse(self, state: GameState, event: EventRecord,
                       inverse: dict[str, Any]) -> None:
        op = inverse.get("op")
        if op == "fail":
            raise UndoConflict(inverse.get("message", "injected inverse failure"))
        if op == "noop":
            return
        if op == "batch":
            for item in inverse.get("operations", ()):
                self._apply_inverse(state, event, item)
            return
        if op == "set":
            self._set_path(state, inverse["path"], inverse.get("value"))
            return
        if op == "delete":
            self._delete_path(state, inverse["path"])
            return
        if op == "end_effect":
            effect = state.effect_records[inverse["effect_id"]]
            prior = effect.state
            effect.state = "ended"
            effect.transitions.append({"at": timestamp(), "from": prior, "to": "ended",
                                       "reason": "source_event_undone"})
            seat = state.seat(effect.target_seat)
            if effect.id in seat.effect_ids:
                seat.effect_ids.remove(effect.id)
            return
        if op == "restore_effect":
            restored = inverse["effect"]
            from .models import EffectRecord
            effect = EffectRecord.from_dict(deepcopy(restored))
            state.effect_records[effect.id] = effect
            seat = state.seat(effect.target_seat)
            if effect.state != "ended" and effect.id not in seat.effect_ids:
                seat.effect_ids.append(effect.id)
            return
        if op in self.inverse_handlers:
            self.inverse_handlers[op](state, event, inverse)
            return
        raise UndoConflict(f"unsupported inverse operation: {op}")

    @staticmethod
    def _is_message(event: EventRecord) -> bool:
        return event.kind.startswith("message_") or "message_id" in event.payload

    def undo(self, event_id: str, confirm: bool = False) -> UndoPreview:
        closure = self._undo_closure(event_id)
        ordered = self._reverse_topological(closure)
        preview = UndoPreview(
            event_ids=[event.id for event in ordered],
            events=[{"id": event.id, "kind": event.kind,
                     "transaction_id": event.transaction_id} for event in ordered],
            retractions=[event.id for event in ordered if self._is_message(event)],
        )
        if not confirm:
            return preview

        candidate = deepcopy(self.state)
        candidate_by_id = {event.id: event for event in candidate.event_records}
        retractions: list[EventRecord] = []
        try:
            for original in ordered:
                if original.id in self._injected_inverse_failures:
                    raise UndoConflict("injected inverse failure")
                event = candidate_by_id[original.id]
                if self._is_message(event):
                    if event.inverse.get("op") == "fail":
                        raise UndoConflict(event.inverse.get(
                            "message", "injected inverse failure"))
                    retractions.append(EventRecord(
                        id=uuid4().hex,
                        kind="message_retraction",
                        payload={"retracts_event": event.id,
                                 "message_id": event.payload.get("message_id")},
                        inverse={"op": "noop"},
                        depends_on=[],
                        transaction_id=f"undo:{event_id}",
                    ))
                else:
                    self._apply_inverse(candidate, event, event.inverse)
                event.state = "undone"
                event.undone_at = timestamp()
            candidate.event_records.extend(retractions)
        except Exception as exc:
            if isinstance(exc, UndoConflict):
                raise
            raise UndoConflict(str(exc)) from exc
        self.state.replace_from(candidate)
        return preview
