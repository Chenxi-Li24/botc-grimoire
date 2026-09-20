"""Compile current Python script modules into the normalized runtime contract."""

from dataclasses import asdict
from types import MappingProxyType
from typing import Iterable

from .models import CharacterSpec, NightTiming, ScriptPack, SelectionSpec
from .zh_cn import build_locale

KNOWN_TEAMS = frozenset({"townsfolk", "outsider", "minion", "demon"})
SPECIAL_STEPS = frozenset({"dusk", "dawn", "minioninfo", "demoninfo"})

START_KNOWING = frozenset({
    "washerwoman", "librarian", "investigator", "chef", "clockmaker",
    "grandmother", "godfather", "widow", "eviltwin", "noble", "panguan",
})
DEATH_TRIGGERS = frozenset({
    "ravenkeeper", "sage", "grandmother", "barber", "sweetheart",
    "moonchild", "tinker", "yanshi",
})

INFORMATION_RESOLVERS = {
    role_id: role_id
    for role_id in (
        "washerwoman", "librarian", "investigator", "chef", "empath",
        "fortuneteller", "undertaker", "grandmother", "chambermaid",
        "clockmaker", "dreamer", "mathematician", "flowergirl", "towncrier",
        "oracle", "juggler", "godfather", "balloonist", "noble", "panguan",
        "tixingguan", "seamstress",
    )
}

COMPLEX_HANDLERS = {
    "pithag": "pit-hag",
    "fang-gu": "fang-gu",
    "lil-monsta": "lil-monsta",
    "philosopher": "philosopher",
    "cannibal": "cannibal",
    "lunatic": "lunatic",
    "widow": "widow",
    "imp": "imp",
    "vigormortis": "vigormortis",
    "pukka": "pukka",
    "po": "po",
    "shabaloth": "shabaloth",
    "zombuul": "zombuul",
    "nodashii": "no-dashii",
    "vortox": "vortox",
}

SELECTIONS = {
    "fortuneteller": SelectionSpec(players=2, allow_self=True),
    "dreamer": SelectionSpec(players=1, allow_self=False),
    "gambler": SelectionSpec(players=1, characters=1),
    "snakecharmer": SelectionSpec(players=1, alive_only=True),
    "ravenkeeper": SelectionSpec(players=1),
    "godfather": SelectionSpec(players=1),
    "widow": SelectionSpec(players=1),
    "pithag": SelectionSpec(players=1, characters=1),
    "cerenovus": SelectionSpec(players=1, characters=1,
                                character_teams=("townsfolk", "outsider")),
    "poisoner": SelectionSpec(players=1),
    "monk": SelectionSpec(players=1, allow_self=False),
    "butler": SelectionSpec(players=1, allow_self=False),
    "sailor": SelectionSpec(players=1),
    "chambermaid": SelectionSpec(players=2),
    "exorcist": SelectionSpec(players=1),
    "innkeeper": SelectionSpec(players=2),
    "devilsadvocate": SelectionSpec(players=1),
    "imp": SelectionSpec(players=1),
    "fang-gu": SelectionSpec(players=1),
    "vigormortis": SelectionSpec(players=1),
    "nodashii": SelectionSpec(players=1),
    "vortox": SelectionSpec(players=1),
    "pukka": SelectionSpec(players=1),
    "shabaloth": SelectionSpec(players=2),
    "witch": SelectionSpec(players=1),
    "seamstress": SelectionSpec(players=2, allow_self=False),
    "professor": SelectionSpec(players=1),
    "assassin": SelectionSpec(players=1),
    "jianning": SelectionSpec(players=1),
}


def _positions(steps: Iterable[dict]) -> dict[str, int]:
    return {
        step["key"]: index
        for index, step in enumerate(steps)
        if step["key"] not in SPECIAL_STEPS
    }


