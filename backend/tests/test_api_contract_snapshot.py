"""Freeze the public HTTP schema while handlers move between modules."""

import hashlib
import json
import unittest

from app.main import app
from app.api.websocket import router as websocket_router


class ApiContractSnapshotTest(unittest.TestCase):
    def test_openapi_shape_is_unchanged(self):
        canonical = json.dumps(app.openapi(), sort_keys=True, ensure_ascii=False)
        self.assertEqual(
            hashlib.sha256(canonical.encode()).hexdigest(),
            "55bbd1fec1b5c13fb50fd2fc72588fd8e2eeb7ca816d318b06ee56ce22cde44f",
        )

    def test_websocket_entry_is_unchanged(self):
        self.assertIn("/ws", [route.path for route in websocket_router.routes])
        self.assertIn(websocket_router, [getattr(route, "original_router", None) for route in app.routes])


if __name__ == "__main__":
    unittest.main()
