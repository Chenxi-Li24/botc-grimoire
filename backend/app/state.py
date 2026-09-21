"""Canonical game entities shared by the current game and the new night engine."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .night.models import EffectRecord, EventRecord, PendingOutcome


@dataclass
class SeatState:
    seat: int
    claimed_by: str | None = None
    character_id: str | None = None
    perceived_character_id: str | None = None
    alignment: str = "good"
    alive: bool = True
    public_alive: bool = True
    died_at: str | None = None
    died_day: int | None = None
    dead_vote_used: bool = False
    effect_ids: list[str] = field(default_factory=list)
    ability_state: dict[str, dict] = field(default_factory=dict)
    legacy_markers: list[str] = field(default_factory=list)
    mad_about: str | None = None
    role_change_notice: str | None = None
    team_change_notice: str | None = None
    death_record: dict | None = None


@dataclass
class PlayerAccount:
    id: str
    name: str
    seat: int | None = None
    wish: str | None = None
    account_id: str | None = None


@dataclass
class GameState:
    player_count: int
    players: dict[str, PlayerAccount] = field(default_factory=dict)
    seats: dict[int, SeatState] = field(default_factory=dict)
    event_records: list[EventRecord] = field(default_factory=list)
    effect_records: dict[str, EffectRecord] = field(default_factory=dict)
    pending_outcomes: dict[str, PendingOutcome] = field(default_factory=dict)
    information_drafts: dict[str, Any] = field(default_factory=dict)
    information_deliveries: dict[str, Any] = field(default_factory=dict)
    information_notices: list[dict[str, Any]] = field(default_factory=list)
    pending_transformations: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def empty(cls, player_count: int) -> "GameState":
        return cls(
            player_count=player_count,
            seats={seat: SeatState(seat=seat) for seat in range(1, player_count + 1)},
        )

    def seat(self, seat: int) -> SeatState:
        seat = int(seat)
        if not 1 <= seat <= self.player_count:
            raise KeyError(seat)
        if seat not in self.seats:
            self.seats[seat] = SeatState(seat=seat)
        return self.seats[seat]

    def replace_from(self, source: "GameState") -> None:
        """Atomically adopt a validated clone while preserving shared containers."""
        self.player_count = source.player_count
        self.players.clear()
        self.players.update(source.players)
        for seat in list(self.seats):
            if seat not in source.seats:
                del self.seats[seat]
        for seat, incoming in source.seats.items():
            current = self.seats.get(seat)
            if current is None:
                self.seats[seat] = incoming
                continue
            for field_name, value in vars(incoming).items():
                setattr(current, field_name, value)
        self.event_records.clear()
        self.event_records.extend(source.event_records)
        self.effect_records.clear()
        self.effect_records.update(source.effect_records)
        self.pending_outcomes.clear()
        self.pending_outcomes.update(source.pending_outcomes)
        self.information_drafts.clear()
        self.information_drafts.update(source.information_drafts)
        self.information_deliveries.clear()
        self.information_deliveries.update(source.information_deliveries)
        self.information_notices.clear()
        self.information_notices.extend(source.information_notices)
        self.pending_transformations.clear()
        self.pending_transformations.update(source.pending_transformations)
