import unittest
from unittest.mock import patch

from app import main


class _GameWithoutPlayers:
    players = {}

    @staticmethod
    def storyteller_view():
        return {"status": "lobby"}


class _Socket:
    def __init__(self):
        self.closed = []

    async def close(self, code: int, reason: str):
        self.closed.append((code, reason))


class PlayerWebSocketSessionTest(unittest.IsolatedAsyncioTestCase):
    async def test_push_closes_removed_player_sessions(self):
        hub = main.Hub()
        socket = _Socket()
        hub.players["removed"] = {socket}

        with patch.object(main, "game", _GameWithoutPlayers()):
            await hub.push_all()

        self.assertEqual(socket.closed, [(4001, "未知身份")])
        self.assertNotIn("removed", hub.players)


if __name__ == "__main__":
    unittest.main()
