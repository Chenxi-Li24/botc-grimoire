"""Seat-owned player commands for the canonical night workflow."""

from __future__ import annotations

from typing import Any

from .service import NavigationConflict


def _body_value(body: Any, key: str, default: Any = None) -> Any:
    if isinstance(body, dict):
        return body.get(key, default)
    return getattr(body, key, default)


def _validate_character(night, step, character_id: str | None) -> str | None:
    required = "character" in step.required_fields
    if required and not character_id:
        raise NavigationConflict("missing_character", "该行动需要选择一个角色")
    if character_id is None:
        return None
    character = night.pack.character_by_id.get(character_id)
    if character is None:
        raise NavigationConflict(
            "invalid_character", "所选角色不在当前剧本中",
            {"character_id": character_id},
        )
    ability_id = step.source.get("ability_character", step.perceived_as or step.character_id)
    ability = night.pack.character_by_id.get(ability_id)
    allowed = ability.selection.character_teams if ability and ability.selection else ()
    if allowed and character.team not in allowed:
        raise NavigationConflict(
            "invalid_character_team", "所选角色不符合该行动要求",
            {"character_id": character_id, "allowed_teams": list(allowed)},
        )
    return character_id


def submit_player_night_action(game, player_id: str, body: Any):
    """Validate seat ownership and dispatch a phone choice to canonical services."""
    player = game.players.get(player_id)
    if player is None or player.seat is None:
        raise ValueError("你还没有入座")
    if game.phase != "night":
        raise ValueError("现在不是夜晚")

    step_id = _body_value(body, "step_id")
    step = game.night.step(step_id)
    if step.actor_seat != player.seat:
        raise ValueError("这不是你的夜晚步骤")
    selected_seats = list(_body_value(body, "selected_seats", []) or [])
    character_id = _body_value(body, "character_id")
    submission = {"selected_seats": selected_seats, "character_id": character_id}
    receipt = step.values.get("player_submission")
    if receipt is not None:
        if receipt != submission:
            raise ValueError("这一步已经提交，不能修改；请联系说书人纠错")
        return None
    if step.id != game.night.queue.current_step_id:
        raise ValueError("夜晚步骤已变化，请按当前提示重新选择")
    if step.status not in {"upcoming", "current"}:
        raise ValueError("这个夜晚步骤已经结束")

    character_id = _validate_character(game.night, step, character_id)
    ability_id = step.source.get("ability_character", step.perceived_as or step.character_id)
    ability = game.night.pack.character_by_id.get(ability_id)

    def accepted(result):
        step.values["player_submission"] = submission
        return result

    if step.character_id in {"poisoner", "widow", "cerenovus"}:
        selection = game.night.record_selection(
            step.id, selected_seats, character_id=character_id,
        )
        target = selection.payload["selected_seats"][0]
        if step.character_id == "poisoner":
            return accepted(game.night.apply_poisoner(player.seat, target))
        if step.character_id == "widow":
            return accepted(game.night.apply_widow(player.seat, target))
        return accepted(game.night.apply_cerenovus(player.seat, target, character_id))

    if step.character_id == "pithag":
        selection = game.night.record_selection(
            step.id, selected_seats, character_id=character_id,
        )
        return accepted(game.night.preview_pit_hag(
            player.seat, selection.payload["selected_seats"][0], character_id,
        ))

    if ability and ability.information_resolver:
        selection = game.night.record_selection(step.id, selected_seats)
        return accepted(game.night.prepare_information(
            player.seat,
            selection.payload["selected_seats"],
            source_event=selection.id,
        ))

    if ((ability and ability.team == "demon") or step.character_id == "lunatic") \
            and "targets" in step.required_fields:
        outcome = game.night.select_outcome(step.id, selected_seats)
        if step.character_id == "lunatic":
            return accepted(game.night.resolve_outcome(outcome.id, "choice_only"))
        return accepted(outcome)

    return accepted(game.night.record_selection(
        step.id,
        selected_seats,
        character_id=character_id,
        acknowledged="acknowledged" in step.required_fields,
    ))
