import unittest

from app.domain.player import Player
from app.game import GameManager
from app.state import SeatState
from night_helpers import make_game


class BalloonistConfigurationTest(unittest.TestCase):
    def setUp(self):
        self.game = GameManager()
        self.game.reset()
        self.game.save = lambda: None

    def test_script_with_balloonist_requires_explicit_version_and_delta(self):
        with self.assertRaisesRegex(ValueError, "气球驾驶员规则"):
            self.game.configure("wafu-leiming", 7)
        with self.assertRaisesRegex(ValueError, "外来者"):
            self.game.configure("wafu-leiming", 7, balloonist_version="new")
        self.game.configure("wafu-leiming", 7, balloonist_version="new",
                            balloonist_outsider_delta=0)
        self.assertEqual(self.game.balloonist_version, "new")
        self.assertEqual(self.game.balloonist_outsider_delta, 0)

    def test_delta_only_applies_when_balloonist_is_in_play(self):
        self.game.configure("wafu-leiming", 7, balloonist_version="new",
                            balloonist_outsider_delta=0)
        without = self.game.expected_composition(["chef", "imp"])
        with_balloonist = self.game.expected_composition(["balloonist", "imp"])
        self.assertEqual(with_balloonist[1], without[1])
        self.game.configure("wafu-leiming", 7, balloonist_version="old",
                            balloonist_outsider_delta=1)
        self.assertEqual(self.game.expected_composition(["balloonist", "imp"])[1],
                         without[1] + 1)

    def test_save_roundtrip_and_missing_version_remains_unset(self):
        self.game.configure("wafu-leiming", 7, balloonist_version="old",
                            balloonist_outsider_delta=1)
        saved = self.game.save_payload()
        self.assertEqual((saved["balloonist_version"], saved["balloonist_outsider_delta"]),
                         ("old", 1))
        self.assertIsNone(self.game.balloonist_version_from_save({"script_id": "wafu-leiming"}))


