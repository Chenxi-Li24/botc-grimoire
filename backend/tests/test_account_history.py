import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from app import game as game_module
from app.api import storyteller
from app.application import runtime
from app.application.history import archive_game
from app.game import GameManager
from app.infrastructure.identity_store import IdentityStore
from app.main import app


class AccountHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.save = patch.object(game_module, "SAVE_PATH", Path(self.temp.name) / "game.json")
        self.save.start()
        self.game = GameManager()
        self.store = IdentityStore(Path(self.temp.name) / "accounts.sqlite3")
        self.patches = [
            patch.object(runtime, "game", self.game),
            patch.object(runtime, "identity_store", self.store),
            patch.object(storyteller, "game", self.game),
        ]
        for p in self.patches:
            p.start()

    def tearDown(self):
        for p in reversed(self.patches):
            p.stop()
        self.save.stop()
        self.temp.cleanup()

    def test_archive_is_idempotent_private_and_persistent(self):
        account_id, _ = self.store.create_account("Alice", "test-password-123")
        other_id, _ = self.store.create_account("Bob", "test-password-123")
        player = self.game.add_player("甲")
        player.account_id = account_id
        self.game.sit(player.id, 1)
        self.game.seat_state(1).character_id = "chef"
        self.game.status = "playing"
        self.game.winner = "good"
        self.game.chats = [{"messages": [{"text": "private chat secret"}]}]
        old_game_id = self.game.game_id
        archive_game(self.game, self.store)
        archive_game(self.game, self.store)
        records = IdentityStore(self.store.path).list_archives(account_id)
        self.assertEqual(len(records), 1)
        self.assertEqual(records[0]["game_id"], old_game_id)
        self.assertEqual(records[0]["roles"], [{"id": "chef", "name": "厨师"}])
        self.assertEqual(records[0]["guesses"], [])
        self.assertNotIn("private chat secret", str(records))
        self.assertEqual(self.store.list_archives(other_id), [])

    def test_account_traveler_role_is_archived(self):
        account_id, _ = self.store.create_account("Traveler", "test-password-123")
        player = self.game.add_player("旅人")
        player.account_id = account_id
        self.game.status = "playing"
        traveler = self.game.add_traveler(player.id)
        self.game.assign_traveler(traveler["id"], "apprentice", "good")
        archive_game(self.game, self.store)
        record = self.store.list_archives(account_id)[0]
        self.assertIsNone(record["seat"])
        self.assertEqual(record["roles"], [{"id": "apprentice", "name": "学徒"}])

    def test_reset_does_not_clear_game_when_archive_fails(self):
        account_id, _ = self.store.create_account("Alice", "test-password-123")
        player = self.game.add_player("甲")
        player.account_id = account_id
        self.game.status = "playing"
        old_game_id = self.game.game_id
        client = TestClient(app, headers={
            "Origin": "http://testserver", "X-Storyteller-Password": "grimoire"
        }, raise_server_exceptions=False)
        with patch.object(self.store, "upsert_archive", side_effect=OSError("disk full")):
            response = client.post("/api/reset")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(self.game.game_id, old_game_id)
        self.assertIn(player.id, self.game.players)
        self.assertEqual(client.post("/api/reset").status_code, 200)
        self.assertNotEqual(self.game.game_id, old_game_id)
        self.assertEqual(len(self.store.list_archives(account_id)), 1)
        new_game_id = self.game.game_id
        self.assertEqual(GameManager().game_id, new_game_id)
        self.assertEqual(client.post("/api/reset").status_code, 200)
        self.assertEqual(len(self.store.list_archives(account_id)), 1)

    def test_configuring_an_active_game_archives_and_starts_new_game(self):
        account_id, _ = self.store.create_account("Alice", "test-password-123")
        player = self.game.add_player("甲")
        player.account_id = account_id
        self.game.status = "playing"
        old_game_id = self.game.game_id
        client = TestClient(app, headers={
            "Origin": "http://testserver", "X-Storyteller-Password": "grimoire"
        })
        response = client.post("/api/config", json={"script": self.game.script_id, "player_count": 7})
        self.assertEqual(response.status_code, 200)
        self.assertNotEqual(self.game.game_id, old_game_id)
        self.assertEqual(len(self.store.list_archives(account_id)), 1)

    def test_lobby_config_does_not_archive_or_replace_game_id(self):
        account_id, _ = self.store.create_account("Alice", "test-password-123")
        player = self.game.add_player("甲")
        player.account_id = account_id
        old_game_id = self.game.game_id
        client = TestClient(app, headers={
            "Origin": "http://testserver", "X-Storyteller-Password": "grimoire"
        })
        self.assertEqual(client.post("/api/config", json={
            "script": self.game.script_id, "player_count": 7
        }).status_code, 200)
        self.assertEqual(self.game.game_id, old_game_id)
        self.assertEqual(self.store.list_archives(account_id), [])

    def test_history_endpoint_is_account_private(self):
        alice, _ = self.store.create_account("Alice", "test-password-123")
        bob, _ = self.store.create_account("Bob", "test-password-123")
        self.store.upsert_archive("g1", alice, {"game_id": "g1", "roles": [{"id": "chef", "name": "厨师"}]})
        alice_token, _ = self.store.issue_session(account_id=alice)
        bob_token, _ = self.store.issue_session(account_id=bob)
        guest_token, _ = self.store.issue_session(player_id="p1", game_id=self.game.game_id)
        client = TestClient(app, headers={"Origin": "http://testserver"})
        client.cookies.set("botc_session", alice_token)
        self.assertEqual(len(client.get("/api/account/history").json()), 1)
        client.cookies.set("botc_session", bob_token)
        self.assertEqual(client.get("/api/account/history").json(), [])
        client.cookies.set("botc_session", guest_token)
        self.assertEqual(client.get("/api/account/history").status_code, 403)


if __name__ == "__main__":
    unittest.main()
