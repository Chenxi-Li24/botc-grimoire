import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import game as game_module
from app.api import player as player_api
from app.application import runtime
from app.application.realtime import Hub
from app.application.history import project_own_history
from app.game import GameManager
from app.infrastructure.identity_store import IdentityStore
from app.main import app


class PlayerInferenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.save = patch.object(game_module, "SAVE_PATH", Path(self.temp.name) / "game.json")
        self.save.start()
        self.game = GameManager()
        self.store = IdentityStore(Path(self.temp.name) / "accounts.sqlite3")
        self.patches = [
            patch.object(runtime, "game", self.game),
            patch.object(runtime, "hub", Hub(self.game)),
            patch.object(runtime, "identity_store", self.store),
            patch.object(player_api, "game", self.game),
        ]
        for item in self.patches:
            item.start()
        self.alice = TestClient(app, headers={"Origin": "http://testserver"})
        self.bob = TestClient(app, headers={"Origin": "http://testserver"})
        self.alice_id = self.alice.post("/api/join", json={"name": "甲", "room_code": self.game.room_code}).json()["player_id"]
        self.bob_id = self.bob.post("/api/join", json={"name": "乙", "room_code": self.game.room_code}).json()["player_id"]
        self.alice_csrf = self.alice.get("/api/session").json()["csrf_token"]
        self.bob_csrf = self.bob.get("/api/session").json()["csrf_token"]
        self.game.status = "playing"
        self.game.save()

    def tearDown(self):
        for item in reversed(self.patches):
            item.stop()
        self.save.stop()
        self.temp.cleanup()

    def _note(self, client, player_id, csrf, **overrides):
        body = {"target": 3, "category": "role", "operation": "set",
                "client_id": "test-1", "data": {"role": "chef", "confidence": "medium", "reason": "第一天发言"}}
        body.update(overrides)
        return client.post(f"/api/player/{player_id}/inference", json=body, headers={"X-CSRF-Token": csrf})

    def test_private_realtime_projection_and_read_only_storyteller(self):
        response = self._note(self.alice, self.alice_id, self.alice_csrf)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["inference"]["events"][0]["target"], 3)
        self.assertEqual(self.bob.get(f"/api/me/{self.bob_id}").json()["inference"]["events"], [])
        self.assertEqual(self.alice.get(f"/api/me/{self.alice_id}").json()["inference"]["events"][0]["data"]["role"], "chef")
        self.assertEqual(self.bob.get(f"/api/me/{self.alice_id}").status_code, 403)
        storyteller = self.game.storyteller_view()["player_inferences"]
        self.assertEqual(storyteller[0]["player_id"], self.alice_id)
        self.assertEqual(storyteller[0]["events"][0]["data"]["role"], "chef")
        self.assertEqual(self.game.seat_state(3).character_id, None)

    def test_idempotent_history_and_restart(self):
        self.assertEqual(self._note(self.alice, self.alice_id, self.alice_csrf).status_code, 200)
        self.assertEqual(self._note(self.alice, self.alice_id, self.alice_csrf).status_code, 200)
        self.assertEqual(len(self.game.inference_events), 1)
        end = self._note(self.alice, self.alice_id, self.alice_csrf, client_id="test-2", operation="clear", data={})
        self.assertEqual(end.status_code, 200)
        self.assertEqual(len(self.game.inference_events), 2)
        restored = GameManager()
        self.assertEqual(len(restored.inference_events), 2)
        self.assertEqual(restored.inference_view(self.alice_id)["current"], [])

    def test_rejects_other_author_invalid_role_and_missing_csrf(self):
        self.assertEqual(self._note(self.bob, self.alice_id, self.bob_csrf).status_code, 403)
        self.assertEqual(self._note(self.alice, self.alice_id, "").status_code, 403)
        self.assertEqual(self._note(self.alice, self.alice_id, self.alice_csrf, data={"role": "not-in-script"}).status_code, 400)
        self.assertEqual(self._note(self.alice, self.alice_id, self.alice_csrf, target=999).status_code, 400)
        self.assertEqual(self.game.inference_events, [])

    def test_account_archive_carries_only_owners_replay(self):
        self._note(self.alice, self.alice_id, self.alice_csrf)
        self.game.winner = "good"
        own = project_own_history(self.game, self.alice_id)
        other = project_own_history(self.game, self.bob_id)
        self.assertEqual(len(own["guesses"]), 1)
        self.assertEqual(other["guesses"], [])
        self.assertEqual(own["guesses"][0]["verdict"], "incorrect")

    def test_only_final_live_role_guess_is_compared_and_finished_game_is_read_only(self):
        self._note(self.alice, self.alice_id, self.alice_csrf)
        self._note(self.alice, self.alice_id, self.alice_csrf, client_id="test-2", data={"role": "imp"})
        self.game.winner = "evil"
        verdicts = [item["verdict"] for item in self.game.inference_replay(self.alice_id)]
        self.assertEqual(verdicts, ["unverified", "incorrect"])
        self.assertEqual(self._note(self.alice, self.alice_id, self.alice_csrf, client_id="test-3").status_code, 400)


if __name__ == "__main__":
    unittest.main()
