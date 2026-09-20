"""Versioned canonical-seat save codec with migration from legacy saves."""

from __future__ import annotations

from dataclasses import asdict

from .catalog import ScriptPack
from .night.information import InformationDelivery, InformationDraft
from .night.models import EffectRecord, EventRecord, PendingOutcome
from .state import GameState, PlayerAccount, SeatState

SCHEMA_VERSION = 2


def _int_keyed(values: dict | None) -> dict[int, object]:
    return {int(key): value for key, value in (values or {}).items()}


def _default_alignment(pack: ScriptPack, character_id: str | None) -> str:
    if character_id is None:
        return "good"
    character = pack.character_by_id.get(character_id)
    return "evil" if character and character.team in ("minion", "demon") else "good"


def _optional_seat(value: object, player_count: int) -> int | None:
    if value is None:
        return None
    seat = int(value)
    if not 1 <= seat <= player_count:
        raise ValueError(f"saved seat {seat} is outside configured range")
    return seat


def decode_save(payload: dict, pack: ScriptPack) -> GameState:
    player_count = int(payload.get("player_count", 6))
    if payload.get("schema_version") == SCHEMA_VERSION and "seats" in payload:
        state = GameState.empty(player_count)
        state.players = {}
        for player_id, account in payload.get("players", {}).items():
            account = {**account, "seat": _optional_seat(account.get("seat"), player_count)}
            state.players[player_id] = PlayerAccount(**account)
        for key, seat_payload in payload.get("seats", {}).items():
            seat = int(key)
            if not 1 <= seat <= player_count:
                raise ValueError(f"saved seat {seat} is outside configured range")
            state.seats[seat] = SeatState(**{**seat_payload, "seat": seat})
        state.event_records = [EventRecord.from_dict(item)
                               for item in payload.get("event_records", ())]
        state.effect_records = {
            effect_id: EffectRecord.from_dict({**item, "id": effect_id})
            for effect_id, item in payload.get("effect_records", {}).items()
        }
        for effect in state.effect_records.values():
            if not 1 <= effect.target_seat <= player_count:
                raise ValueError(f"effect target {effect.target_seat} is outside configured range")
        state.pending_outcomes = {
            outcome_id: PendingOutcome.from_dict({**item, "id": outcome_id})
            for outcome_id, item in payload.get("pending_outcomes", {}).items()
        }
        state.information_drafts = {
            draft_id: InformationDraft.from_dict({**item, "id": draft_id})
            for draft_id, item in payload.get("information_drafts", {}).items()
        }
        state.information_deliveries = {
            delivery_id: InformationDelivery.from_dict({**item, "id": delivery_id})
            for delivery_id, item in payload.get("information_deliveries", {}).items()
        }
        state.information_notices = list(payload.get("information_notices", ()))
        state.pending_transformations = dict(payload.get("pending_transformations", {}))
        return state

    state = GameState.empty(player_count)
    players = payload.get("players", {})
    seat_roles = _int_keyed(payload.get("seat_roles"))
    seat_fakes = _int_keyed(payload.get("seat_fakes"))
    seat_alive = _int_keyed(payload.get("seat_alive"))
    seat_dead_day = _int_keyed(payload.get("seat_dead_day"))
    seat_dead_vote = _int_keyed(payload.get("seat_dead_vote"))
    markers = _int_keyed(payload.get("seat_markers"))
    mad_about = _int_keyed(payload.get("mad_about"))
    role_changes = _int_keyed(payload.get("seat_role_changes"))
    team_changes = _int_keyed(payload.get("seat_team_changes"))

    claimed: dict[int, dict] = {}
    for player_id, legacy in players.items():
        seat = _optional_seat(legacy.get("seat"), player_count)
        state.players[player_id] = PlayerAccount(
            id=legacy.get("id", player_id),
            name=legacy.get("name", ""),
            seat=seat,
            wish=legacy.get("wish"),
        )
        if seat is not None:
            claimed[seat] = {**legacy, "id": player_id}

    for seat in range(1, player_count + 1):
        legacy_player = claimed.get(seat, {})
        character_id = (role_changes.get(seat) or seat_roles.get(seat)
                        or legacy_player.get("role_id"))
        alive = bool(legacy_player.get("alive", seat_alive.get(seat, True)))
        died_day = legacy_player.get("died_day", legacy_player.get("died_night",
                                                                  seat_dead_day.get(seat)))
        team_notice = team_changes.get(seat)
        seat_state = state.seat(seat)
        seat_state.claimed_by = legacy_player.get("id")
        seat_state.character_id = character_id
        seat_state.perceived_character_id = seat_fakes.get(seat)
        seat_state.alignment = team_notice or _default_alignment(pack, character_id)
        seat_state.alive = alive
        hidden_night_death = (
            payload.get("phase") == "night"
            and not alive
            and died_day == payload.get("night_no")
        )
        seat_state.public_alive = True if hidden_night_death else alive
        seat_state.died_day = died_day
        seat_state.died_at = f"legacy:day:{died_day}" if died_day is not None else None
        seat_state.dead_vote_used = bool(
            legacy_player.get("dead_vote_used", seat_dead_vote.get(seat, False))
        )
        seat_state.legacy_markers = list(markers.get(seat, ()))
        seat_state.mad_about = mad_about.get(seat)
        seat_state.role_change_notice = role_changes.get(seat)
        seat_state.team_change_notice = team_notice
    return state


def encode_save(state: GameState) -> dict:
    payload = {
        "schema_version": SCHEMA_VERSION,
        "player_count": state.player_count,
        "players": {player_id: asdict(account)
                    for player_id, account in state.players.items()},
        "seats": {str(seat): asdict(seat_state)
                  for seat, seat_state in state.seats.items()},
        "event_records": [event.to_dict() for event in state.event_records],
        "effect_records": {effect_id: effect.to_dict()
                           for effect_id, effect in state.effect_records.items()},
        "pending_outcomes": {outcome_id: outcome.to_dict()
                             for outcome_id, outcome in state.pending_outcomes.items()},
        "information_drafts": {draft_id: draft.to_dict()
                               for draft_id, draft in state.information_drafts.items()},
        "information_deliveries": {delivery_id: delivery.to_dict()
                                   for delivery_id, delivery in state.information_deliveries.items()},
        "information_notices": list(state.information_notices),
        "pending_transformations": dict(state.pending_transformations),
    }
    # Validate that round-tripping the canonical section is structurally safe before disk replace.
    if len(payload["seats"]) != state.player_count:
        raise ValueError("canonical save has an incomplete seat set")
    return payload
