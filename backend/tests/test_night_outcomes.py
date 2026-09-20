import unittest

from night_helpers import make_game


class NightOutcomeTest(unittest.TestCase):
    def test_secret_death_rebuilds_unexecuted_suffix(self):
        game, _ = make_game({1: "imp", 2: "ravenkeeper", 3: "undertaker"}, night=2)
        outcome = game.night.resolve_test_attack(
            source=1, target=2, resolution="secret_death",
        )
        self.assertTrue(game.seat_state(2).public_alive)
        self.assertEqual(
            game.night.queue.step_for(3, "undertaker").status, "upcoming",
        )
        self.assertEqual(
            game.night.queue.step_for(2, "ravenkeeper", trigger="death").depends_on,
            [outcome.event_id],
        )

    def test_dawn_publishes_only_confirmed_secret_deaths(self):
        game, _ = make_game({1: "imp", 2: "chef", 3: "empath"}, night=2)
        game.night.resolve_test_attack(1, 2, "secret_death")
        game.night.publish_dawn()
        self.assertFalse(game.seat_state(2).public_alive)
        self.assertTrue(game.seat_state(3).public_alive)

    def test_lunatic_choice_is_exposed_to_real_demon_without_killing(self):
        game, _ = make_game({1: "lunatic", 2: "imp", 3: "chef"}, script="wafu-leiming", night=2)
        game.night.resolve_test_attack(1, 3)
        context = game.night.projection()["context"]["lunatic_choices"]
        self.assertEqual(context[0]["lunatic_seat"], 1)
        self.assertEqual(context[0]["target_seats"], [3])
        self.assertTrue(game.seat_state(3).alive)


if __name__ == "__main__":
    unittest.main()
