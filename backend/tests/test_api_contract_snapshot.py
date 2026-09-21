"""Freeze the HTTP schema, including account profiles and Balloonist commands."""

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
            "2fe9a774b6588b4d6d6a408777b40ef5535fbf3183db1778d005d916cb9cf4eb",
        )

    def test_websocket_entry_is_unchanged(self):
        self.assertIn("/ws", [route.path for route in websocket_router.routes])
        self.assertIn(websocket_router, [getattr(route, "original_router", None) for route in app.routes])


if __name__ == "__main__":
    unittest.main()
