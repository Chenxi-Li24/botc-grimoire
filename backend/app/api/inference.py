"""Session-authenticated, owner-only player deductions."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from ..application import runtime
from .dependencies import require_matching_player


router = APIRouter()


class InferenceBody(BaseModel):
    target: int | str
    category: str
    operation: str
    data: dict[str, Any] = Field(default_factory=dict)
    client_id: str


@router.post("/api/player/{player_id}/inference", dependencies=[Depends(require_matching_player)])
async def record_inference(player_id: str, body: InferenceBody):
    try:
        runtime.game.record_inference(player_id, body.target, body.category,
                                      body.operation, body.data, body.client_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await runtime.hub.push_all()
    return runtime.game.player_view(player_id)
