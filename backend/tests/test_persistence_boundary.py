import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

import app.game as game_module
from app.game import GameManager
from app.infrastructure.persistence import read_snapshot, write_snapshot


class PersistenceBoundaryTest(unittest.TestCase):
    def test_atomic_write_and_read_preserve_json_contract(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "save" / "game.json"
            payload = {"schema_version": 2, "name": "暗流涌动"}
            write_snapshot(path, payload, backup_legacy=False)
            self.assertEqual(read_snapshot(path), payload)
            self.assertFalse(path.with_suffix(".tmp").exists())
            self.assertIn("暗流涌动", path.read_text(encoding="utf-8"))

    def test_legacy_backup_is_created_only_once(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "game.json"
            path.write_text('{"status":"lobby"}', encoding="utf-8")
            write_snapshot(path, {"schema_version": 2}, backup_legacy=True)
            backup = path.with_suffix(".v1.json")
            self.assertEqual(backup.read_text(encoding="utf-8"), '{"status":"lobby"}')
            write_snapshot(path, {"schema_version": 2, "next": True}, backup_legacy=True)
            self.assertEqual(backup.read_text(encoding="utf-8"), '{"status":"lobby"}')

    def test_manager_reloads_from_override_path_without_live_save(self):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "game.json"
            with patch.object(game_module, "SAVE_PATH", path):
                game = GameManager()
                game.set_room_code("4826")
                restored = GameManager()
            self.assertEqual(restored.room_code, "4826")
            self.assertEqual(json.loads(path.read_text())["room_code"], "4826")


if __name__ == "__main__":
    unittest.main()
