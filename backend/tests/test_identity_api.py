import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import game as game_module
from app.api import player as player_api
from app.application import runtime
from app.game import GameManager
from app.infrastructure.identity_store import IdentityStore
from app.main import app


class IdentityApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.save_patch = patch.object(game_module, "SAVE_PATH", Path(self.temp.name) / "game.json")
        self.save_patch.start()
        self.game = GameManager()
        self.store = IdentityStore(Path(self.temp.name) / "accounts.sqlite3")
        self.game_patch = patch.object(runtime, "game", self.game)
        self.player_patch = patch.object(player_api, "game", self.game)
        self.store_patch = patch.object(runtime, "identity_store", self.store, create=True)
        for p in (self.game_patch, self.player_patch, self.store_patch):
            p.start()
        self.client = TestClient(app, headers={"Origin": "http://testserver"})

    def tearDown(self):
        for p in (self.store_patch, self.player_patch, self.game_patch, self.save_patch):
            p.stop()
        self.temp.cleanup()

    def test_guest_session_is_private_and_names_do_not_restore_identity(self):
        room = self.game.room_code
        first = self.client.post("/api/join", json={"name": "甲", "room_code": room})
        self.assertEqual(first.status_code, 200)
        alice = first.json()["player_id"]
        self.assertEqual(self.client.get("/api/session").json()["player_id"], alice)
        other = TestClient(app, headers={"Origin": "http://testserver"})
        self.assertEqual(other.get(f"/api/me/{alice}").status_code, 401)
        second = other.post("/api/join", json={"name": "甲", "room_code": room})
        self.assertNotEqual(second.json()["player_id"], alice)

    def test_account_login_restores_linked_guest_and_rejects_missing_csrf(self):
        room = self.game.room_code
        player_id = self.client.post("/api/join", json={"name": "甲", "room_code": room}).json()["player_id"]
        csrf = self.client.get("/api/session").json()["csrf_token"]
        register = self.client.post(
            "/api/account/register",
            json={"username": "Alice", "password": "test-password-123"},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(register.status_code, 200)
        self.assertTrue(register.json()["recovery_code"])
        self.assertEqual(self.game.players[player_id].account_id, register.json()["account_id"])
        self.assertEqual(self.client.post("/api/account/logout").status_code, 403)
        other = TestClient(app, headers={"Origin": "http://testserver"})
        login = other.post("/api/account/login", json={"username": "alice", "password": "test-password-123"})
        self.assertEqual(login.status_code, 200)
        self.assertEqual(other.get("/api/session").json()["player_id"], player_id)

    def test_cross_origin_join_is_rejected(self):
        bad = TestClient(app, headers={"Origin": "https://evil.example"})
        response = bad.post("/api/join", json={"name": "甲", "room_code": self.game.room_code})
        self.assertEqual(response.status_code, 403)

    def test_account_recovery_and_logout_all(self):
        created = self.client.post(
            "/api/account/register", json={"username": "Alice", "password": "old-password-123"}
        )
        self.assertEqual(created.status_code, 200)
        code = created.json()["recovery_code"]
        second = TestClient(app, headers={"Origin": "http://testserver"})
        self.assertEqual(second.post(
            "/api/account/login", json={"username": "Alice", "password": "old-password-123"}
        ).status_code, 200)
        csrf = self.client.get("/api/session").json()["csrf_token"]
        self.assertEqual(self.client.post(
            "/api/account/logout-all", headers={"X-CSRF-Token": csrf}
        ).status_code, 200)
        self.assertEqual(second.get("/api/session").status_code, 401)
        reset = self.client.post("/api/account/reset-password", json={
            "username": "Alice", "recovery_code": code, "new_password": "new-password-123"
        })
        self.assertEqual(reset.status_code, 200)
        self.assertTrue(reset.json()["recovery_code"])
        self.assertEqual(self.client.post("/api/account/reset-password", json={
            "username": "Alice", "recovery_code": code, "new_password": "newer-password-123"
        }, headers={"X-CSRF-Token": self.client.get("/api/session").json()["csrf_token"]}).status_code, 401)
        fresh = TestClient(app, headers={"Origin": "http://testserver"})
        self.assertEqual(fresh.post(
            "/api/account/login", json={"username": "Alice", "password": "old-password-123"}
        ).status_code, 401)

    def test_session_expiry_is_not_a_guest_credential(self):
        token, _ = self.store.issue_session(player_id="not-a-player", game_id=self.game.game_id, now=1, ttl=1)
        self.client.cookies.set("botc_session", token)
        self.assertEqual(self.client.get("/api/session").status_code, 401)

    def test_removed_guest_session_cannot_be_used(self):
        player_id = self.client.post("/api/join", json={
            "name": "甲", "room_code": self.game.room_code
        }).json()["player_id"]
        self.game.remove_player(player_id)
        self.assertEqual(self.client.get("/api/session").status_code, 401)


if __name__ == "__main__":
    unittest.main()
