import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.game import GameManager, Player
from app.night.information import InformationDraft
from app.night.player_actions import submit_player_night_action
from app.night.models import PendingOutcome
from tests.night_helpers import make_game


def current_step(game, seat, character):
    step = next(
        item for item in game.night.queue.steps
        if item.actor_seat == seat and item.character_id == character
    )
    game.night.queue.current_step_id = step.id
    return step


class PlayerNightActionsTest(unittest.TestCase):
    def test_rejects_foreign_and_stale_steps(self):
        game, player_id = make_game(
            {1: "poisoner", 2: "imp", 3: "chef"},
            claim_seat=1, night=2, script="trouble-brewing",
        )
        poisoner = next(item for item in game.night.queue.steps if item.actor_seat == 1)
        imp = current_step(game, 2, "imp")

        with self.assertRaisesRegex(ValueError, "不是你的夜晚步骤"):
            submit_player_night_action(game, player_id, {
                "step_id": imp.id,
                "selected_seats": [3],
            })
        with self.assertRaisesRegex(ValueError, "夜晚步骤已变化"):
            submit_player_night_action(game, player_id, {
                "step_id": poisoner.id,
                "selected_seats": [3],
            })

    def test_validates_targets_before_dispatch(self):
        game, player_id = make_game(
            {1: "poisoner", 2: "imp"},
            claim_seat=1, night=2, script="trouble-brewing",
        )
        step = current_step(game, 1, "poisoner")
        with self.assertRaisesRegex(RuntimeError, "需要选择 1 名玩家"):
            submit_player_night_action(game, player_id, {
                "step_id": step.id,
                "selected_seats": [],
            })

    def test_demon_player_choice_creates_pending_outcome(self):
        game, player_id = make_game(
            {1: "imp", 2: "chef"},
            claim_seat=1, night=2, script="trouble-brewing",
        )
        step = current_step(game, 1, "imp")

        result = submit_player_night_action(game, player_id, {
            "step_id": step.id,
            "selected_seats": [2],
        })

        self.assertIsInstance(result, PendingOutcome)
        self.assertEqual(result.selected_seats, [2])
        self.assertEqual(result.status, "pending")
        self.assertEqual(result.metadata["step_id"], step.id)
        self.assertEqual(step.values["targets"], [2])

    def test_lunatic_choice_is_resolved_as_choice_only_and_visible_to_demon(self):
        game, player_id = make_game(
            {1: "lunatic", 2: "shabaloth", 3: "chambermaid"},
            claim_seat=1, night=2, script="bad-moon-rising",
        )
        demon = Player(id="demon-player", name="真恶魔", seat=2)
        game.players[demon.id] = demon
        game.seat_state(2).claimed_by = demon.id
        demon.bind(game.seat_state(2))
        step = current_step(game, 1, "lunatic")

        result = submit_player_night_action(game, player_id, {
            "step_id": step.id,
            "selected_seats": [3],
        })

        self.assertEqual(result.status, "resolved")
        self.assertEqual(result.resolution, "choice_only")
        demon_step = current_step(game, 2, "shabaloth")
        workflow = game._player_night_workflow(2)
        self.assertEqual(workflow["prompt"]["id"], demon_step.id)
        self.assertEqual(workflow["lunatic_choices"][0]["target_seats"], [3])

    def test_information_action_prepares_canonical_draft(self):
        game, player_id = make_game(
            {1: "dreamer", 2: "imp", 3: "cerenovus"},
            claim_seat=1, night=2, script="sects-and-violets",
        )
        step = current_step(game, 1, "dreamer")

        result = submit_player_night_action(game, player_id, {
            "step_id": step.id,
            "selected_seats": [2],
        })

        self.assertIsInstance(result, InformationDraft)
        self.assertEqual(result.targets, [2])
        self.assertEqual(step.values["targets"], [2])

    def test_submitted_choice_is_receipted_once_and_cannot_be_changed(self):
        game, player_id = make_game(
            {1: "imp", 2: "chef", 3: "poisoner"},
            claim_seat=1, night=2, script="trouble-brewing",
        )
        step = current_step(game, 1, "imp")
        body = {"step_id": step.id, "selected_seats": [2]}
        submit_player_night_action(game, player_id, body)
        workflow = game._player_night_workflow(1)
        self.assertIsNone(workflow["prompt"])
        self.assertEqual(workflow["receipt"]["step_id"], step.id)
        submit_player_night_action(game, player_id, body)
        self.assertEqual(len(game.pending_outcomes), 1)
        with self.assertRaisesRegex(ValueError, "已经提交"):
            submit_player_night_action(game, player_id, {
                "step_id": step.id, "selected_seats": [3],
            })

    def test_receipt_remains_visible_after_other_players_steps_become_current(self):
        game, player_id = make_game(
            {1: "poisoner", 2: "imp", 3: "chef"},
            claim_seat=1, night=2, script="trouble-brewing",
        )
        step = current_step(game, 1, "poisoner")
        submit_player_night_action(game, player_id, {
            "step_id": step.id, "selected_seats": [3],
        })
        other = game.night.queue.step_for(2, "imp")
        game.night.queue.current_step_id = other.id
        self.assertEqual(game.player_view(player_id)["night_workflow"]["receipt"],
                         {"step_id": step.id})

    def test_storyteller_undo_clears_the_player_submission_receipt(self):
        game, player_id = make_game(
            {1: "imp", 2: "chef", 3: "poisoner"},
            claim_seat=1, night=2, script="trouble-brewing",
        )
        step = current_step(game, 1, "imp")
        result = submit_player_night_action(game, player_id, {
            "step_id": step.id, "selected_seats": [2],
        })
        self.assertEqual(game._player_night_workflow(1)["receipt"], {"step_id": step.id})
        game.night.undo(result.source_event, confirm=True)
        self.assertNotIn("player_submission", step.values)

    def test_widow_grimoire_survives_submission_until_dawn_without_leaking(self):
        game, player_id = make_game(
            {1: "widow", 2: "drunk", 3: "imp"},
            claim_seat=1, script="wafu-leiming",
        )
        game.seat_state(2).perceived_character_id = "chef"
        step = game.night.queue.step_for(1, "widow")
        game.night.navigate(step_id=step.id)
        before = game.player_view(player_id)["night_workflow"]
        self.assertEqual(before["widow_grimoire"]["seats"][1]["real_character_id"], "drunk")
        self.assertEqual(before["widow_grimoire"]["seats"][1]["perceived_character_id"], "chef")
        submit_player_night_action(game, player_id, {
            "step_id": step.id, "selected_seats": [2],
        })
        after = game.player_view(player_id)["night_workflow"]
        self.assertIsNone(after["prompt"])
        self.assertEqual(after["widow_grimoire"]["seats"][1]["real_character_id"], "drunk")
        game.night.navigate(direction="next")
        self.assertIsNotNone(game.player_view(player_id)["night_workflow"]["widow_grimoire"])
        game.phase = "day"
        self.assertIsNone(game.player_view(player_id)["night_workflow"]["widow_grimoire"])

    def test_widow_grimoire_is_not_loaned_to_previous_or_other_claimant(self):
        game, widow_id = make_game(
            {1: "widow", 2: "drunk", 3: "imp"},
            claim_seat=1, script="wafu-leiming",
        )
        game.night.navigate(step_id=game.night.queue.step_for(1, "widow").id)
        other = Player(id="other-player", name="旁观", seat=2)
        game.players[other.id] = other
        game.seat_state(2).claimed_by = other.id
        other.bind(game.seat_state(2))
        game.night_steps = [{"key": "widow"}]
        game.night_idx = 0
        self.assertIsNone(game.player_view(other.id)["night_workflow"]["widow_grimoire"])
        game.seat_state(1).claimed_by = "new-owner"
        former_view = game.player_view(widow_id)
        self.assertIsNone(former_view["night_workflow"]["widow_grimoire"])
        self.assertNotIn("grimoire", former_view)

    def test_replacement_widow_claimant_does_not_inherit_open_grimoire(self):
        game, first_id = make_game(
            {1: "widow", 2: "drunk", 3: "imp"},
            claim_seat=1, script="wafu-leiming",
        )
        step = game.night.queue.step_for(1, "widow")
        game.night.navigate(step_id=step.id)
        self.assertIsNotNone(game.player_view(first_id)["night_workflow"]["widow_grimoire"])
        game.remove_player(first_id)
        replacement = Player(id="replacement", name="继任寡妇")
        game.players[replacement.id] = replacement
        game.sit(replacement.id, 1)
        view = game.player_view(replacement.id)
        self.assertIsNone(view["night_workflow"]["widow_grimoire"])
        self.assertNotIn("grimoire", view)

    def test_status_roles_dispatch_to_sourced_effects(self):
        cases = [
            ("trouble-brewing", "poisoner", 2, None, "poisoned"),
            ("wafu-leiming", "widow", 1, None, "poisoned"),
            ("sects-and-violets", "cerenovus", 2, "dreamer", "mad"),
        ]
        for script, character, night, chosen_character, effect_type in cases:
            with self.subTest(character=character):
                assignments = {1: character, 2: "dreamer" if script != "trouble-brewing" else "chef"}
                game, player_id = make_game(
                    assignments, claim_seat=1, night=night, script=script,
                )
                step = current_step(game, 1, character)
                result = submit_player_night_action(game, player_id, {
                    "step_id": step.id,
                    "selected_seats": [2],
                    "character_id": chosen_character,
                })
                self.assertEqual(result.type, effect_type)
                self.assertEqual(result.source_character, character)
                self.assertEqual(step.values["targets"], [2])

    def test_pit_hag_action_creates_private_preview(self):
        game, player_id = make_game(
            {1: "pithag", 2: "dreamer", 3: "fang-gu"},
            claim_seat=1, night=2, script="sects-and-violets",
        )
        step = current_step(game, 1, "pithag")

        preview = submit_player_night_action(game, player_id, {
            "step_id": step.id,
            "selected_seats": [2],
            "character_id": "mutant",
        })

        self.assertEqual(preview.status, "pending")
        self.assertEqual(preview.target_seat, 2)
        self.assertEqual(step.values["character"], "mutant")
        self.assertIn(preview.id, game.pending_transformations)

    def test_projection_contains_only_safe_selection_fields(self):
        game, player_id = make_game(
            {1: "dreamer", 2: "imp", 3: "cerenovus"},
            claim_seat=1, night=2, script="sects-and-violets",
        )
        current_step(game, 1, "dreamer")

        prompt = game.player_view(player_id)["night_workflow"]["prompt"]

        self.assertEqual(prompt["target_seats"], [2, 3])
        self.assertEqual(prompt["player_count"], 1)
        self.assertFalse(prompt["allow_self"])
        self.assertTrue(all(set(item) <= {"id", "name", "team"}
                            for item in prompt["character_candidates"]))
        self.assertNotIn("seat_context", repr(prompt))
        self.assertNotIn("true_result", repr(prompt))

    def test_player_selection_survives_save_reload(self):
        game, player_id = make_game(
            {1: "imp", 2: "chef"},
            claim_seat=1, night=2, script="trouble-brewing",
        )
        step = current_step(game, 1, "imp")
        result = submit_player_night_action(game, player_id, {
            "step_id": step.id,
            "selected_seats": [2],
        })

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "game.json"
            with patch("app.game.SAVE_PATH", path):
                GameManager.save(game)
                restored = GameManager()

        self.assertIn(result.id, restored.pending_outcomes)
        restored_step = restored.night.step(step.id)
        self.assertEqual(restored_step.values["targets"], [2])
        self.assertEqual(restored.player_view(player_id)["night_workflow"]["receipt"],
                         {"step_id": step.id})


if __name__ == "__main__":
    unittest.main()
