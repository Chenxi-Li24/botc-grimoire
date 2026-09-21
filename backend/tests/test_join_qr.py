import os
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.api import qr as qr_module


class _QrImage:
    def save(self, buffer, format):
        buffer.write(b"png")


class JoinQrTest(unittest.TestCase):
    def test_join_links_keep_local_first_and_include_public_fallback(self):
        with patch.object(qr_module, "get_lan_ip", return_value="192.168.1.23"), \
             patch.object(qr_module.game, "room_code", "2468"), \
             patch.dict(os.environ, {"PUBLIC_URL": "https://join.example.test:30677/"}):
            self.assertEqual(qr_module.join_links(), {
                "local_url": "http://192.168.1.23:8000/#/?room=2468",
                "public_url": "https://join.example.test:30677/#/?room=2468",
            })

    def test_public_qr_encodes_public_join_url(self):
        with patch.object(qr_module.game, "room_code", "2468"), \
             patch.dict(os.environ, {"PUBLIC_URL": "https://join.example.test:30677/"}), \
             patch.object(qr_module.qrcode, "make", return_value=_QrImage()) as make:
            response = qr_module.qr(mode="public")

        self.assertEqual(make.call_args.args[0], "https://join.example.test:30677/#/?room=2468")
        self.assertEqual(response.media_type, "image/png")

    def test_public_qr_reports_missing_public_url_without_replacing_local_qr(self):
        with patch.object(qr_module, "get_lan_ip", return_value="192.168.1.23"), \
             patch.object(qr_module.game, "room_code", "2468"), \
             patch.dict(os.environ, {"PUBLIC_URL": ""}), \
             patch.object(qr_module.qrcode, "make", return_value=_QrImage()) as make:
            self.assertIsNone(qr_module.join_links()["public_url"])
            with self.assertRaises(HTTPException) as failure:
                qr_module.qr(mode="public")
            qr_module.qr(mode="local")

        self.assertEqual(failure.exception.status_code, 404)
        self.assertEqual(make.call_args.args[0], "http://192.168.1.23:8000/#/?room=2468")


if __name__ == "__main__":
    unittest.main()
