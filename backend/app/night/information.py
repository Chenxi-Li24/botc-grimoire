"""Structured information drafting, delivery, truth annotation, and correction."""

from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any
from uuid import uuid4

from ..catalog import ScriptPack
from ..state import GameState
from .ability_state import AbilityStateStore
from .effects import EffectLedger
from .journal import EventJournal
from .models import timestamp
from .resolvers import ResolverContext, ResolverResult, resolve_information


@dataclass
class InformationClaim:
    label: str
    value: Any
    truthful: bool


@dataclass
class InformationDraft:
    id: str
    actor_seat: int
    real_character: str
    perceived_character: str
    resolver_key: str | None
    targets: list[int]
    true_result: Any
    legal_results: list[Any]
    registrations: list[dict]
    effect_snapshot: list[str]
    reason: str | None
    source_event: str
    prepared_event: str
    status: str = "pending"
    created_at: str = field(default_factory=timestamp)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "InformationDraft":
        return cls(**value)


@dataclass
class InformationDelivery:
    id: str
    actor_seat: int
    real_character: str
    perceived_character: str
    targets: list[int]
    true_result: Any
    delivered_result: Any
    claims: list[InformationClaim]
    registrations: list[dict]
    effect_snapshot: list[str]
    reason: str | None
    source_event: str
    draft_id: str
    automatic: bool = False
    accepted_at: str = field(default_factory=timestamp)
    delivered_at: str | None = None
    corrections: list[dict[str, Any]] = field(default_factory=list)

    @property
    def event_id(self) -> str:
        return self.source_event

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "InformationDelivery":
        value = deepcopy(value)
        value["claims"] = [InformationClaim(**claim) if isinstance(claim, dict) else claim
                           for claim in value.get("claims", ())]
        return cls(**value)


