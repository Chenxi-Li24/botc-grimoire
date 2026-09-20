"""Pure information resolvers over canonical facts."""

from __future__ import annotations

from dataclasses import dataclass, field
from itertools import combinations
from typing import Any, Callable

from ..catalog import ScriptPack
from ..state import GameState, SeatState
from .ability_state import AbilityStateStore


@dataclass
class ResolverContext:
    state: GameState
    pack: ScriptPack
    abilities: AbilityStateStore
    actor_seat: int
    targets: list[int]
    registrations: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class ResolverResult:
    true_result: Any
    legal_results: list[Any]
    claims: list[dict[str, Any]]
    requires_registration: bool = False
    discretion: bool = False
    unknown: bool = False


Resolver = Callable[[ResolverContext], ResolverResult]


def _character(ctx: ResolverContext, seat: int) -> str | None:
    registered = next((item.get("character_id") for item in ctx.registrations
                       if item.get("seat") == seat and item.get("character_id")), None)
    return registered or ctx.state.seat(seat).character_id


def _alignment(ctx: ResolverContext, seat: int) -> str:
    registered = next((item.get("alignment") for item in ctx.registrations
                       if item.get("seat") == seat and item.get("alignment")), None)
    return registered or ctx.state.seat(seat).alignment


def _ambiguous_registration(ctx: ResolverContext, seats: list[int] | None = None) -> bool:
    scope = seats or [seat.seat for seat in ctx.state.seats.values() if seat.character_id]
    decided = {item.get("seat") for item in ctx.registrations}
    return any(ctx.state.seat(seat).character_id in {"spy", "recluse"} and seat not in decided
               for seat in scope)


def _scalar(value: Any, label: str = "result", *, registration: bool = False) -> ResolverResult:
    return ResolverResult(
        true_result=value,
        legal_results=[value],
        claims=[{"label": label, "value": value, "truthful": True}],
        requires_registration=registration,
    )


def _occupied(ctx: ResolverContext) -> list[SeatState]:
    return sorted((seat for seat in ctx.state.seats.values() if seat.character_id),
                  key=lambda seat: seat.seat)


def chef(ctx: ResolverContext) -> ResolverResult:
    seats = _occupied(ctx)
    count = 0
    if len(seats) > 1:
        for index, seat in enumerate(seats):
            nxt = seats[(index + 1) % len(seats)]
            if _alignment(ctx, seat.seat) == _alignment(ctx, nxt.seat) == "evil":
                count += 1
    return _scalar(count, "evil_neighbor_pairs",
                   registration=_ambiguous_registration(ctx))


def clockmaker(ctx: ResolverContext) -> ResolverResult:
    seats = _occupied(ctx)
    demons = [index for index, seat in enumerate(seats)
              if (character := ctx.pack.character_by_id.get(_character(ctx, seat.seat) or ""))
              and character.team == "demon"]
    minions = [index for index, seat in enumerate(seats)
               if (character := ctx.pack.character_by_id.get(_character(ctx, seat.seat) or ""))
               and character.team == "minion"]
    if not demons or not minions:
        return _scalar(0, "steps_between")
    size = len(seats)
    value = min(min((distance := abs(demon - minion)) - 1,
                    size - distance - 1)
                for demon in demons for minion in minions)
    return _scalar(value, "steps_between", registration=_ambiguous_registration(ctx))


def _nearest_alive(ctx: ResolverContext, actor: int) -> list[int]:
    seats = _occupied(ctx)
    indexes = {seat.seat: index for index, seat in enumerate(seats)}
    if actor not in indexes or len(seats) < 2:
        return []
    found = []
    origin = indexes[actor]
    for direction in (-1, 1):
        for distance in range(1, len(seats)):
            candidate = seats[(origin + direction * distance) % len(seats)]
            if candidate.alive:
                found.append(candidate.seat)
                break
    return list(dict.fromkeys(found))


def empath(ctx: ResolverContext) -> ResolverResult:
    neighbors = _nearest_alive(ctx, ctx.actor_seat)
    value = sum(_alignment(ctx, seat) == "evil" for seat in neighbors)
    return _scalar(value, "evil_alive_neighbors",
                   registration=_ambiguous_registration(ctx, neighbors))


def fortuneteller(ctx: ResolverContext) -> ResolverResult:
    red_herring = ctx.abilities.fortune_teller_red_herring(ctx.actor_seat)
    seen_demon = False
    for seat in ctx.targets:
        role_id = _character(ctx, seat)
        role = ctx.pack.character_by_id.get(role_id or "")
        seen_demon = seen_demon or bool(role and role.team == "demon") or seat == red_herring
    return _scalar(seen_demon, "demon_detected",
                   registration=_ambiguous_registration(ctx, ctx.targets))


def seamstress(ctx: ResolverContext) -> ResolverResult:
    value = (len(ctx.targets) == 2
             and _alignment(ctx, ctx.targets[0]) == _alignment(ctx, ctx.targets[1]))
    return _scalar(value, "same_alignment",
                   registration=_ambiguous_registration(ctx, ctx.targets))


def chambermaid(ctx: ResolverContext) -> ResolverResult:
    prior_night = max(0, int(ctx.abilities.get(
        ctx.actor_seat, "_system", "current_night", 1)) - 1)
    value = sum(bool(ctx.abilities.wake_events(seat, prior_night)) for seat in ctx.targets)
    return _scalar(value, "selected_players_woke")


def oracle(ctx: ResolverContext) -> ResolverResult:
    dead = [seat.seat for seat in ctx.state.seats.values()
            if seat.character_id and not seat.alive]
    value = sum(_alignment(ctx, seat) == "evil" for seat in dead)
    return _scalar(value, "dead_evil_players",
                   registration=_ambiguous_registration(ctx, dead))


