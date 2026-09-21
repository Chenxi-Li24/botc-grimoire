import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect

from app import game as game_module
from app.api import chat, player, websocket
from app.application import runtime
from app.application.realtime import Hub
from app.game import GameManager
from app.infrastructure.identity_store import IdentityStore
from app.main import app


class IdentityAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.save = patch.object(game_module, "SAVE_PATH", Path(self.temp.name) / "game.json")
        self.save.start()
        self.game = GameManager()
        self.hub = Hub(self.game)
        self.store = IdentityStore(Path(self.temp.name) / "accounts.sqlite3")
        self.patches = [
            patch.object(runtime, "game", self.game),
            patch.object(runtime, "hub", self.hub),
            patch.object(runtime, "identity_store", self.store),
            patch.object(player, "game", self.game),
            patch.object(chat, "game", self.game),
            patch.object(websocket, "hub", self.hub),
        ]
        for p in self.patches:
            p.start()
        self.alice = TestClient(app, headers={"Origin": "http://testserver"})
        self.bob = TestClient(app, headers={"Origin": "http://testserver"})
        self.alice_id = self.alice.post("/api/join", json={
            "name": "甲", "room_code": self.game.room_code
        }).json()["player_id"]
        self.bob_id = self.bob.post("/api/join", json={
            "name": "乙", "room_code": self.game.room_code
        }).json()["player_id"]
        self.bob_csrf = self.bob.get("/api/session").json()["csrf_token"]

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.save.stop()
        self.temp.cleanup()

    def test_public_id_cannot_read_or_act_for_another_player(self):
        self.assertEqual(self.bob.get(f"/api/me/{self.alice_id}").status_code, 403)
        self.assertEqual(self.bob.post(
            f"/api/player/{self.alice_id}/vote",
            headers={"X-CSRF-Token": self.bob_csrf},
        ).status_code, 403)
        self.assertEqual(self.bob.post(
            "/api/chat/create", params={"player_id": self.alice_id},
            json={"invitees": []}, headers={"X-CSRF-Token": self.bob_csrf},
        ).status_code, 403)

    def test_missing_csrf_and_cross_origin_cannot_write(self):
        self.assertEqual(self.alice.post(f"/api/player/{self.alice_id}/vote").status_code, 403)
        csrf = self.alice.get("/api/session").json()["csrf_token"]
        self.assertEqual(self.alice.post(
            f"/api/player/{self.alice_id}/vote",
            headers={"X-CSRF-Token": csrf, "Origin": "https://evil.example"},
        ).status_code, 403)

    def test_websocket_ignores_public_id_as_credentials(self):
        with self.assertRaises(WebSocketDisconnect):
            with self.bob.websocket_connect(f"/ws?who={self.alice_id}") as ws:
                ws.receive_json()
        with self.bob.websocket_connect("/ws") as ws:
            view = ws.receive_json()
            self.assertEqual(view["me"]["id"], self.bob_id)
        anonymous = TestClient(app, headers={"Origin": "http://testserver"})
        with self.assertRaises(WebSocketDisconnect):
            with anonymous.websocket_connect("/ws") as ws:
                ws.receive_json()
        with self.assertRaises(WebSocketDisconnect):
            with self.bob.websocket_connect("/ws", headers={"Origin": "https://evil.example"}) as ws:
                ws.receive_json()


if __name__ == "__main__":
    unittest.main()