def _selection_for(module, role_id: str) -> SelectionSpec | None:
    action = getattr(module, "NIGHT_ACTIONS", {}).get(role_id)
    if action is None:
        return SELECTIONS.get(role_id)
    return SelectionSpec(
        players=int(action.get("count", 0)),
        characters=1 if action.get("char") else 0,
        character_teams=("townsfolk", "outsider") if action.get("good_char") else (),
    )


def _trigger_for(role_id: str, first: int | None, other: int | None) -> str:
    if role_id in START_KNOWING:
        return "start-knowing"
    if role_id in DEATH_TRIGGERS:
        return "death"
    if first is not None and other is None:
        return "first-night"
    if first is None and other is None:
        return "passive"
    return "normal"


def compile_script_pack(module, order: dict[str, list[dict]]) -> ScriptPack:
    known_role_ids = {role["id"] for role in module.ROLES}
    unknown_steps = {
        step["key"]
        for kind in ("first", "other")
        for step in order.get(kind, ())
        if step["key"] not in SPECIAL_STEPS and step["key"] not in known_role_ids
    }
    if unknown_steps:
        raise ValueError(
            f"{module.SCRIPT_ID}: night order references unknown characters "
            f"{sorted(unknown_steps)}"
        )
    first_positions = _positions(order.get("first", ()))
    other_positions = _positions(order.get("other", ()))
    seen: set[str] = set()
    characters: list[CharacterSpec] = []
    for role in module.ROLES:
        role_id = role["id"]
        if role_id in seen:
            raise ValueError(f"{module.SCRIPT_ID}: duplicate character id {role_id}")
        seen.add(role_id)
        if role["team"] not in KNOWN_TEAMS:
            raise ValueError(f"{module.SCRIPT_ID}/{role_id}: unknown team {role['team']}")
        first = first_positions.get(role_id)
        other = other_positions.get(role_id)
        resolver = INFORMATION_RESOLVERS.get(role_id)
        handler = COMPLEX_HANDLERS.get(role_id)
        selection = _selection_for(module, role_id)
        if (first is not None or other is not None) and not (resolver or handler or selection):
            handler = "manual"
        characters.append(CharacterSpec(
            id=role_id,
            team=role["team"],
            name_key=f"character.{role_id}.name",
            ability_key=f"character.{role_id}.ability",
            english_name=role.get("en", role_id),
            night=NightTiming(
                first=first,
                other=other,
                trigger=_trigger_for(role_id, first, other),
            ),
            selection=selection,
            information_resolver=resolver,
            complex_handler=handler,
        ))
    locale = MappingProxyType(build_locale(module, order))
    return ScriptPack(
        id=module.SCRIPT_ID,
        min_players=module.MIN_PLAYERS,
        characters=tuple(characters),
        locale=locale,
        english_name=module.EN,
        adjust_roles=tuple(module.ADJUST_ROLES),
        source="official" if module.SCRIPT_ID in {
            "trouble-brewing", "bad-moon-rising", "sects-and-violets"
        } else "community",
    )


def compile_builtin_packs(modules, night_order) -> dict[str, ScriptPack]:
    modules = tuple(modules)
    packs = {
        module.SCRIPT_ID: compile_script_pack(module, night_order[module.SCRIPT_ID])
        for module in modules
    }
    if len(packs) != len(modules):
        raise ValueError("duplicate script id")
    return packs


def pack_to_view(pack: ScriptPack) -> dict:
    """Compatibility projection used by lobby code and existing save views."""
    roles = []
    for character in pack.characters:
        roles.append({
            "id": character.id,
            "name": pack.locale[character.name_key],
            "en": character.english_name,
            "team": character.team,
            "ability": pack.locale[character.ability_key],
            "night": asdict(character.night),
            "selection": asdict(character.selection) if character.selection else None,
            "information_resolver": character.information_resolver,
            "complex_handler": character.complex_handler,
        })
    return {
        "name": pack.locale[f"script.{pack.id}.name"],
        "en": pack.english_name,
        "min_players": pack.min_players,
        "roles": roles,
        "runtime_version": pack.version,
        "source": pack.source,
    }
