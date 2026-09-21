"""Freeze the intentional HTTP schema, including private inference writes."""

import hashlib
import json
import unittest

from app.main import app
from app.api.websocket import router as websocket_router


class ApiContractSnapshotTest(unittest.TestCase):
    def test_openapi_shape_matches_expanded_contract(self):
        canonical = json.dumps(app.openapi(), sort_keys=True, ensure_ascii=False)
        self.assertEqual(
            hashlib.sha256(canonical.encode()).hexdigest(),
            "e0315e971aeb79d25b8df2335c4fb14c5d48dca2fea191def429a2c223ff6b1e",
        )

    def test_websocket_entry_is_unchanged(self):
        self.assertIn("/ws", [route.path for route in websocket_router.routes])
        self.assertIn(websocket_router, [getattr(route, "original_router", None) for route in app.routes])


if __name__ == "__main__":
    unittest.main()