def mathematician(ctx: ResolverContext) -> ResolverResult:
    value = int(ctx.abilities.get(ctx.actor_seat, "mathematician", "malfunction_count", 0))
    return _scalar(value, "malfunction_count")


def _start_role_candidates(ctx: ResolverContext, team: str) -> ResolverResult:
    holders = [seat for seat in _occupied(ctx)
               if (character := ctx.pack.character_by_id.get(_character(ctx, seat.seat) or ""))
               and character.team == team]
    if not holders:
        result = {"character_id": None, "seats": [], "count": 0}
        return _scalar(result, f"{team}_identity",
                       registration=_ambiguous_registration(ctx))
    legal = []
    all_seats = [seat.seat for seat in _occupied(ctx)]
    for holder in holders:
        for decoy in all_seats:
            if decoy == holder.seat:
                continue
            value = {"character_id": _character(ctx, holder.seat),
                     "seats": sorted([holder.seat, decoy]), "count": 1}
            if value not in legal:
                legal.append(value)
    true_result = legal[0] if legal else {
        "character_id": _character(ctx, holders[0].seat),
        "seats": [holders[0].seat], "count": 1,
    }
    return ResolverResult(
        true_result=true_result,
        legal_results=legal or [true_result],
        claims=[{"label": f"{team}_identity", "value": true_result, "truthful": True}],
        requires_registration=_ambiguous_registration(ctx),
        discretion=len(legal) > 1,
    )


def washerwoman(ctx: ResolverContext) -> ResolverResult:
    return _start_role_candidates(ctx, "townsfolk")


def librarian(ctx: ResolverContext) -> ResolverResult:
    return _start_role_candidates(ctx, "outsider")


def investigator(ctx: ResolverContext) -> ResolverResult:
    return _start_role_candidates(ctx, "minion")


def noble(ctx: ResolverContext) -> ResolverResult:
    seats = [seat.seat for seat in _occupied(ctx)]
    legal = [list(group) for group in combinations(seats, 3)
             if sum(_alignment(ctx, seat) == "evil" for seat in group) == 1]
    true_result = legal[0] if legal else []
    return ResolverResult(
        true_result=true_result,
        legal_results=legal,
        claims=[{"label": "exactly_one_evil", "value": true_result,
                 "truthful": bool(true_result)}],
        requires_registration=_ambiguous_registration(ctx),
        discretion=True,
    )


def dreamer(ctx: ResolverContext) -> ResolverResult:
    if len(ctx.targets) != 1:
        return ResolverResult(None, [], [], discretion=True)
    target = ctx.targets[0]
    actual = _character(ctx, target)
    actual_spec = ctx.pack.character_by_id.get(actual or "")
    good = [role.id for role in ctx.pack.characters
            if role.team in {"townsfolk", "outsider"}]
    evil = [role.id for role in ctx.pack.characters if role.team in {"minion", "demon"}]
    legal = []
    for good_id in good:
        for evil_id in evil:
            if actual in {good_id, evil_id}:
                legal.append({"target": target, "good_character": good_id,
                              "evil_character": evil_id})
    true_result = {"target": target, "character_id": actual,
                   "alignment": ("good" if actual_spec and actual_spec.team in {"townsfolk", "outsider"}
                                 else "evil")}
    return ResolverResult(
        true_result=true_result,
        legal_results=legal,
        claims=[{"label": "target_character", "value": actual, "truthful": True}],
        requires_registration=_ambiguous_registration(ctx, [target]),
        discretion=True,
    )


def grandmother(ctx: ResolverContext) -> ResolverResult:
    grandchild = ctx.abilities.grandchild(ctx.actor_seat)
    if grandchild:
        return _scalar(grandchild, "grandchild")
    candidates = [{"seat": seat.seat, "character_id": seat.character_id}
                  for seat in _occupied(ctx) if seat.seat != ctx.actor_seat]
    return ResolverResult(None, candidates, [], discretion=True)


def godfather(ctx: ResolverContext) -> ResolverResult:
    outsiders = [seat.character_id for seat in _occupied(ctx)
                 if ctx.pack.character_by_id.get(seat.character_id or "")
                 and ctx.pack.character_by_id[seat.character_id].team == "outsider"]
    return _scalar(outsiders, "outsiders_in_play",
                   registration=_ambiguous_registration(ctx))


def retrospective(ctx: ResolverContext) -> ResolverResult:
    role = ctx.state.seat(ctx.actor_seat).character_id or "_system"
    value = ctx.abilities.get(ctx.actor_seat, role, "information_result")
    if value is None:
        return ResolverResult(None, [], [], discretion=True, unknown=True)
    return _scalar(value)


RESOLVERS: dict[str, Resolver] = {
    "chef": chef,
    "clockmaker": clockmaker,
    "empath": empath,
    "fortuneteller": fortuneteller,
    "seamstress": seamstress,
    "chambermaid": chambermaid,
    "oracle": oracle,
    "mathematician": mathematician,
    "washerwoman": washerwoman,
    "librarian": librarian,
    "investigator": investigator,
    "noble": noble,
    "dreamer": dreamer,
    "grandmother": grandmother,
    "godfather": godfather,
    "undertaker": retrospective,
    "flowergirl": retrospective,
    "towncrier": retrospective,
    "juggler": retrospective,
    "balloonist": retrospective,
    "panguan": retrospective,
    "tixingguan": retrospective,
}


def resolve_information(resolver_key: str | None, context: ResolverContext) -> ResolverResult:
    resolver = RESOLVERS.get(resolver_key or "")
    if resolver is None:
        return ResolverResult(None, [], [], discretion=True, unknown=True)
    return resolver(context)
