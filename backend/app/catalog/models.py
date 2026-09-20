"""Normalized, source-agnostic character and script contracts."""

from dataclasses import dataclass, field
from typing import Mapping


@dataclass(frozen=True)
class NightTiming:
    first: int | None = None
    other: int | None = None
    trigger: str = "normal"


@dataclass(frozen=True)
class SelectionSpec:
    players: int = 0
    characters: int = 0
    distinct_players: bool = True
    allow_self: bool = True
    alive_only: bool = False
    character_teams: tuple[str, ...] = ()


@dataclass(frozen=True)
class CharacterSpec:
    id: str
    team: str
    name_key: str
    ability_key: str
    english_name: str
    night: NightTiming = field(default_factory=NightTiming)
    selection: SelectionSpec | None = None
    information_resolver: str | None = None
    complex_handler: str | None = None


@dataclass(frozen=True)
class ScriptPack:
    id: str
    min_players: int
    characters: tuple[CharacterSpec, ...]
    locale: Mapping[str, str]
    english_name: str
    adjust_roles: tuple[str, ...] = ()
    source: str = "builtin"
    version: int = 1

    @property
    def character_by_id(self) -> dict[str, CharacterSpec]:
        return {character.id: character for character in self.characters}
