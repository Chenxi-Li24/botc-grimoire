import unittest

from app.main import app
from night_helpers import make_game


class NightApiContractTest(unittest.TestCase):
    def test_all_modular_night_routes_are_exposed(self):
        paths = set(app.openapi()["paths"])
        expected = {
            f"/api/night/{name}"
            for name in ("step", "select", "outcome", "information", "effect", "pit-hag", "undo")
        }
        self.assertLessEqual(expected, paths)

    def test_player_projection_does_not_expose_storyteller_truth(self):
        game, player_id = make_game(
            {1: "chef", 2: "imp", 3: "poisoner"}, claim_seat=1,
        )
        game.night.prepare_information(1)
        view = game.player_view(player_id)
        serialized = repr(view)
        self.assertNotIn("true_result", serialized)
        self.assertNotIn("effect_snapshot", serialized)
        self.assertNotIn("undo_previews", serialized)


if __name__ == "__main__":
    unittest.main()
