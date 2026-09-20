import unittest

from night_helpers import make_game


class NightEffectTest(unittest.TestCase):
    def test_effect_lifetimes_suspend_resume_and_end(self):
        game, _ = make_game(
            {1: "poisoner", 2: "widow", 3: "chef"},
            script="wafu-leiming", night=2,
        )
        poison = game.night.apply_poisoner(source=1, target=3)
        widow = game.night.apply_widow(source=2, target=3)
        game.night.set_source_ability(1, active=False, permanent=False)
        game.night.set_source_ability(2, active=False, permanent=False)
        self.assertEqual(
            [game.effects.get(x).state for x in (poison.id, widow.id)],
            ["suspended", "suspended"],
        )
        game.night.set_source_ability(1, active=True, permanent=False)
        game.night.set_source_ability(2, active=True, permanent=False)
        self.assertEqual(
            [game.effects.get(x).state for x in (poison.id, widow.id)],
            ["active", "active"],
        )
        game.effects.advance("dusk")
        self.assertEqual(game.effects.get(poison.id).state, "ended")
        self.assertEqual(game.effects.get(widow.id).state, "active")

    def test_cerenovus_next_choice_ends_previous_madness(self):
        game, _ = make_game(
            {1: "cerenovus", 2: "chef", 3: "empath"},
            script="wafu-leiming", night=2,
        )
        first = game.night.apply_cerenovus(1, 2, "chef")
        second = game.night.apply_cerenovus(1, 3, "dreamer")
        self.assertEqual(game.effects.get(first.id).state, "ended")
        self.assertEqual(game.effects.get(second.id).state, "active")
        self.assertIsNone(game.seat_state(2).mad_about)
        self.assertEqual(game.seat_state(3).mad_about, "dreamer")


if __name__ == "__main__":
    unittest.main()
