import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import game as game_module
from app.api import player as player_api
from app.application import runtime
from app.game import GameManager
from app.infrastructure.identity_store import IdentityStore
from app.infrastructure.identity_store import LoginRateLimited
from app.main import app


class RecoveryStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = IdentityStore(Path(self.temp.name) / "accounts.sqlite3")

    def tearDown(self):
        self.temp.cleanup()

    def test_single_use_expiry_and_wrong_game(self):
        code = self.store.issue_participant_recovery("game-1", "player-1", now=1000)
        self.assertIsNone(self.store.redeem_participant_recovery("game-2", code, now=1001))
        self.assertEqual(self.store.redeem_participant_recovery("game-1", code, now=1001), "player-1")
        self.assertIsNone(self.store.redeem_participant_recovery("game-1", code, now=1002))
        expired = self.store.issue_participant_recovery("game-1", "player-1", now=1000)
        self.assertIsNone(self.store.redeem_participant_recovery("game-1", expired, now=1601))

    def test_concurrent_redeem_only_one_wins(self):
        code = self.store.issue_participant_recovery("game-1", "player-1", now=1000)
        barrier = threading.Barrier(2)
        results = []

        def redeem():
            barrier.wait()
            results.append(self.store.redeem_participant_recovery("game-1", code, now=1001))

        threads = [threading.Thread(target=redeem) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        self.assertEqual(sorted(str(result) for result in results), ["None", "player-1"])

    def test_repeated_invalid_recovery_attempts_are_limited(self):
        for _ in range(5):
            self.store.record_recovery_failure("client-1", now=1000)
        with self.assertRaises(LoginRateLimited):
            self.store.check_recovery_limit("client-1", now=1001)
        self.store.check_recovery_limit("client-1", now=1901)


class RecoveryApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.save = patch.object(game_module, "SAVE_PATH", Path(self.temp.name) / "game.json")
        self.save.start()
        self.game = GameManager()
        self.store = IdentityStore(Path(self.temp.name) / "accounts.sqlite3")
        self.patches = [
            patch.object(runtime, "game", self.game),
            patch.object(runtime, "identity_store", self.store),
            patch.object(player_api, "game", self.game),
        ]
        for p in self.patches:
            p.start()
        self.client = TestClient(app, headers={"Origin": "http://testserver"})
        self.player_id = self.client.post("/api/join", json={
            "name": "甲", "room_code": self.game.room_code
        }).json()["player_id"]

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.save.stop()
        self.temp.cleanup()

    def test_storyteller_code_recovers_same_player_without_account(self):
        issued = self.client.post(
            f"/api/st/players/{self.player_id}/recovery-code",
            headers={"X-Storyteller-Password": "grimoire"},
        )
        self.assertEqual(issued.status_code, 200)
        code = issued.json()["code"]
        new_device = TestClient(app, headers={"Origin": "http://testserver"})
        recovered = new_device.post("/api/recover-participant", json={
            "room_code": self.game.room_code, "code": code
        })
        self.assertEqual(recovered.status_code, 200)
        self.assertEqual(new_device.get("/api/session").json()["player_id"], self.player_id)
        self.assertIsNone(new_device.get("/api/session").json()["account"])
        self.assertEqual(new_device.post("/api/recover-participant", json={
            "room_code": self.game.room_code, "code": code
        }, headers={"X-CSRF-Token": new_device.get("/api/session").json()["csrf_token"]}).status_code, 401)

    def test_guest_sessions_can_be_revoked_without_touching_accounts(self):
        result = self.client.post(
            f"/api/st/players/{self.player_id}/revoke-guest-sessions",
            headers={"X-Storyteller-Password": "grimoire"},
        )
        self.assertEqual(result.status_code, 200)
        self.assertEqual(self.client.get("/api/session").status_code, 401)


if __name__ == "__main__":
    unittest.main()
