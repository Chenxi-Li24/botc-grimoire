import unittest

from app.night.information import InformationClaim, InformationDelivery, InformationDraft
from app.night.models import EventRecord, PendingOutcome
from night_helpers import make_game


class SeatAuditTest(unittest.TestCase):
    def test_unclaimed_seat_gets_private_history_but_player_view_does_not(self):
        game, player_id = make_game({1: "chef", 2: "imp", 3: "poisoner"}, claim_seat=1)
        game.events.append({"seq": 1, "phase": "night", "n": 2, "seat": 2,
                            "type": "kill", "data": {"role": "imp", "target": 1}})
        audit = game.storyteller_view()["seats"][1]["audit"]
        self.assertEqual(audit["events"][0]["selected_seats"], [1])
        self.assertEqual(audit["events"][0]["role_snapshot"], "imp")
        self.assertEqual(audit["events"][0]["number"], 2)
        self.assertNotIn("audit", game.player_view(player_id)["seats"][1])

    def test_withdrawn_information_keeps_original_content_and_truth(self):
        game, _ = make_game({1: "investigator", 2: "imp", 3: "poisoner"})
        game.journal_events.append(EventRecord("message-1", "message_information", {}, {}, [],
                                               "txn", state="undone"))
        game.information_deliveries["delivery-1"] = InformationDelivery(
            id="delivery-1", actor_seat=1, real_character="investigator",
            perceived_character="investigator", targets=[2, 3], true_result="爪牙在其中",
            delivered_result="2号或3号是爪牙", claims=[InformationClaim("结果", "假", False)],
            registrations=[{"seat": 2, "as": "minion"}], effect_snapshot=["poisoned"],
            reason="poisoned", source_event="message-1", draft_id="draft-1",
        )
        entry = next(item for item in game.storyteller_view()["seats"][0]["audit"]["events"]
                     if item["id"] == "delivery-1")
        self.assertEqual(entry["state"], "withdrawn")
        self.assertEqual(entry["delivered_result"], "2号或3号是爪牙")
        self.assertEqual(entry["claims"][0]["truthful"], False)
        self.assertEqual(entry["effect_snapshot"], ["poisoned"])
        self.assertIsNone(entry["number"])

    def test_outcome_separates_selected_and_resolved_targets(self):
        game, _ = make_game({1: "imp", 2: "chef", 3: "poisoner"})
        game.journal_events.extend([
            EventRecord("selection-1", "action_selection", {}, {}, [], "txn"),
            EventRecord("resolution-1", "outcome_resolved", {}, {}, [], "txn"),
        ])
        game.pending_outcomes["outcome-1"] = PendingOutcome(
            id="outcome-1", source_event="selection-1", source_seat=1,
            source_character="imp", selected_seats=[2], hints=[],
            resolution="redirected", affected_seats=[3], status="resolved",
            resolution_event="resolution-1", metadata={"night_no": 3},
        )
        entry = next(item for item in game.storyteller_view()["seats"][0]["audit"]["events"]
                     if item["id"] == "outcome-1")
        self.assertEqual(entry["selected_seats"], [2])
        self.assertEqual(entry["affected_seats"], [3])
        self.assertEqual(entry["number"], 3)
        self.assertEqual(entry["state"], "effective")

    def test_pit_hag_role_change_uses_event_snapshot_after_later_change(self):
        game, _ = make_game({1: "pithag", 2: "chef", 3: "imp"})
        game.journal_events.append(EventRecord(
            "transform-1", "pit_hag_transformation",
            {"actor_seat": 1, "target_seat": 2, "from": "chef", "to": "investigator",
             "night_no": 2}, {}, [], "txn"))
        game.seat_roles[2] = "imp"
        entry = next(item for item in game.storyteller_view()["seats"][1]["audit"]["events"]
                     if item["id"] == "transform-1")
        self.assertEqual((entry["from"], entry["to"]), ("chef", "investigator"))
        self.assertEqual(entry["role_snapshot"], "chef")
        self.assertEqual(entry["number"], 2)

    def test_red_herring_only_when_fortune_teller_is_present(self):
        game, player_id = make_game({1: "fortuneteller", 2: "chef", 3: "imp"}, claim_seat=2)
        game.fortuneteller_red = 2
        self.assertTrue(game.storyteller_view()["seats"][1]["red_herring"])
        self.assertNotIn("red_herring", game.player_view(player_id)["seats"][1])
        game.seat_roles[1] = "chef"
        self.assertNotIn("red_herring", game.storyteller_view()["seats"][1])

    def test_unsent_draft_is_distinct_from_missing_history(self):
        game, _ = make_game({1: "investigator", 2: "imp", 3: "poisoner"})
        game.information_drafts["draft-1"] = InformationDraft(
            id="draft-1", actor_seat=1, real_character="investigator",
            perceived_character="investigator", resolver_key=None, targets=[2, 3],
            true_result="爪牙在其中", legal_results=[], registrations=[], effect_snapshot=[],
            reason=None, source_event="manual", prepared_event="prepared-1",
        )
        entry = next(item for item in game.storyteller_view()["seats"][0]["audit"]["events"]
                     if item["id"] == "draft-1")
        self.assertEqual(entry["state"], "unsent")
        self.assertIsNone(entry["number"])
        self.assertNotIn("delivered_result", entry)

    def test_selection_without_outcome_remains_visible(self):
        game, _ = make_game({1: "imp", 2: "chef", 3: "poisoner"})
        game.journal_events.append(EventRecord(
            "selection-1", "action_selection",
            {"source_seat": 1, "source_character": "imp", "selected_seats": [2],
             "step_id": "night:2:100:1:imp:real:other"}, {}, [], "txn"))
        entry = next(item for item in game.storyteller_view()["seats"][0]["audit"]["events"]
                     if item["id"] == "selection-1")
        self.assertEqual(entry["state"], "selected")
        self.assertEqual(entry["number"], 2)

    def test_lunatic_choice_links_to_demon_and_dawn_death_is_separate(self):
        game, _ = make_game({1: "lunatic", 2: "imp", 3: "chef", 4: "chef"})
        game.pending_outcomes["lunatic-1"] = PendingOutcome(
            id="lunatic-1", source_event="select-l", source_seat=1,
            source_character="lunatic", selected_seats=[3], hints=[],
            resolution="choice_only", status="resolved", metadata={"night_no": 2, "lunatic_choice": True},
        )
        game.pending_outcomes["demon-1"] = PendingOutcome(
            id="demon-1", source_event="select-d", source_seat=2,
            source_character="imp", selected_seats=[3], hints=[],
            resolution="redirected", affected_seats=[4], status="resolved",
            metadata={"night_no": 2, "is_demon_attack": True},
        )
        victim = game.seat_state(4)
        victim.public_alive = False
        victim.death_record = {"outcome_id": "demon-1", "night_no": 2}
        seats = game.storyteller_view()["seats"]
        lunatic = next(item for item in seats[0]["audit"]["events"] if item["id"] == "lunatic-1")
        demon = next(item for item in seats[1]["audit"]["events"] if item["id"] == "demon-1")
        self.assertEqual(lunatic["linked_outcome_id"], "demon-1")
        self.assertTrue(lunatic["demon_followed"])
        self.assertEqual(demon["linked_lunatic_selection"], [3])
        self.assertEqual(demon["selected_seats"], [3])
        self.assertEqual(demon["affected_seats"], [4])
        self.assertEqual(demon["dawn_deaths"], [4])


if __name__ == "__main__":
    unittest.main()
