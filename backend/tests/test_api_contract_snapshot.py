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
            "8b32765c1ff78ff538f0a5e8ba2ed7267cdc6169b1d01ec4ea56677718263bf1",
        )

    def test_websocket_entry_is_unchanged(self):
        self.assertIn("/ws", [route.path for route in websocket_router.routes])
        self.assertIn(websocket_router, [getattr(route, "original_router", None) for route in app.routes])


if __name__ == "__main__":
    unittest.main()