class InformationEngine:
    def __init__(self, state: GameState, pack: ScriptPack, journal: EventJournal,
                 effects: EffectLedger, abilities: AbilityStateStore) -> None:
        self.state = state
        self.pack = pack
        self.journal = journal
        self.effects = effects
        self.abilities = abilities

    def _actor(self, actor_seat: int) -> tuple[str, str]:
        seat = self.state.seat(actor_seat)
        if seat.character_id is None:
            raise ValueError("actor seat has no character")
        real = seat.character_id
        perceived = seat.perceived_character_id if real == "drunk" else real
        if perceived is None:
            raise ValueError("cognitive override has no perceived character")
        return real, perceived

    def _impairment(self, actor_seat: int, real: str,
                    perceived: str) -> tuple[list[str], list[str]]:
        snapshot = [effect.id for effect in self.effects.active_for_seat(actor_seat)]
        reasons = [effect.type for effect in self.effects.active_for_seat(actor_seat)
                   if effect.type in {"poisoned", "drunk", "information_override"}]
        if real == "drunk":
            snapshot.append("intrinsic:drunk")
            reasons.append("drunk")
        perceived_spec = self.pack.character_by_id.get(perceived)
        vortox_in_play = any(
            seat.character_id == "vortox" and seat.alive
            for seat in self.state.seats.values()
        )
        if (vortox_in_play and perceived_spec
                and perceived_spec.team == "townsfolk"):
            snapshot.append("global:vortox")
            reasons.append("vortox_forced_false")
        return list(dict.fromkeys(snapshot)), list(dict.fromkeys(reasons))

    @staticmethod
    def _reason(result: ResolverResult, impairments: list[str]) -> str | None:
        if impairments:
            return ",".join(impairments)
        if result.requires_registration:
            return "registration_choice"
        if result.unknown:
            return "unknown_resolver"
        if result.discretion or len(result.legal_results) != 1:
            return "storyteller_discretion"
        return None

    def prepare(self, actor_seat: int, targets: list[int] | None = None, *,
                registrations: list[dict] | None = None,
                source_event: str | None = None) -> InformationDraft | InformationDelivery:
        targets = list(targets or ())
        for target in targets:
            self.state.seat(target)
        real, perceived = self._actor(actor_seat)
        spec = self.pack.character_by_id.get(perceived)
        resolver_key = spec.information_resolver if spec else None
        context = ResolverContext(
            state=self.state,
            pack=self.pack,
            abilities=self.abilities,
            actor_seat=actor_seat,
            targets=targets,
            registrations=deepcopy(registrations or []),
        )
        result = resolve_information(resolver_key, context)
        effect_snapshot, impairments = self._impairment(actor_seat, real, perceived)
        reason = self._reason(result, impairments)
        draft_id = uuid4().hex
        known = {event.id for event in self.journal.records}
        source = source_event or "information:manual"
        prepared = self.journal.append(
            "information_prepared",
            {"draft_id": draft_id, "actor_seat": actor_seat,
             "real_character": real, "perceived_character": perceived},
            {"op": "delete", "path": ["information_drafts", draft_id]},
            depends_on=[source] if source in known else [],
        )
        draft = InformationDraft(
            id=draft_id,
            actor_seat=actor_seat,
            real_character=real,
            perceived_character=perceived,
            resolver_key=resolver_key,
            targets=targets,
            true_result=deepcopy(result.true_result),
            legal_results=deepcopy(result.legal_results),
            registrations=deepcopy(context.registrations),
            effect_snapshot=effect_snapshot,
            reason=reason,
            source_event=source,
            prepared_event=prepared.id,
        )
        self.state.information_drafts[draft.id] = draft
        if reason is None and len(result.legal_results) == 1:
            return self.deliver(
                draft.id,
                delivered_result=result.legal_results[0],
                claims=result.claims,
                automatic=True,
            )
        return draft

    @staticmethod
    def _claims(values: list[InformationClaim | dict]) -> list[InformationClaim]:
        claims = [value if isinstance(value, InformationClaim) else InformationClaim(**value)
                  for value in values]
        if any(type(claim.truthful) is not bool for claim in claims):
            raise ValueError("every information claim needs an explicit truthful flag")
        return claims

    @staticmethod
    def _derive_claims(draft: InformationDraft, delivered_result: Any) -> list[InformationClaim]:
        if draft.resolver_key == "dreamer" and isinstance(delivered_result, dict):
            actual = (draft.true_result or {}).get("character_id")
            return [
                InformationClaim("good_character", delivered_result.get("good_character"),
                                 delivered_result.get("good_character") == actual),
                InformationClaim("evil_character", delivered_result.get("evil_character"),
                                 delivered_result.get("evil_character") == actual),
            ]
        truthful = (delivered_result in draft.legal_results
                    if draft.legal_results else delivered_result == draft.true_result)
        return [InformationClaim("result", deepcopy(delivered_result), truthful)]

    def deliver(self, draft_id: str, delivered_result: Any, *,
                claims: list[InformationClaim | dict] | None = None,
                reason: str | None = None, automatic: bool = False) -> InformationDelivery:
        try:
            draft = self.state.information_drafts[draft_id]
        except KeyError as exc:
            raise KeyError(draft_id) from exc
        if draft.status != "pending":
            raise ValueError("information draft has already been delivered")
        explicit_required = any(item in (draft.reason or "") for item in (
            "drunk", "poisoned", "information_override", "vortox_forced_false",
        ))
        if claims is None and explicit_required:
            raise ValueError("impaired information requires explicit truth flags")
        normalized_claims = (self._claims(claims) if claims is not None
                             else self._derive_claims(draft, delivered_result))
        if "vortox_forced_false" in (draft.reason or "") and any(
            claim.truthful for claim in normalized_claims
        ):
            raise ValueError("Vortox information must be false")
        delivery_id = uuid4().hex
        event = self.journal.append(
            "message_information",
            {"message_id": delivery_id, "draft_id": draft.id,
             "actor_seat": draft.actor_seat,
             "delivered_result": deepcopy(delivered_result)},
            {"op": "noop"},
            depends_on=[draft.prepared_event],
        )
        delivery = InformationDelivery(
            id=delivery_id,
            actor_seat=draft.actor_seat,
            real_character=draft.real_character,
            perceived_character=draft.perceived_character,
            targets=list(draft.targets),
            true_result=deepcopy(draft.true_result),
            delivered_result=deepcopy(delivered_result),
            claims=normalized_claims,
            registrations=deepcopy(draft.registrations),
            effect_snapshot=list(draft.effect_snapshot),
            reason=reason or draft.reason,
            source_event=event.id,
            draft_id=draft.id,
            automatic=automatic,
            delivered_at=None,
        )
        self.state.information_deliveries[delivery.id] = delivery
        draft.status = "delivered"
        if automatic:
            self.state.information_notices.append({
                "id": uuid4().hex,
                "kind": "automatic_information_sent",
                "actor_seat": draft.actor_seat,
                "delivery_id": delivery.id,
                "payload": deepcopy(delivered_result),
                "created_at": timestamp(),
            })
        return delivery

    def correct(self, delivery_id: str,
                claims: list[InformationClaim | dict], reason: str) -> dict[str, Any]:
        delivery = self.state.information_deliveries[delivery_id]
        corrected = self._claims(claims)
        correction = {
            "id": uuid4().hex,
            "claims": [asdict(claim) for claim in corrected],
            "reason": reason,
            "created_at": timestamp(),
        }
        event = self.journal.append(
            "information_correction",
            {"delivery_id": delivery_id, "correction": deepcopy(correction)},
            {"op": "noop"},
            depends_on=[delivery.source_event],
        )
        correction["event_id"] = event.id
        delivery.corrections.append(correction)
        return correction

    def projection(self) -> dict[str, Any]:
        event_states = {event.id: event.state for event in self.journal.records}
        return {
            "drafts": [draft.to_dict() for draft in self.state.information_drafts.values()
                       if draft.status == "pending"],
            "deliveries": [{**delivery.to_dict(),
                            "retracted": event_states.get(delivery.source_event) == "undone"}
                           for delivery in self.state.information_deliveries.values()],
            "notices": deepcopy(self.state.information_notices),
        }
