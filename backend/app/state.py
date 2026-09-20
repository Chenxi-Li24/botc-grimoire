"""Canonical game entities shared by the current game and the new night engine."""

from __future__ import annotations

from dataclasses import dataclass, field


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


@dataclass
class PlayerAccount:
    id: str
    name: str
    seat: int | None = None
    wish: str | None = None


@dataclass
class GameState:
    player_count: int
    players: dict[str, PlayerAccount] = field(default_factory=dict)
    seats: dict[int, SeatState] = field(default_factory=dict)

    @classmethod
    def empty(cls, player_count: int) -> "GameState":
        return cls(
            player_count=player_count,
            seats={seat: SeatState(seat=seat) for seat in range(1, player_count + 1)},
        )

    def seat(self, seat: int) -> SeatState:
        if seat not in self.seats:
            self.seats[seat] = SeatState(seat=seat)
        return self.seats[seat]
