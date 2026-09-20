"""Typed accessors for character state that survives nights and phase changes."""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from ..state import GameState


class AbilityStateStore:
    def __init__(self, state: GameState) -> None:
        self.state = state

    def character(self, seat: int, character_id: str | None = None) -> dict[str, Any]:
        holder = self.state.seat(seat)
        key = character_id or holder.character_id
        if key is None:
            raise ValueError("seat has no character")
        return holder.ability_state.setdefault(key, {})

    def get(self, seat: int, character_id: str | None = None,
            key: str | None = None, default=None):
        data = self.character(seat, character_id)
        return data if key is None else data.get(key, default)

    def set(self, seat: int, key: str, value: Any,
            character_id: str | None = None) -> Any:
        self.character(seat, character_id)[key] = deepcopy(value)
        return value

    def set_fortune_teller_red_herring(self, seat: int, target: int | None) -> None:
        self.set(seat, "red_herring", target, "fortuneteller")

    def fortune_teller_red_herring(self, seat: int) -> int | None:
        return self.get(seat, "fortuneteller", "red_herring")

    def set_grandchild(self, seat: int, target: int, character_id: str) -> None:
        self.set(seat, "grandchild", {"seat": target, "character_id": character_id},
                 "grandmother")

    def grandchild(self, seat: int) -> dict | None:
        return self.get(seat, "grandmother", "grandchild")

    def add_balloonist_seen(self, seat: int, target: int, team: str,
                            night_no: int) -> None:
        data = self.character(seat, "balloonist")
        data.setdefault("history", []).append(
            {"seat": target, "team": team, "night_no": night_no}
        )

    def balloonist_history(self, seat: int) -> list[dict]:
        return list(self.get(seat, "balloonist", "history", []))

    def set_acquired_ability(self, seat: int, owner: str,
                             character_id: str | None,
                             drunk_target: int | None = None) -> None:
        if owner not in {"philosopher", "cannibal"}:
            raise ValueError("owner must be philosopher or cannibal")
        self.set(seat, "acquired", {"character_id": character_id,
                                    "drunk_target": drunk_target}, owner)

    def acquired_ability(self, seat: int, owner: str) -> dict | None:
        return self.get(seat, owner, "acquired")

    def set_juggler_guesses(self, seat: int, guesses: list[dict]) -> None:
        self.set(seat, "guesses", guesses, "juggler")

    def juggler_guesses(self, seat: int) -> list[dict]:
        return list(self.get(seat, "juggler", "guesses", []))

    def set_once_used(self, seat: int, character_id: str, used: bool = True) -> None:
        self.set(seat, "once_used", bool(used), character_id)

    def once_used(self, seat: int, character_id: str) -> bool:
        return bool(self.get(seat, character_id, "once_used", False))

    def set_fang_gu_jump_used(self, seat: int, used: bool = True) -> None:
        self.set(seat, "jump_used", bool(used), "fang-gu")

    def fang_gu_jump_used(self, seat: int) -> bool:
        return bool(self.get(seat, "fang-gu", "jump_used", False))

    def set_po_charge(self, seat: int, charge: int) -> None:
        self.set(seat, "charge", max(0, int(charge)), "po")

    def po_charge(self, seat: int) -> int:
        return int(self.get(seat, "po", "charge", 0))

    def set_targets(self, seat: int, character_id: str, targets: list[int]) -> None:
        if character_id not in {"shabaloth", "pukka"}:
            raise ValueError("target chain is only typed for Shabaloth or Pukka")
        self.set(seat, "targets", list(targets), character_id)

    def targets(self, seat: int, character_id: str) -> list[int]:
        return list(self.get(seat, character_id, "targets", []))

    def record_wake(self, seat: int, night_no: int, step_id: str,
                    reason: str = "ability") -> None:
        data = self.character(seat, "_system")
        data.setdefault("wake_events", []).append(
            {"night_no": night_no, "step_id": step_id, "reason": reason}
        )

    def wake_events(self, seat: int, night_no: int | None = None) -> list[dict]:
        events = list(self.get(seat, "_system", "wake_events", []))
        return events if night_no is None else [e for e in events if e["night_no"] == night_no]
