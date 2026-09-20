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


if __name__ == "__main__":
    unittest.main()
