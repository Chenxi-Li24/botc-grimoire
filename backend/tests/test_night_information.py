import unittest

from app.night.information import InformationDelivery, InformationDraft
from night_helpers import make_game


class NightInformationTest(unittest.TestCase):
    def test_deterministic_information_is_sent_automatically(self):
        game, _ = make_game({1: "chef", 2: "imp", 3: "poisoner"})
        result = game.night.prepare_information(1)
        self.assertIsInstance(result, InformationDelivery)
        self.assertTrue(result.automatic)
        self.assertEqual(result.claims[0].truthful, True)

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


if __name__ == "__main__":
    unittest.main()
