"""游戏状态管理(单局、内存态)。"""

import random
import secrets
from dataclasses import dataclass

from .roles import (DEMON, MINION, OUTSIDER, TB_COMPOSITION, TB_ROLES,
                    TOWNSFOLK)


@dataclass
class Player:
    id: str
    name: str
    seat: int
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
        self.roles_by_id = {r["id"]: r for r in TB_ROLES}
        self.reset()

    def reset(self) -> None:
        self.players: dict[str, Player] = {}
        self.status: str = "lobby"  # lobby | playing
        self.script: str = "trouble-brewing"

    # ---- 玩家进出 ----

    def add_player(self, name: str) -> Player:
        player = Player(id=secrets.token_hex(4), name=name.strip()[:20],
                        seat=len(self.players) + 1)
        self.players[player.id] = player
        return player

    def remove_player(self, player_id: str) -> None:
        if player_id not in self.players:
            return
        del self.players[player_id]
        for i, p in enumerate(self.players.values(), start=1):
            p.seat = i

    # ---- 角色分配 ----

    def assign_roles(self) -> list[dict]:
        """按暗流涌动官方配置表随机分配,支持男爵 +2 外来者。"""
        n = len(self.players)
        if n < 5:
            raise ValueError("至少需要 5 名玩家才能分配角色")
        comp = TB_COMPOSITION.get(n)
        if comp is None:
            raise ValueError(f"暗流涌动支持 5~15 人,当前 {n} 人")
        townsfolk, outsider, minion, demon = comp

        by_team = {team: [r for r in TB_ROLES if r["team"] == team]
                   for team in (TOWNSFOLK, OUTSIDER, MINION, DEMON)}

        pool = random.sample(by_team[DEMON], demon)
        minions = random.sample(by_team[MINION], minion)
        pool += minions
        if any(r["id"] == "baron" for r in minions):  # 男爵:多 2 外来者、少 2 镇民
            townsfolk -= 2
            outsider += 2
        pool += random.sample(by_team[OUTSIDER], outsider)
        pool += random.sample(by_team[TOWNSFOLK], townsfolk)
        random.shuffle(pool)

        for player, role in zip(self.players.values(), pool):
            player.role_id = role["id"]
        self.status = "playing"
        return [p.storyteller(self.roles_by_id) for p in self.players.values()]

    # ---- 状态操作 ----

    def toggle_alive(self, player_id: str) -> None:
        if player_id in self.players:
            self.players[player_id].alive = not self.players[player_id].alive

    # ---- 视图 ----

    def player_view(self, player_id: str) -> dict:
        by_seat = sorted(self.players.values(), key=lambda p: p.seat)
        return {
            "status": self.status,
            "me": self.players[player_id].private(self.roles_by_id),
            "players": [p.public() for p in by_seat],
        }

    def storyteller_view(self) -> dict:
        by_seat = sorted(self.players.values(), key=lambda p: p.seat)
        return {
            "status": self.status,
            "script": self.script,
            "players": [p.storyteller(self.roles_by_id) for p in by_seat],
            "roles": TB_ROLES,
        }
