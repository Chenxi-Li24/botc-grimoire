"""Authenticated storyteller commands for the canonical night workflow."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any, Callable

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse

from ..game import GameManager
from ..night.journal import UndoConflict
from ..night.outcomes import OutcomeConflict
from ..night.service import NavigationConflict
from .schemas import (
    EffectBody,
    InformationBody,
    NavigateBody,
    PitHagBody,
    ResolveOutcomeBody,
    SelectNightTargetsBody,
    UndoBody,
)


class NightCommandError(RuntimeError):
    def __init__(self, code: str, message: str,
                 details: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.details = details or {}


async def night_error_response(_request: Request,
                               exc: NightCommandError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={"code": exc.code, "message": str(exc), "details": exc.details},
    )


def _raise_domain(exc: Exception) -> None:
    if isinstance(exc, NavigationConflict):
        raise NightCommandError(exc.code, str(exc), exc.details) from exc
    if isinstance(exc, UndoConflict):
        raise NightCommandError("undo_conflict", str(exc)) from exc
    if isinstance(exc, OutcomeConflict):
        raise NightCommandError("outcome_conflict", str(exc)) from exc
    if isinstance(exc, KeyError):
        missing = exc.args[0] if exc.args else None
        raise NightCommandError("stale_id", "请求引用的夜晚记录已不存在",
                                {"id": missing}) from exc
    if isinstance(exc, ValueError):
        raise NightCommandError("invalid_command", str(exc)) from exc
    raise exc


def _serialize(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, dict):
        return {key: _serialize(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_serialize(item) for item in value]
    return value


def _model_dump(value: Any) -> dict[str, Any]:
    return value.model_dump() if hasattr(value, "model_dump") else value.dict()


def create_night_router(game: GameManager, hub: Any,
                        require_storyteller: Callable) -> APIRouter:
    router = APIRouter(
        prefix="/api/night",
        dependencies=[Depends(require_storyteller)],
        tags=["night"],
    )

    async def success(result: Any, *, mutate: bool = True) -> dict[str, Any]:
        if mutate:
            game.save()
            await hub.push_all()
        return {
            "result": _serialize(result),
            "night_workflow": game.night.projection(),
        }

    @router.post("/step")
    async def navigate(body: NavigateBody) -> dict[str, Any]:
        try:
            if body.direction == "goto":
                if body.step_id is None:
                    raise NavigationConflict("missing_step", "goto 需要 step_id")
                result = game.navigate_night(step_id=body.step_id)
            else:
                result = game.navigate_night(
                    direction=body.direction,
                    force_token=body.force_token,
                )
            return await success(result)
        except Exception as exc:
            _raise_domain(exc)

    @router.post("/select")
    async def select_targets(body: SelectNightTargetsBody) -> dict[str, Any]:
        try:
            if body.arbitrary_death:
                result = game.night.create_arbitrary_death(body.selected_seats)
            else:
                if body.step_id is None:
                    raise NavigationConflict("missing_step", "选择目标需要 step_id")
                result = game.night.select_outcome(body.step_id, body.selected_seats)
            return await success(result)
        except Exception as exc:
            _raise_domain(exc)

    @router.post("/outcome")
    async def resolve_outcome(body: ResolveOutcomeBody) -> dict[str, Any]:
        try:
            details = dict(body.details)
            if body.rationale:
                details["rationale"] = body.rationale
            result = game.night.resolve_outcome(
                body.outcome_id,
                body.resolution,
                affected_seats=body.affected_seats,
                details=details,
            )
            return await success(result)
        except Exception as exc:
            _raise_domain(exc)

    @router.post("/information")
    async def information(body: InformationBody) -> dict[str, Any]:
        try:
            if body.action == "prepare":
                if body.actor_seat is None:
                    raise ValueError("prepare 需要 actor_seat")
                result = game.night.prepare_information(
                    body.actor_seat,
                    body.targets,
                    registrations=body.registrations,
                    source_event=body.source_event,
                )
            elif body.action == "deliver":
                if body.draft_id is None:
                    raise ValueError("deliver 需要 draft_id")
                claims = ([_model_dump(claim) for claim in body.claims]
                          if body.claims is not None else None)
                result = game.night.deliver_information(
                    body.draft_id,
                    body.delivered_result,
                    claims=claims,
                    reason=body.reason or None,
                )
            else:
                if body.delivery_id is None or body.claims is None:
                    raise ValueError("correct 需要 delivery_id 和 claims")
                result = game.night.correct_information(
                    body.delivery_id,
                    [_model_dump(claim) for claim in body.claims],
                    body.reason,
                )
            return await success(result)
        except Exception as exc:
            _raise_domain(exc)

    @router.post("/effect")
    async def effect(body: EffectBody) -> dict[str, Any]:
        try:
            if body.action == "source_ability":
                if body.active is None:
                    raise ValueError("source_ability 需要 active")
                result = game.night.set_source_ability(
                    body.source_seat, active=body.active, permanent=body.permanent,
                )
            else:
                if body.target_seat is None:
                    raise ValueError(f"{body.action} 需要 target_seat")
                if body.action == "poisoner":
                    result = game.night.apply_poisoner(
                        body.source_seat, body.target_seat,
                    )
                elif body.action == "widow":
                    result = game.night.apply_widow(
                        body.source_seat, body.target_seat,
                    )
                else:
                    if body.claimed_character is None:
                        raise ValueError("cerenovus 需要 claimed_character")
                    result = game.night.apply_cerenovus(
                        body.source_seat, body.target_seat,
                        body.claimed_character,
                    )
            return await success(result)
        except Exception as exc:
            _raise_domain(exc)

    @router.post("/pit-hag")
    async def pit_hag(body: PitHagBody) -> dict[str, Any]:
        try:
            if body.action == "preview":
                if (body.actor_seat is None or body.target_seat is None
                        or body.character_id is None):
                    raise ValueError(
                        "preview 需要 actor_seat、target_seat 和 character_id"
                    )
                result = game.night.preview_pit_hag(
                    body.actor_seat, body.target_seat, body.character_id,
                )
            elif body.preview_id is not None:
                result = game.night.confirm_pit_hag_preview(body.preview_id)
            else:
                if (body.actor_seat is None or body.target_seat is None
                        or body.character_id is None):
                    raise ValueError(
                        "confirm 需要 preview_id 或完整的角色变更参数"
                    )
                result = game.night.confirm_pit_hag(
                    body.actor_seat, body.target_seat, body.character_id,
                )
            return await success(result)
        except Exception as exc:
            _raise_domain(exc)

    @router.post("/undo")
    async def undo(body: UndoBody) -> dict[str, Any]:
        try:
            result = game.night.undo(body.event_id, confirm=body.confirm)
            return await success(result, mutate=body.confirm)
        except Exception as exc:
            _raise_domain(exc)

    return router
