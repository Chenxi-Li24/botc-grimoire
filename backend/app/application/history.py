"""Minimal, account-private game history projection."""

from __future__ import annotations

from typing import Any

from app.game import GameManager
from app.infrastructure.identity_store import IdentityStore


def project_own_history(game: GameManager, player_id: str) -> dict[str, Any]:
    player = game.players[player_id]
    role_ids: list[str] = []
    seat = player.seat
    if seat is not None:
        for event in game.events:
            data = event.get("data", {})
            if event.get("type") == "role_change" and event.get("seat") == seat:
                for role_id in (data.get("from"), data.get("to")):
                    if role_id and role_id not in role_ids:
                        role_ids.append(role_id)
            if event.get("type") == "transform" and data.get("target") == seat:
                for role_id in (data.get("from"), data.get("char")):
                    if role_id and role_id not in role_ids:
                        role_ids.append(role_id)
    if player.role_id and player.role_id not in role_ids:
        role_ids.append(player.role_id)
    roles = [{"id": role_id, "name": game.roles.get(role_id, {}).get("name", role_id)}
             for role_id in role_ids]
    return {
        "game_id": game.game_id,
        "script_id": game.script_id,
        "seat": seat,
        "roles": roles,
        # The private inference event log is a separate planned subsystem; never infer
        # guesses from chat or from storyteller-only adjudication data.
        "guesses": [],
        "winner": game.winner,
        "finished": game.winner is not None,
    }


def archive_game(game: GameManager, store: IdentityStore) -> None:
    for player in game.players.values():
        if player.account_id is None:
            continue
        store.upsert_archive(game.game_id, player.account_id, project_own_history(game, player.id))
