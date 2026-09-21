import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from app.main import FRONTEND_DIST, app, require_frontend_build


class FrontendStaticLayoutTest(unittest.TestCase):
    def test_only_built_vue_entry_is_served(self):
        self.assertEqual(FRONTEND_DIST.name, "dist")
        self.assertTrue((FRONTEND_DIST / "index.html").is_file())
        self.assertFalse((FRONTEND_DIST.parent / "legacy").exists())
        paths = {getattr(route, "path", None) for route in app.routes}
        self.assertNotIn("/legacy", paths)
        self.assertNotIn("/app.js", paths)
        self.assertNotIn("/styles.css", paths)

    def test_missing_build_has_an_actionable_error(self):
        with TemporaryDirectory() as directory:
            with self.assertRaisesRegex(RuntimeError, "npm run build"):
                require_frontend_build(Path(directory))


if __name__ == "__main__":
    unittest.main()
