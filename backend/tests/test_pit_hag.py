import unittest

from app.night.journal import UndoConflict
from night_helpers import make_game


class PitHagTest(unittest.TestCase):
    def test_creating_demon_disables_its_kill_and_enables_arbitrary_death(self):
        game, _ = make_game(
            {1: "pithag", 2: "dreamer", 3: "clockmaker"},
            script="sects-and-violets", night=2,
        )
        event = game.night.confirm_pit_hag(1, 2, "fang-gu")
        self.assertEqual(game.seat_state(2).character_id, "fang-gu")
        self.assertEqual(
            game.seat_state(2).ability_state["fang-gu"]["created_demon_no_kill_night"],
            2,
        )
        self.assertEqual(
            game.seat_state(1).ability_state["pithag"]["arbitrary_death_source"]["event_id"],
            event.id,
        )
        demon_step = game.night.queue.step_for(2, "fang-gu")
        self.assertEqual(demon_step.skip_reason, "created_demon_no_kill_this_night")

    def test_creating_demon_suppresses_legacy_phone_kill_at_dawn(self):
        game, _ = make_game(
            {1: "pithag", 2: "dreamer", 3: "imp", 4: "chef"},
            script="wafu-leiming", night=2,
        )
        game.night.confirm_pit_hag(1, 2, "fang-gu")
        game.night_kills = {"2": {"seat": 4, "by": 3, "role": "imp"}}

        game._apply_night_kills()

        self.assertTrue(game.seat_state(4).alive)

    def test_duplicate_role_is_a_silent_failure(self):
        game, _ = make_game(
            {1: "pithag", 2: "dreamer", 3: "clockmaker"},
            script="sects-and-violets", night=2,
        )
        event = game.night.confirm_pit_hag(1, 2, "clockmaker")
        self.assertEqual(event.kind, "pit_hag_silent_failure")
        self.assertEqual(game.seat_state(2).character_id, "dreamer")

    def test_pit_hag_dependency_undo_is_atomic(self):
        game, _ = make_game(
            {1: "pithag", 2: "chef", 3: "imp"},
            script="mantanghong", night=2,
        )
        event = game.night.confirm_pit_hag(1, 2, "noble")
        delivery = game.night.deliver_test_information(2, depends_on=[event.id])
        preview = game.night.undo(event.id, confirm=False)
        self.assertLessEqual({event.id, delivery.event_id}, set(preview.event_ids))
        self.assertEqual(len(preview.event_ids), 3)
        before = game.save_payload()
        game.night.inject_inverse_failure(delivery.event_id)
        with self.assertRaises(UndoConflict):
            game.night.undo(event.id, confirm=True)
        self.assertEqual(game.save_payload(), before)


if __name__ == "__main__":
    unittest.main()
