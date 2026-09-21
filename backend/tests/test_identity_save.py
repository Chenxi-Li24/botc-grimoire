"""Per-game identity survives saves without becoming a public credential."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from app import game as game_module
from app.game import GameManager
from app.roles import SCRIPT_PACKS
from app.save_codec import decode_save


class IdentitySaveTest(unittest.TestCase):
    def test_game_and_account_link_survive_restart_without_public_account_id(self):
        with TemporaryDirectory() as directory, patch.object(
            game_module, "SAVE_PATH", Path(directory) / "game.json"
        ):
            game = GameManager()
            game_id = game.game_id
            player = game.add_player("甲")
            player.account_id = "account-1"
            game.save()

            restored = GameManager()
            self.assertEqual(restored.game_id, game_id)
            self.assertEqual(restored.players[player.id].account_id, "account-1")
            self.assertNotIn("account_id", restored.players[player.id].public())

    def test_old_v2_account_defaults_to_guest(self):
        old = {
            "schema_version": 2,
            "player_count": 1,
            "players": {"p1": {"id": "p1", "name": "甲", "seat": None, "wish": None}},
            "seats": {"1": {"seat": 1}},
        }
        state = decode_save(old, SCRIPT_PACKS["trouble-brewing"])
        self.assertIsNone(state.players["p1"].account_id)

    def test_reset_creates_new_game_id(self):
        with TemporaryDirectory() as directory, patch.object(
            game_module, "SAVE_PATH", Path(directory) / "game.json"
        ):
            game = GameManager()
            original = game.game_id
            game.reset()
            self.assertNotEqual(game.game_id, original)


if __name__ == "__main__":
    unittest.main()
