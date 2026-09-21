import unittest

from app.game import Player
from app.night.information import InformationDelivery, InformationDraft
from night_helpers import make_game


class NightInformationTest(unittest.TestCase):
    def test_deterministic_information_is_sent_automatically(self):
        game, _ = make_game({1: "chef", 2: "imp", 3: "poisoner"})
        result = game.night.prepare_information(1)
        self.assertIsInstance(result, InformationDelivery)
        self.assertTrue(result.automatic)
        self.assertEqual(result.claims[0].truthful, True)

    def test_chef_does_not_create_multiple_messages_for_one_step(self):
        game, _ = make_game({1: "chef", 2: "imp", 3: "poisoner"})
        step = game.night.queue.step_for(1, "chef")
        selection = game.night.record_selection(step.id, [])
        first = game.night.prepare_information(1, source_event=selection.id)
        repeated_selection = game.night.record_selection(step.id, [])
        second = game.night.prepare_information(1, source_event=repeated_selection.id)
        self.assertEqual(first.id, second.id)
        self.assertIsInstance(first.delivered_result, int)
        self.assertEqual(len(game.information_deliveries), 1)
        self.assertEqual(len(game.information_notices), 1)

    def test_chef_delivery_cannot_be_a_list_of_candidate_numbers(self):
        game, _ = make_game({1: "chef", 2: "poisoner", 3: "imp"})
        game.night.apply_poisoner(2, 1)
        draft = game.night.prepare_information(1)
        with self.assertRaisesRegex(ValueError, "single integer"):
            game.night.deliver_information(draft.id, [0, 1], claims=[
                {"label": "result", "value": [0, 1], "truthful": False},
            ])
        self.assertEqual(len(game.information_deliveries), 0)

    def test_poisoned_information_requires_explicit_truth_flags(self):
        game, _ = make_game({1: "chef", 2: "poisoner", 3: "imp"})
        game.night.apply_poisoner(2, 1)
        draft = game.night.prepare_information(1)
        self.assertIsInstance(draft, InformationDraft)
        self.assertIn("poisoned", draft.reason)
        with self.assertRaisesRegex(ValueError, "explicit truth flags"):
            game.night.deliver_information(draft.id, draft.true_result)
        delivery = game.night.deliver_information(draft.id, draft.true_result, claims=[{
            "label": "result", "value": draft.true_result, "truthful": True,
        }])
        self.assertTrue(delivery.claims[0].truthful)
        self.assertIn(game.night.state.effect_records[next(iter(game.night.state.effect_records))].id,
                      delivery.effect_snapshot)

    def test_send_time_poison_status_is_recorded_even_if_draft_was_clean(self):
        # A discretionary draft exercises the prepare/send interval.
        game, _ = make_game({1: "dreamer", 2: "poisoner", 3: "fang-gu"},
                            script="sects-and-violets")
        draft = game.night.prepare_information(1, [3])
        poison = game.night.apply_poisoner(2, 1)
        result = draft.legal_results[0]
        with self.assertRaisesRegex(ValueError, "explicit truth flags"):
            game.night.deliver_information(draft.id, result)
        sent = game.night.deliver_information(draft.id, result, claims=[
            {"label": "result", "value": result, "truthful": True},
        ])
        self.assertIn(poison.id, sent.effect_snapshot)
        self.assertIn("poisoned", sent.reason)

    def test_dreamer_records_which_of_two_roles_is_true(self):
        game, _ = make_game(
            {1: "dreamer", 2: "fang-gu", 3: "clockmaker"},
            script="sects-and-violets",
        )
        draft = game.night.prepare_information(1, [2])
        self.assertIsInstance(draft, InformationDraft)
        delivered = {"good_character": "clockmaker", "evil_character": "fang-gu"}
        delivery = game.night.deliver_information(draft.id, delivered)
        truth = {claim.label: claim.truthful for claim in delivery.claims}
        self.assertEqual(truth, {"good_character": False, "evil_character": True})

    def test_delivery_keeps_its_original_night_for_player_history(self):
        game, player_id = make_game(
            {1: "dreamer", 2: "fang-gu", 3: "clockmaker"},
            script="sects-and-violets", claim_seat=1, night=2,
        )
        draft = game.night.prepare_information(1, [2])
        delivery = game.night.deliver_information(draft.id, draft.legal_results[0])
        self.assertEqual(delivery.night_no, 2)
        received = game.player_view(player_id)["night_workflow"]["deliveries"]
        self.assertEqual(received[0]["night_no"], 2)

    def test_replacement_claimant_cannot_read_predecessor_information(self):
        game, first_id = make_game({1: "chef", 2: "imp"}, claim_seat=1)
        delivery = game.night.prepare_information(1)
        self.assertEqual(len(game.player_view(first_id)["night_workflow"]["deliveries"]), 1)
        game.remove_player(first_id)
        second = Player(id="second", name="新玩家")
        game.players[second.id] = second
        game.sit(second.id, 1)
        self.assertEqual(game.player_view(second.id)["night_workflow"]["deliveries"], [])
        self.assertFalse(game.mark_private_deliveries_delivered(second.id))
        self.assertIsNone(delivery.delivered_at)

    def test_information_sent_to_offline_seat_binds_to_first_claimant(self):
        game, _ = make_game({1: "chef", 2: "imp"})
        game.night.prepare_information(1)
        first = Player(id="first", name="线下领取者")
        game.players[first.id] = first
        game.sit(first.id, 1)
        self.assertEqual(len(game.player_view(first.id)["night_workflow"]["deliveries"]), 1)
        game.remove_player(first.id)
        second = Player(id="second", name="继任者")
        game.players[second.id] = second
        game.sit(second.id, 1)
        self.assertEqual(game.player_view(second.id)["night_workflow"]["deliveries"], [])


if __name__ == "__main__":
    unittest.main()
