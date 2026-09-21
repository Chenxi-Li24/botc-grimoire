import unittest

from app.application.projections import ProjectionMixin
from app.game import GameManager
from night_helpers import make_game


class ProjectionBoundaryTest(unittest.TestCase):
    def test_public_game_methods_are_provided_by_projection_module(self):
        self.assertTrue(issubclass(GameManager, ProjectionMixin))
        self.assertNotIn("player_view", GameManager.__dict__)
        self.assertNotIn("storyteller_view", GameManager.__dict__)

    def test_player_view_hides_unclaimed_private_identity(self):
        game, player_id = make_game({1: "chef", 2: "imp", 3: "poisoner"}, claim_seat=1)
        player = game.player_view(player_id)
        storyteller = game.storyteller_view()
        self.assertNotIn("assigned_role", player["seats"][1])
        self.assertEqual(storyteller["seats"][1]["assigned_role"]["id"], "imp")


if __name__ == "__main__":
    unittest.main()
