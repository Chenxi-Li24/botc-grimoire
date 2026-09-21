"""Contracts for the opt-in guest/WebSocket load probe."""

import asyncio
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from types import SimpleNamespace
from unittest.mock import patch

from tools.load_benchmark import (Client, benchmark, guest_name, percentile_ms, receive_room_code,
                                  validate_active_game, validate_target, websocket_url)


class LoadBenchmarkTests(unittest.TestCase):
    def test_percentiles_use_nearest_rank_and_report_no_samples(self):
        self.assertEqual(percentile_ms([10, 30, 20, 40], 50), 20)
        self.assertEqual(percentile_ms([10, 30, 20, 40], 95), 40)
        self.assertIsNone(percentile_ms([], 99))

    def test_default_target_is_local_and_not_live_port(self):
        with self.assertRaisesRegex(ValueError, "port 8000"):
            validate_target("http://127.0.0.1:8000", allow_live=False, allow_remote=False)
        with self.assertRaisesRegex(ValueError, "non-loopback"):
            validate_target("https://join.example.test", allow_live=False, allow_remote=False)
        self.assertEqual(
            validate_target("http://localhost:8001/", allow_live=False, allow_remote=False),
            "http://localhost:8001",
        )

    def test_live_and_remote_targets_need_separate_explicit_flags(self):
        self.assertEqual(
            validate_target("http://127.0.0.1:8000", allow_live=True, allow_remote=False),
            "http://127.0.0.1:8000",
        )
        self.assertEqual(
            validate_target("https://join.example.test", allow_live=False, allow_remote=True),
            "https://join.example.test",
        )

    def test_target_rejects_credentials_paths_and_query_strings(self):
        for target in ("http://u:p@localhost:8001", "http://localhost:8001/foo",
                       "http://localhost:8001/?x=1", "ftp://localhost:8001"):
            with self.subTest(target=target), self.assertRaises(ValueError):
                validate_target(target, allow_live=True, allow_remote=True)

    def test_websocket_url_preserves_origin_authority(self):
        self.assertEqual(websocket_url("http://127.0.0.1:8019"), "ws://127.0.0.1:8019/ws")
        self.assertEqual(websocket_url("https://join.example.test"), "wss://join.example.test/ws")

    def test_guest_write_sends_session_csrf_header(self):
        class Handler(BaseHTTPRequestHandler):
            def do_POST(self):
                body = ('{"csrf":"' + self.headers.get("X-CSRF-Token", "") + '"}').encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *_args):
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            client = Client(f"http://127.0.0.1:{server.server_port}")
            client.csrf_token = "session-secret"
            self.assertEqual(client.request("POST", "/wish", {"wish": "x"})["csrf"],
                             "session-secret")
        finally:
            server.shutdown()
            server.server_close()
            thread.join()

    def test_active_game_requires_15_players_and_isolated_empty_lobby(self):
        clean = {"status": "lobby", "players": [], "winner": None}
        validate_active_game("http://127.0.0.1:8019", clean, 15)
        for origin, state, count in (
            ("http://127.0.0.1:8000", clean, 15),
            ("https://join.example.test", clean, 15),
            ("http://127.0.0.1:8019", clean, 14),
            ("http://127.0.0.1:8019", {**clean, "players": [{"id": "other"}]}, 15),
            ("http://127.0.0.1:8019", {**clean, "status": "playing"}, 15),
            ("http://127.0.0.1:8019", {**clean, "winner": "good"}, 15),
        ):
            with self.subTest(origin=origin, state=state, count=count), self.assertRaises(ValueError):
                validate_active_game(origin, state, count)

    def test_broadcast_receiver_waits_for_new_room_code(self):
        class Socket:
            def __init__(self):
                self.values = iter(['{"room_code":"0001"}', '{"room_code":"0002"}'])

            async def recv(self):
                return next(self.values)

        client = Client("http://127.0.0.1:8019")
        client.socket = Socket()
        elapsed = asyncio.run(receive_room_code(client, "0002", time.perf_counter()))
        self.assertGreaterEqual(elapsed, 0)

    def test_generated_guest_names_fit_eight_character_join_limit(self):
        names = [guest_name("load-abcdef", index) for index in range(1, 16)]
        self.assertEqual(len(set(names)), 15)
        self.assertTrue(all(1 <= len(name) <= 8 for name in names))

    def test_active_game_rejects_port_8000_before_network_request(self):
        args = SimpleNamespace(url="http://127.0.0.1:8000", allow_live=True,
                               allow_remote=False, players=15, http_rounds=1,
                               push_rounds=0, broadcast_rounds=1, active_game=True,
                               password="test-secret")
        with patch.object(Client, "request", side_effect=AssertionError("network request made")):
            with self.assertRaisesRegex(ValueError, "non-8000"):
                asyncio.run(benchmark(args))


if __name__ == "__main__":
    unittest.main()
