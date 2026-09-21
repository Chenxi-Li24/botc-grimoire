"""Explicit request contracts for storyteller night commands."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class NavigateBody(BaseModel):
    direction: Literal["previous", "next", "goto"]
    step_id: str | None = None
    force_token: str | None = None


class SelectNightTargetsBody(BaseModel):
    step_id: str | None = None
    selected_seats: list[int] = Field(default_factory=list)
    arbitrary_death: bool = False
    create_outcome: bool = True
    character_id: str | None = None
    acknowledged: bool = False


class PlayerNightActionBody(BaseModel):
    step_id: str
    selected_seats: list[int] = Field(default_factory=list)
    character_id: str | None = None


class ResolveOutcomeBody(BaseModel):
    outcome_id: str
    resolution: Literal[
        "secret_death", "no_death", "delayed", "redirected",
        "transformation", "choice_only",
    ]
    affected_seats: list[int] = Field(default_factory=list)
    rationale: str = ""
    details: dict[str, Any] = Field(default_factory=dict)


class InformationClaimBody(BaseModel):
    label: str
    value: Any = None
    truthful: bool


class InformationBody(BaseModel):
    action: Literal["prepare", "deliver", "correct"]
    actor_seat: int | None = None
    step_id: str | None = None
    targets: list[int] = Field(default_factory=list)
    registrations: list[dict[str, Any]] = Field(default_factory=list)
    source_event: str | None = None
    draft_id: str | None = None
    delivery_id: str | None = None
    delivered_result: Any = None
    claims: list[InformationClaimBody] | None = None
    reason: str = ""


class BalloonistBody(BaseModel):
    action: Literal["preview", "send"]
    step_id: str
    target: int | str
    registered_type: str | None = None
    registered_role: str | None = None
    truthful: bool | None = None
    correction_of: str | None = None


class EffectBody(BaseModel):
    action: Literal["poisoner", "widow", "cerenovus", "source_ability"]
    source_seat: int
    step_id: str | None = None
    target_seat: int | None = None
    claimed_character: str | None = None
    active: bool | None = None
    permanent: bool = False


class PitHagBody(BaseModel):
    action: Literal["preview", "confirm"] = "confirm"
    preview_id: str | None = None
    step_id: str | None = None
    actor_seat: int | None = None
    target_seat: int | None = None
    character_id: str | None = None


class UndoBody(BaseModel):
    event_id: str
    confirm: bool = False
