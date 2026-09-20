"""Durable records shared by the night journal and effect ledger."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any


def timestamp() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class EventRecord:
    id: str
    kind: str
    payload: dict[str, Any]
    inverse: dict[str, Any]
    depends_on: list[str]
    transaction_id: str
    state: str = "active"
    created_at: str = field(default_factory=timestamp)
    undone_at: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "EventRecord":
        return cls(**value)


@dataclass
class EffectRecord:
    id: str
    type: str
    target_seat: int
    source_seat: int | None
    source_character: str | None
    source_event: str
    payload: dict[str, Any]
    lifetime_policy: dict[str, Any]
    state: str
    transitions: list[dict[str, Any]]
    started_at: str = field(default_factory=timestamp)
    expected_end: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "EffectRecord":
        return cls(**value)


@dataclass
class PendingOutcome:
    id: str
    source_event: str
    source_seat: int | None
    source_character: str
    selected_seats: list[int]
    hints: list[dict[str, Any]]
    resolution: str | None = None
    affected_seats: list[int] = field(default_factory=list)
    created_event: str | None = None
    resolution_event: str | None = None
    status: str = "pending"
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=timestamp)
    resolved_at: str | None = None

    @property
    def event_id(self) -> str | None:
        return self.resolution_event or self.created_event

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "PendingOutcome":
        return cls(**value)
