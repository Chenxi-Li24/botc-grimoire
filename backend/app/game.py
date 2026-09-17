"""游戏状态管理(单局、内存态):说书人配置板子/人数,玩家选环形座位入座。"""

import random
import secrets
from dataclasses import dataclass

from .roles import (COMPOSITION, DEMON, MINION, OUTSIDER, SCRIPTS,
                    SCRIPT_ADJUST_ROLES, ROLE_ADJUSTMENTS, TOWNSFOLK)


@dataclass
class Player:
    id: str
    name: str
    seat: int | None = None
    role_id: str | None = None
    alive: bool = True

    def public(self) -> dict:
        return {"id": self.id, "name": self.name, "seat": self.seat, "alive": self.alive}

    def private(self, roles: dict) -> dict:
        """玩家自己看到的视图(醉鬼伪装等逻辑以后在这里扩展)。"""
        view = self.public()
        if self.role_id:
            view["role"] = roles[self.role_id]
        return view

    def storyteller(self, roles: dict) -> dict:
        """说书人全知视图。"""
        view = self.public()
        if self.role_id:
            view["role"] = roles[self.role_id]
        return view


class GameManager:
    """一局游戏的全部状态;重启进程即重置,存档留待后续。"""

    def __init__(self) -> None:
        self.reset()
        self.script_id: str = "trouble-brewing"  # 说书人可配置
        self.player_count: int = 6

    def reset(self) -> None:
        self.players: dict[str, Player] = {}
        self.status: str = "lobby"  # lobby | playing

    @property
    def roles(self) -> dict:
        return {r["id"]: r for r in SCRIPTS[self.script_id]["roles"]}

    @property
    def seats(self) -> dict[int, Player]:
        return {p.seat: p for p in self.players.values() if p.seat is not None}

    # ---- 局配置 ----

    def configure(self, script_id: str, player_count: int) -> None:
        if script_id not in SCRIPTS:
            raise ValueError("未知脚本")
        if not 5 <= player_count <= 15:
            raise ValueError("人数需在 5~15 之间")
        self.script_id = script_id
        self.player_count = player_count
        for p in self.players.values():  # 改配置 → 清空座位与角色,玩家重新入座
            p.seat = None
            p.role_id = None
            p.alive = True
        self.status = "lobby"

    # ---- 玩家进出 ----

    def add_player(self, name: str) -> Player:
        player = Player(id=secrets.token_hex(4), name=name.strip()[:20])
        self.players[player.id] = player
        return player

    def sit(self, player_id: str, seat: int) -> None:
        if player_id not in self.players:
            raise ValueError("玩家不存在")
        if not 1 <= seat <= self.player_count:
            raise ValueError(f"座位需在 1~{self.player_count} 之间")
        if self.status == "playing":
            raise ValueError("游戏进行中,不能换座")
        owner = self.seats.get(seat)
        if owner and owner.id != player_id:
            raise ValueError(f"座位 {seat} 已被 {owner.name} 占用")
        self.players[player_id].seat = seat

    def remove_player(self, player_id: str) -> None:
        if player_id not in self.players:
            return
        del self.players[player_id]  # 座位随玩家释放

    # ---- 角色分配 ----

    def assign_roles(self) -> list[dict]:
        n = self.player_count
        if self.status == "playing":
            raise ValueError("本局已开始,先重置")
        if any(p.seat is None for p in self.players.values()):
            raise ValueError("还有玩家未选择座位")
        if len(self.players) < n:
            raise ValueError(f"还有 {n - len(self.players)} 个空座位,等玩家入座")

        comp = list(COMPOSITION[n])
        by_team = {team: [r for r in SCRIPTS[self.script_id]["roles"] if r["team"] == team]
                   for team in (TOWNSFOLK, OUTSIDER, MINION, DEMON)}

        pool = random.sample(by_team[DEMON], comp[3])
        minions = random.sample(by_team[MINION], comp[2])
        pool += minions
        # 脚本特殊调整(男爵/方古等改变配比,在抽外来者之前结算)
        for rid in SCRIPT_ADJUST_ROLES.get(self.script_id, ()):
            if any(r["id"] == rid for r in pool):
                dt, do, dm, dd = ROLE_ADJUSTMENTS[rid]
                comp[0] += dt
                comp[1] += do
                comp[2] += dm
                comp[3] += dd
        pool += random.sample(by_team[OUTSIDER], comp[1])
        pool += random.sample(by_team[TOWNSFOLK], comp[0])
        random.shuffle(pool)

        by_seat = sorted(self.players.values(), key=lambda p: p.seat)
        for player, role in zip(by_seat, pool):
            player.role_id = role["id"]
        self.status = "playing"
        return [p.storyteller(self.roles) for p in by_seat]

    # ---- 状态操作 ----

    def toggle_alive(self, player_id: str) -> None:
        if player_id in self.players:
            self.players[player_id].alive = not self.players[player_id].alive

    # ---- 视图 ----

    def _seat_slots(self, st_view: bool, my_id: str | None = None) -> list[dict]:
        seat_of = self.seats
        slots = []
        for i in range(1, self.player_count + 1):
            p = seat_of.get(i)
            if p is None:
                slots.append({"seat": i, "player": None})
                continue
            entry = p.storyteller(self.roles) if st_view else p.public()
            slot = {"seat": i, "player": entry}
            if my_id is not None:  # is_me 属于座位槽位层,不属于 player
                slot["is_me"] = p.id == my_id
            slots.append(slot)
        return slots

    def player_view(self, player_id: str) -> dict:
        me = self.players[player_id]
        return {
            "status": self.status,
            "script": SCRIPTS[self.script_id]["name"],
            "player_count": self.player_count,
            "me": me.private(self.roles),
            "seats": self._seat_slots(st_view=False, my_id=player_id),
        }

    def storyteller_view(self) -> dict:
        return {
            "status": self.status,
            "script": self.script_id,
            "player_count": self.player_count,
            "scripts": [{"id": sid, "name": s["name"], "en": s["en"]}
                        for sid, s in SCRIPTS.items()],
            "seats": self._seat_slots(st_view=True),
        }
