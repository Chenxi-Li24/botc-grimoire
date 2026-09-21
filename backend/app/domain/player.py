"""Player account facade over canonical seat state."""

from __future__ import annotations

from dataclasses import dataclass, field
from ..state import SeatState


@dataclass
class Player:
    id: str
    name: str
    seat: int | None = None
    wish: str | None = None  # 许愿(仅大厅):善良/邪恶或自定义文字,说书人配板时参考;仅本人与说书人可见
    _seat_state: SeatState | None = field(default=None, repr=False, compare=False)

    def bind(self, seat_state: SeatState | None) -> None:
        self._seat_state = seat_state

    @property
    def role_id(self) -> str | None:
        return self._seat_state.character_id if self._seat_state else None

    @role_id.setter
    def role_id(self, value: str | None) -> None:
        if self._seat_state is not None:
            self._seat_state.character_id = value

    @property
    def alive(self) -> bool:
        return self._seat_state.alive if self._seat_state else True

    @alive.setter
    def alive(self, value: bool) -> None:
        if self._seat_state is not None:
            self._seat_state.alive = value
            self._seat_state.public_alive = value

    @property
    def died_day(self) -> int | None:
        return self._seat_state.died_day if self._seat_state else None

    @died_day.setter
    def died_day(self, value: int | None) -> None:
        if self._seat_state is not None:
            self._seat_state.died_day = value

    @property
    def dead_vote_used(self) -> bool:
        return self._seat_state.dead_vote_used if self._seat_state else False

    @dead_vote_used.setter
    def dead_vote_used(self, value: bool) -> None:
        if self._seat_state is not None:
            self._seat_state.dead_vote_used = value

    def public(self) -> dict:
        visible_alive = (self._seat_state.public_alive if self._seat_state else self.alive)
        return {"id": self.id, "name": self.name, "seat": self.seat, "alive": visible_alive}

    def private(self, roles: dict, fake_id: str | None = None) -> dict:
        """玩家自己看到的视图。fake_id 为认知覆盖:酒鬼看到说书人标记的假镇民角色。"""
        view = self.public()
        rid = fake_id if (fake_id and self.role_id) else self.role_id
        if rid:
            view["role"] = roles[rid]
        return view

    def storyteller(self, roles: dict) -> dict:
        """说书人全知视图。"""
        view = self.public()
        view["alive"] = self.alive
        view["wish"] = self.wish  # 许愿仅说书人可见(玩家座位列表里的 public() 不带)
        if self.role_id:
            view["role"] = roles[self.role_id]
        return view
