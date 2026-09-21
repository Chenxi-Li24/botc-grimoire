"""Role-scoped WebSocket delivery."""

from fastapi import WebSocket


class Hub:
    """WebSocket 连接池:按「说书人 / 玩家id」分组,推送各自的视图。"""

    def __init__(self, game=None) -> None:
        self._game = game
        self.storytellers: set[WebSocket] = set()
        self.players: dict[str, set[WebSocket]] = {}

    @property
    def game(self):
        if self._game is None:
            from .. import main
            return main.game
        return self._game

    async def connect(self, who: str, ws: WebSocket) -> None:
        await ws.accept()
        if who == "storyteller":
            self.storytellers.add(ws)
            await ws.send_json(self.game.storyteller_view())
        elif who in self.game.players:
            self.players.setdefault(who, set()).add(ws)
            await ws.send_json(self.game.player_view(who))
            if self.game.mark_private_deliveries_delivered(who):
                self.game.save()
        else:
            await ws.close(code=4001, reason="未知身份")
            return

    def disconnect(self, who: str, ws: WebSocket) -> None:
        if who == "storyteller":
            self.storytellers.discard(ws)
        else:
            self.players.get(who, set()).discard(ws)

    async def push_all(self) -> None:
        """任何状态变化后向所有在线设备推送各自的视图。"""
        view = self.game.storyteller_view()
        for ws in list(self.storytellers):
            await self._send(ws, view)
        for player_id, sockets in list(self.players.items()):
            if player_id not in self.game.players:
                for ws in list(sockets):
                    try:
                        await ws.close(code=4001, reason="未知身份")
                    except Exception:
                        pass
                self.players.pop(player_id, None)
                continue
            view = self.game.player_view(player_id)
            delivered = False
            for ws in list(sockets):
                delivered = await self._send(ws, view) or delivered
            if delivered and self.game.mark_private_deliveries_delivered(player_id):
                self.game.save()

    @staticmethod
    async def _send(ws: WebSocket, view: dict) -> bool:
        try:
            await ws.send_json(view)
            return True
        except Exception:
            return False  # 断开的连接由 disconnect() 清理
