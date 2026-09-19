import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.main import FRONTEND_DIST, FRONTEND_LEGACY, require_frontend_build


class FrontendStaticLayoutTest(unittest.TestCase):
    def test_built_and_legacy_entries_exist(self):
        self.assertEqual(FRONTEND_DIST.name, "dist")
        self.assertEqual(FRONTEND_LEGACY.name, "legacy")
        self.assertTrue((FRONTEND_DIST / "index.html").is_file())
        self.assertTrue((FRONTEND_LEGACY / "index.html").is_file())

    def test_missing_build_has_an_actionable_error(self):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "npm run build"):
                require_frontend_build(Path(directory))


if __name__ == "__main__":
    unittest.main()
