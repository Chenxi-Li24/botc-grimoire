import unittest

from app.night.service import NavigationConflict
from night_helpers import make_game


class NightQueueTest(unittest.TestCase):
    def test_only_in_play_roles_are_queued_and_lunatic_precedes_demon(self):
        game, _ = make_game(
            {1: "lunatic", 2: "imp", 3: "chef"},
            script="wafu-leiming", night=2,
        )
        acting = [step for step in game.night.queue.steps if step.actor_seat]
        identities = [(step.actor_seat, step.character_id) for step in acting]
        self.assertIn((1, "lunatic"), identities)
        self.assertIn((2, "imp"), identities)
        self.assertLess(identities.index((1, "lunatic")), identities.index((2, "imp")))
        self.assertNotIn("washerwoman", [step.character_id for step in acting])

    def test_forced_continuation_requires_the_matching_second_confirmation(self):
        game, _ = make_game({1: "imp", 2: "chef"}, night=2)
        step = game.night.queue.step_for(1, "imp")
        game.night.navigate(step_id=step.id)
        blocked = game.night.navigate(direction="next")
        self.assertTrue(blocked.blocked)
        self.assertEqual(blocked.omissions, ["targets"])
        with self.assertRaises(NavigationConflict):
            game.night.navigate(direction="next", force=True, force_token="wrong")
        result = game.night.navigate(
            direction="next", force=True, force_token=blocked.force_token,
        )
        self.assertIsNotNone(result.forced_event_id)
        self.assertEqual(step.skip_reason, "forced")

    def test_first_night_lunatic_can_acknowledge_without_selecting_a_target(self):
        game, _ = make_game(
            {1: "lunatic", 2: "imp", 3: "chef"},
            script="wafu-leiming", night=1,
        )
        step = game.night.queue.step_for(1, "lunatic")
        game.night.navigate(step_id=step.id)

        game.night.record_selection(step.id, [], acknowledged=True)
        result = game.night.navigate(direction="next")

        self.assertFalse(result.blocked)
        self.assertTrue(step.values["acknowledged"])

    def test_unclaimed_seat_survives_player_removal(self):
        game, player_id = make_game({1: "washerwoman", 2: "imp"}, claim_seat=1)
        game.remove_player(player_id)
        self.assertEqual(game.seat_state(1).character_id, "washerwoman")
        self.assertIsNone(game.seat_state(1).claimed_by)


if __name__ == "__main__":
    unittest.main()