class BalloonistInformationTest(unittest.TestCase):
    def setUp(self):
        self.game, self.player_id = make_game(
            {1: "balloonist", 2: "recluse", 3: "chef", 4: "widow", 5: "imp"},
            claim_seat=1, script="wafu-leiming",
        )
        self.game.balloonist_version = "new"
        self.game.balloonist_outsider_delta = 0
        self.step = self.game.night.queue.step_for(1, "balloonist")
        self.game.night.queue.current_step_id = self.step.id

    def test_new_version_alternates_registered_type_and_can_revisit_target(self):
        first = self.game.send_balloonist(self.step.id, 2, registered_type="outsider")
        self.assertEqual(first["real_type"], "outsider")
        self.assertEqual(first["registered_type"], "outsider")
        self.game.night_no = 2
        self.game._bind_night_service()
        self.step = self.game.night.queue.step_for(1, "balloonist")
        self.game.night.queue.current_step_id = self.step.id
        self.game.send_balloonist(self.step.id, 3)
        self.game.night_no = 3
        self.game._bind_night_service()
        self.step = self.game.night.queue.step_for(1, "balloonist")
        self.game.night.queue.current_step_id = self.step.id
        candidates = self.game.balloonist_context(1)["candidates"]
        self.assertIn(2, [item["target"] for item in candidates])
        self.game.send_balloonist(self.step.id, 2, registered_type="outsider")
        self.assertEqual([item["target"] for item in self.game.balloonist_storyteller_history()],
                         [2, 3, 2])

    def test_old_version_rejects_repeated_type_and_recluse_snapshot_is_private(self):
        self.game.balloonist_version = "old"
        first = self.game.send_balloonist(self.step.id, 2, registered_type="demon",
                                          registered_role="imp")
        self.assertEqual((first["real_type"], first["registered_type"]),
                         ("outsider", "demon"))
        self.game.night_no = 2
        self.game._bind_night_service()
        self.step = self.game.night.queue.step_for(1, "balloonist")
        self.game.night.queue.current_step_id = self.step.id
        with self.assertRaisesRegex(ValueError, "类型"):
            self.game.send_balloonist(self.step.id, 5)
        self.game.send_balloonist(self.step.id, 3)
        player = self.game.player_view(self.player_id)
        self.assertEqual(player["balloonist_history"], [
            {"night_no": 1, "target": 2, "target_label": "2号", "retracted": False},
            {"night_no": 2, "target": 3, "target_label": "3号", "retracted": False},
        ])
        self.assertNotIn("registered_type", str(player["balloonist_history"]))

    def test_retraction_removes_constraint_but_preserves_audit_and_receipt(self):
        first = self.game.send_balloonist(self.step.id, 2, registered_type="outsider")
        self.game.night.undo(first["event_id"], confirm=True)
        history = self.game.balloonist_storyteller_history()
        self.assertTrue(history[0]["retracted"])
        self.assertTrue(self.game.player_view(self.player_id)["balloonist_history"][0]["retracted"])
        self.game.night_no = 2
        self.game._bind_night_service()
        self.assertIsNone(self.game.balloonist_context(1)["previous_type"])

    def test_legacy_unversioned_game_does_not_create_history(self):
        self.game.balloonist_version = None
        with self.assertRaisesRegex(ValueError, "旧局"):
            self.game.send_balloonist(self.step.id, 2, registered_type="outsider")
        self.assertEqual(self.game.balloonist_storyteller_history(), [])

    def test_session_bound_receipts_do_not_leak_to_successor(self):
        self.game.send_balloonist(self.step.id, 3)
        self.game.players.pop(self.player_id)
        replacement = Player(id="replacement", name="替补", seat=1)
        self.game.players[replacement.id] = replacement
        self.game.seat_state(1).claimed_by = replacement.id
        replacement.bind(self.game.seat_state(1))
        self.assertEqual(self.game.player_view(replacement.id)["balloonist_history"], [])

    def test_offline_delivery_binds_to_first_claimant_only(self):
        self.game.seat_state(1).claimed_by = None
        self.game.players.clear()
        self.game.send_balloonist(self.step.id, 3)
        first = self.game.add_player("先领座")
        self.game.sit(first.id, 1)
        self.assertEqual(len(self.game.player_view(first.id)["balloonist_history"]), 1)
        self.game.remove_player(first.id)
        second = self.game.add_player("后来者")
        self.game.sit(second.id, 1)
        self.assertEqual(self.game.player_view(second.id)["balloonist_history"], [])

    def test_impaired_actor_can_choose_normally_excluded_type_with_false_flag(self):
        self.game.send_balloonist(self.step.id, 3)
        self.game.night_no = 2
        self.game._bind_night_service()
        self.step = self.game.night.queue.step_for(1, "balloonist")
        self.game.night.queue.current_step_id = self.step.id
        source = self.game.journal.append("test_poison", {}, {"op": "noop"})
        self.game.effects.apply("poisoned", 1, source_event=source.id)
        context = self.game.balloonist_context(1)
        same_type = next(item for item in context["candidates"] if item["target"] == 3)
        self.assertEqual(same_type["allowed_types"], ["townsfolk"])
        self.assertEqual(same_type["rule_compliant_types"], [])
        with self.assertRaisesRegex(ValueError, "真假"):
            self.game.send_balloonist(self.step.id, 3)
        sent = self.game.send_balloonist(self.step.id, 3, truthful=False)
        self.assertFalse(sent["rule_compliant"])
        self.assertFalse(sent["truthful"])

    def test_old_version_marks_exhausted_step_skipped(self):
        self.game.balloonist_version = "old"
        for night, target in enumerate((2, 3, 4, 5), start=1):
            self.game.night_no = night
            self.game._bind_night_service()
            step = self.game.night.queue.step_for(1, "balloonist")
            self.game.night.queue.current_step_id = step.id
            self.game.send_balloonist(step.id, target,
                                      **({"registered_type": "outsider"} if target == 2 else {}))
        self.game.night_no = 5
        self.game._bind_night_service()
        step = self.game.night.queue.step_for(1, "balloonist")
        self.assertEqual((step.status, step.skip_reason),
                         ("skipped", "balloonist_types_exhausted"))
        self.assertTrue(self.game.balloonist_context(1)["exhausted"])


if __name__ == "__main__":
    unittest.main()
