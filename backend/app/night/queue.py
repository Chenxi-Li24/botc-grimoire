"""Dynamic, seat-scoped night action queue."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from ..catalog import CharacterSpec, ScriptPack
from ..night_order import NIGHT_ORDER, SPECIAL_NIGHT_STEPS
from ..state import GameState, SeatState


@dataclass
class NightStep:
    id: str
    actor_seat: int | None
    character_id: str
    perceived_as: str | None
    trigger: str
    order: int
    status: str = "upcoming"
    skip_reason: str | None = None
    required_fields: tuple[str, ...] = ()
    depends_on: list[str] = field(default_factory=list)
    source: dict[str, Any] = field(default_factory=dict)
    values: dict[str, Any] = field(default_factory=dict)
    name: str = ""
    reminder: str = ""

    def to_dict(self, *, current: bool = False) -> dict[str, Any]:
        value = asdict(self)
        value["required_fields"] = list(self.required_fields)
        if current and self.status == "upcoming":
            value["status"] = "current"
        return value

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "NightStep":
        return cls(**{**value, "required_fields": tuple(value.get("required_fields", ()))})


class NightQueue:
    """Builds actions from canonical seats and preserves only executed history."""

    def __init__(self, state: GameState, pack: ScriptPack, night_no: int,
                 traveler_actions: list[dict[str, Any]] | None = None) -> None:
        self.state = state
        self.pack = pack
        self.night_no = night_no
        self.traveler_actions = traveler_actions or []
        self.steps: list[NightStep] = []
        self.current_step_id: str | None = None

    @property
    def kind(self) -> str:
        return "first" if self.night_no == 1 else "other"

    @property
    def current(self) -> NightStep | None:
        return next((step for step in self.steps if step.id == self.current_step_id), None)

    def _character(self, character_id: str) -> CharacterSpec | None:
        return self.pack.character_by_id.get(character_id)

    def _acting_character(self, seat: SeatState) -> str | None:
        # Drunk follows the schedule of the character they believe they are. Lunatic
        # retains its explicit early step so its target can feed the real Demon step.
        if seat.character_id == "drunk" and seat.perceived_character_id:
            return seat.perceived_character_id
        return seat.character_id

    def _required_fields(self, character: CharacterSpec) -> tuple[str, ...]:
        if self.night_no == 1 and character.id == "godfather":
            return ()
        if self.night_no == 1 and character.id == "lunatic":
            return ("acknowledged",)
        required: list[str] = []
        if character.selection and character.selection.players:
            required.append("targets")
        if character.selection and character.selection.characters:
            required.append("character")
        if character.complex_handler == "manual" and not required:
            required.append("acknowledged")
        return tuple(required)

    def _condition(self, seat: SeatState, character: CharacterSpec,
                   trigger: str) -> tuple[str, str | None, list[str]]:
        ability = seat.ability_state.get(seat.character_id or character.id, {})
        if trigger == "death":
            died_tonight = (not seat.alive and seat.died_day == self.night_no)
            if not died_tonight:
                return "skipped", "death_trigger_not_met", []
            if (character.id == "sage"
                    and not (seat.death_record or {}).get("is_demon_attack")):
                return "skipped", "requires_demon_attack", []
            dependencies = [seat.died_at] if seat.died_at else []
            return "upcoming", None, dependencies
        if not seat.alive:
            return "skipped", "actor_dead", []
        if ability.get("active") is False or ability.get("can_act") is False:
            return "skipped", "ability_inactive", []
        return "upcoming", None, []

    def _special_allowed(self, key: str) -> bool:
        if key in {"dusk", "dawn"}:
            return True
        if self.night_no != 1:
            return False
        teams = {
            character.team
            for seat in self.state.seats.values()
            if seat.character_id
            and (character := self._character(seat.character_id)) is not None
        }
        return ((key == "minioninfo" and "minion" in teams)
                or (key == "demoninfo" and "demon" in teams))

    def _step_id(self, order: int, actor: int | None, character_id: str,
                 perceived_as: str | None, trigger: str) -> str:
        identity = actor if actor is not None else "special"
        perceived = perceived_as or "real"
        return f"night:{self.night_no}:{order}:{identity}:{character_id}:{perceived}:{trigger}"

    def _generate(self) -> list[NightStep]:
        sheet = NIGHT_ORDER[self.pack.id][self.kind]
        generated: list[NightStep] = []
        for sheet_index, item in enumerate(sheet):
            key = item["key"]
            base_order = sheet_index * 100
            if key in SPECIAL_NIGHT_STEPS:
                if not self._special_allowed(key):
                    continue
                generated.append(NightStep(
                    id=self._step_id(base_order, None, key, None, "special"),
                    actor_seat=None,
                    character_id=key,
                    perceived_as=None,
                    trigger="special",
                    order=base_order,
                    name=self.pack.locale.get(f"night.{self.kind}.{key}.name", item["name"]),
                    reminder=self.pack.locale.get(
                        f"night.{self.kind}.{key}.reminder", item["hint"]),
                ))
                if key == "dusk":
                    for offset, traveler in enumerate(self.traveler_actions, start=1):
                        traveler_id = traveler["character_id"]
                        generated.append(NightStep(
                            id=self._step_id(base_order + offset, None, traveler_id,
                                             None, "traveler"),
                            actor_seat=None,
                            character_id=traveler_id,
                            perceived_as=None,
                            trigger="traveler",
                            order=base_order + offset,
                            required_fields=tuple(traveler.get("required_fields", ())),
                            source={"traveler_ids": traveler.get("traveler_ids", [])},
                            name=traveler.get("name", traveler_id),
                            reminder=traveler.get("reminder", ""),
                        ))
                continue

            scheduled = self._character(key)
            if scheduled is None:
                continue
            matching = [
                seat for seat in self.state.seats.values()
                if self._acting_character(seat) == key
            ]
            for seat in sorted(matching, key=lambda value: value.seat):
                real = self._character(seat.character_id) if seat.character_id else None
                if real is None:
                    continue
                perceived = (seat.perceived_character_id
                             if seat.character_id == "lunatic"
                             else key if key != seat.character_id else None)
                trigger = scheduled.night.trigger_for(self.night_no == 1)
                status, skip_reason, dependencies = self._condition(seat, scheduled, trigger)
                order = base_order + seat.seat
                generated.append(NightStep(
                    id=self._step_id(order, seat.seat, real.id, perceived, trigger),
                    actor_seat=seat.seat,
                    character_id=real.id,
                    perceived_as=perceived,
                    trigger=trigger,
                    order=order,
                    status=status,
                    skip_reason=skip_reason,
                    required_fields=self._required_fields(scheduled),
                    depends_on=dependencies,
                    source={"ability_character": scheduled.id,
                            "claimed_by": seat.claimed_by},
                    name=self.pack.locale.get(scheduled.name_key, scheduled.english_name),
                    reminder=self.pack.locale.get(
                        f"night.{self.kind}.{scheduled.id}.reminder",
                        self.pack.locale.get(scheduled.ability_key, "")),
                ))

        # Imported sheets are allowed to put Lunatic elsewhere; the interaction contract
        # is stricter: each Lunatic choice must be visible before a real Demon action.
        demon_steps = [step for step in generated
                       if step.actor_seat is not None
                       and step.perceived_as is None
                       and (character := self._character(step.character_id)) is not None
                       and character.team == "demon"
                       and step.trigger != "special"]
        lunatic_steps = [step for step in generated if step.character_id == "lunatic"]
        if demon_steps and lunatic_steps:
            first_demon_order = min(step.order for step in demon_steps)
            for offset, step in enumerate(lunatic_steps, start=1):
                if step.order >= first_demon_order:
                    step.order = first_demon_order - len(lunatic_steps) + offset - 1
        generated.sort(key=lambda step: (step.order, step.actor_seat or 0, step.id))
        return generated

    def build(self) -> list[NightStep]:
        self.steps = self._generate()
        self.current_step_id = self.steps[0].id if self.steps else None
        return self.steps

    def rebuild_suffix(self, cause_event_id: str | None = None) -> list[NightStep]:
        if not self.steps:
            return self.build()
        old_by_id = {step.id: step for step in self.steps}
        current = self.current
        cutoff = current.order if current else -1
        terminal = [step for step in self.steps
                    if step.status in {"completed", "undone"}
                    or (step.status == "skipped" and step.skip_reason == "forced")]
        terminal_ids = {step.id for step in terminal}
        fresh = self._generate()
        rebuilt: list[NightStep] = list(terminal)
        for step in fresh:
            if step.id in terminal_ids:
                continue
            previous = old_by_id.get(step.id)
            if previous is not None:
                step.values = previous.values
            elif current is not None and step.order < cutoff:
                continue
            if cause_event_id and cause_event_id not in step.depends_on and step.trigger in {
                "death", "created", "start-knowing",
            }:
                step.depends_on.append(cause_event_id)
            rebuilt.append(step)
        rebuilt.sort(key=lambda step: (step.order, step.actor_seat or 0, step.id))
        self.steps = rebuilt
        if self.current_step_id not in {step.id for step in rebuilt}:
            next_step = next((step for step in rebuilt if step.order >= cutoff
                              and step.status not in {"completed", "undone"}), None)
            self.current_step_id = next_step.id if next_step else (rebuilt[-1].id if rebuilt else None)
        return self.steps

    def step_for(self, seat: int, character_id: str,
                 trigger: str | None = None) -> NightStep:
        step = next((item for item in self.steps
                     if item.actor_seat == seat
                     and (item.character_id == character_id
                          or item.perceived_as == character_id)
                     and (trigger is None or item.trigger == trigger)), None)
        if step is None:
            raise KeyError((seat, character_id, trigger))
        return step

    def dump(self) -> dict[str, Any]:
        return {
            "night_no": self.night_no,
            "current_step_id": self.current_step_id,
            "steps": [step.to_dict() for step in self.steps],
        }

    def restore(self, value: dict[str, Any]) -> None:
        if int(value.get("night_no", -1)) != self.night_no:
            self.build()
            return
        self.steps = [NightStep.from_dict(item) for item in value.get("steps", ())]
        self.current_step_id = value.get("current_step_id")
        if not self.steps:
            self.build()
        elif self.current_step_id not in {step.id for step in self.steps}:
            self.current_step_id = self.steps[0].id

    def projection(self) -> dict[str, Any]:
        return {
            "night_no": self.night_no,
            "current_step_id": self.current_step_id,
            "steps": [step.to_dict(current=step.id == self.current_step_id)
                      for step in self.steps],
        }
