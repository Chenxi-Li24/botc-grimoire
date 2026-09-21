import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch

from app.scripts import SCRIPTS, SCRIPT_PACKS
from app.night_order import NIGHT_ORDER
from app import game as game_module
from app.game import GameManager


class CommunityCatalogTests(unittest.TestCase):
    def test_source_backed_scripts_have_unique_roles_and_night_steps(self):
        for script_id, minimum in (
            ("qieqiesiyu", 11),
            ("yebankuanghuan", 23),
            ("sunaomituan", 11),
            ("huyanluanyu", 25),
            ("kaixinkuailehou", 22),
        ):
            with self.subTest(script_id=script_id):
                pack = SCRIPT_PACKS[script_id]
                self.assertGreaterEqual(len(pack.characters), minimum)
                ids = {role.id for role in pack.characters}
                self.assertEqual(len(ids), len(pack.characters))
                self.assertEqual(ids, {r["id"] for r in SCRIPTS[script_id]["roles"]})
                for kind in ("first", "other"):
                    steps = NIGHT_ORDER[script_id][kind]
                    self.assertEqual(steps[0]["key"], "dusk")
                    self.assertEqual(steps[-1]["key"], "dawn")
                    self.assertTrue(all(step["key"] in ids | {"dusk", "dawn", "minioninfo", "demoninfo"} for step in steps))

    def test_lunatic_precedes_demon_action_in_each_night(self):
        for script_id in ("qieqiesiyu", "sunaomituan", "huyanluanyu"):
            with self.subTest(script_id=script_id):
                roles = {r["id"]: r for r in SCRIPTS[script_id]["roles"]}
                for kind in ("first", "other"):
                    keys = [step["key"] for step in NIGHT_ORDER[script_id][kind]]
                    if "lunatic" in keys:
                        for key in keys:
                            if key in roles and roles[key]["team"] == "demon":
                                self.assertLess(keys.index("lunatic"), keys.index(key))

    def test_small_script_rejects_oversized_table_and_inference_is_not_carried_into_new_game(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(game_module, "SAVE_PATH", Path(directory) / "game.json"):
            game = GameManager()
            game.configure("qieqiesiyu", 6, balloonist_version="new",
                           balloonist_outsider_delta=1)
            with self.assertRaises(ValueError):
                game.configure("qieqiesiyu", 7, balloonist_version="new",
                               balloonist_outsider_delta=1)
            game.assign_roles()
            self.assertEqual(game.status, "playing")
            self.assertTrue(game.night_steps)
            player = game.add_player("甲")
            game.record_inference(player.id, 1, "role", "set", {"role": "savant"}, "note-1")
            game.configure("trouble-brewing", 6)
            self.assertEqual(game.inference_events, [])

    def test_poppy_grower_never_auto_reveals_evil_team(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(game_module, "SAVE_PATH", Path(directory) / "game.json"):
            game = GameManager()
            game.configure("yebankuanghuan", 7, balloonist_version="new",
                           balloonist_outsider_delta=1)
            minion = game.add_player("爪牙")
            demon = game.add_player("恶魔")
            game.sit(minion.id, 1)
            game.sit(demon.id, 2)
            game.seat_roles[1] = "poisoner"
            game.seat_roles[2] = "vigormortis"
            game.seat_roles[3] = "poppygrower"
            game.status = "playing"
            game.phase = "day"
            self.assertNotIn("demon_seats", game.player_view(minion.id))
            self.assertNotIn("minion_seats", game.player_view(demon.id))


if __name__ == "__main__":
    unittest.main()
