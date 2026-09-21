import tempfile
import unittest
import sqlite3
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from PIL import Image

from app import game as game_module
from app.api import player as player_api
from app.application import runtime
from app.game import GameManager
from app.infrastructure.identity_store import IdentityStore
from app.main import app


class IdentityApiTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.save_patch = patch.object(game_module, "SAVE_PATH", Path(self.temp.name) / "game.json")
        self.save_patch.start()
        self.game = GameManager()
        self.store = IdentityStore(Path(self.temp.name) / "accounts.sqlite3")
        self.game_patch = patch.object(runtime, "game", self.game)
        self.player_patch = patch.object(player_api, "game", self.game)
        self.store_patch = patch.object(runtime, "identity_store", self.store, create=True)
        for p in (self.game_patch, self.player_patch, self.store_patch):
            p.start()
        self.client = TestClient(app, headers={"Origin": "http://testserver"})

    def tearDown(self):
        for p in (self.store_patch, self.player_patch, self.game_patch, self.save_patch):
            p.stop()
        self.temp.cleanup()

    def test_guest_session_is_private_and_duplicate_names_are_rejected(self):
        room = self.game.room_code
        first = self.client.post("/api/join", json={"name": "甲", "room_code": room})
        self.assertEqual(first.status_code, 200)
        alice = first.json()["player_id"]
        self.assertEqual(self.client.get("/api/session").json()["player_id"], alice)
        other = TestClient(app, headers={"Origin": "http://testserver"})
        self.assertEqual(other.get(f"/api/me/{alice}").status_code, 401)
        second = other.post("/api/join", json={"name": "甲", "room_code": room})
        self.assertEqual(second.status_code, 409)
        self.assertEqual(len(self.game.players), 1)

    def test_registration_profile_and_uid_login_are_password_gated(self):
        created = self.client.post("/api/account/register", json={
            "username": "Alice", "password": "four", "nickname": "🧙甲",
        })
        self.assertEqual(created.status_code, 200)
        uid = created.json()["uid"]
        self.assertRegex(uid, r"^[1-9][0-9]{3}$")
        profile = self.client.get("/api/account/profile").json()
        self.assertEqual(profile["nickname"], "🧙甲")
        self.assertEqual(profile["uid"], uid)
        csrf = self.client.get("/api/session").json()["csrf_token"]
        self.client.post("/api/account/logout", headers={"X-CSRF-Token": csrf})
        self.assertEqual(self.client.post("/api/account/login", json={
            "username": uid, "password": "four", "mode": "username",
        }).status_code, 401)
        self.assertEqual(self.client.post("/api/account/login", json={
            "username": uid, "password": "wrong", "mode": "uid",
        }).status_code, 401)
        self.assertEqual(self.client.post("/api/account/login", json={
            "username": uid, "password": "four", "mode": "uid",
        }).status_code, 200)

    def test_legacy_long_account_nickname_can_join_without_silent_truncation(self):
        account_id, _ = self.store.create_account("Alice", "four")
        with sqlite3.connect(self.store.path) as db:
            db.execute("UPDATE accounts SET nickname = ?, nickname_key = ? WHERE id = ?",
                       ("LongLegacyName", "longlegacyname", account_id))
        token, csrf = self.store.issue_session(account_id=account_id)
        self.client.cookies.set("botc_session", token)
        joined = self.client.post("/api/join", json={"name": "LongLegacyName", "room_code": self.game.room_code},
                                  headers={"X-CSRF-Token": csrf})
        self.assertEqual(joined.status_code, 200)
        self.assertEqual(self.game.players[joined.json()["player_id"]].name, "LongLegacyName")

    def test_nickname_change_updates_live_player_but_not_chat_snapshot(self):
        self.client.post("/api/join", json={"name": "旧名", "room_code": self.game.room_code})
        csrf = self.client.get("/api/session").json()["csrf_token"]
        registered = self.client.post("/api/account/register", json={
            "username": "Alice", "password": "four", "nickname": "旧名",
        }, headers={"X-CSRF-Token": csrf})
        self.assertEqual(registered.status_code, 200)
        player = next(iter(self.game.players.values()))
        self.game.events.append({"name": "旧名", "kind": "chat"})
        csrf = self.client.get("/api/session").json()["csrf_token"]
        changed = self.client.post("/api/account/nickname", json={"nickname": "新名"}, headers={"X-CSRF-Token": csrf})
        self.assertEqual(changed.status_code, 200)
        self.assertEqual(player.name, "新名")
        self.assertEqual(self.game.events[-1]["name"], "旧名")

    def test_avatar_upload_reencodes_image_and_rejects_svg_or_oversize(self):
        self.client.post("/api/account/register", json={"username": "Alice", "password": "four"})
        csrf = self.client.get("/api/session").json()["csrf_token"]
        stream = BytesIO()
        Image.new("RGB", (2, 2), (255, 0, 0)).save(stream, format="JPEG")
        uploaded = self.client.put("/api/account/avatar", content=stream.getvalue(),
                                   headers={"X-CSRF-Token": csrf, "Content-Type": "image/jpeg"})
        self.assertEqual(uploaded.status_code, 200)
        avatar = self.client.get("/api/account/avatar")
        self.assertEqual(avatar.status_code, 200)
        self.assertEqual(avatar.headers["content-type"], "image/png")
        self.assertTrue(avatar.content.startswith(b"\x89PNG"))
        self.assertEqual(self.client.put("/api/account/avatar", content=b"<svg></svg>",
                                         headers={"X-CSRF-Token": csrf, "Content-Type": "image/svg+xml"}).status_code, 400)
        self.assertEqual(self.client.put("/api/account/avatar", content=b"x" * (2 * 1024 * 1024 + 1),
                                         headers={"X-CSRF-Token": csrf, "Content-Type": "image/png"}).status_code, 413)

    def test_account_login_restores_linked_guest_and_rejects_missing_csrf(self):
        room = self.game.room_code
        player_id = self.client.post("/api/join", json={"name": "甲", "room_code": room}).json()["player_id"]
        csrf = self.client.get("/api/session").json()["csrf_token"]
        register = self.client.post(
            "/api/account/register",
            json={"username": "Alice", "password": "test-password-123"},
            headers={"X-CSRF-Token": csrf},
        )
        self.assertEqual(register.status_code, 200)
        self.assertTrue(register.json()["recovery_code"])
        self.assertEqual(self.game.players[player_id].account_id, register.json()["account_id"])
        self.assertEqual(self.client.post("/api/account/logout").status_code, 403)
        other = TestClient(app, headers={"Origin": "http://testserver"})
        login = other.post("/api/account/login", json={"username": "alice", "password": "test-password-123"})
        self.assertEqual(login.status_code, 200)
        self.assertEqual(other.get("/api/session").json()["player_id"], player_id)

    def test_logging_into_another_account_cannot_take_over_current_seat(self):
        room = self.game.room_code
        player_id = self.client.post("/api/join", json={"name": "甲", "room_code": room}).json()["player_id"]
        csrf = self.client.get("/api/session").json()["csrf_token"]
        first = self.client.post("/api/account/register", json={
            "username": "Alice", "password": "alice-password-123",
        }, headers={"X-CSRF-Token": csrf}).json()
        self.store.create_account("Bob", "bob-password-123")
        csrf = self.client.get("/api/session").json()["csrf_token"]
        switched = self.client.post("/api/account/login", json={
            "username": "Bob", "password": "bob-password-123",
        }, headers={"X-CSRF-Token": csrf})
        self.assertEqual(switched.status_code, 409)
        self.assertEqual(self.game.players[player_id].account_id, first["account_id"])
        self.assertEqual(self.client.get("/api/session").json()["player_id"], player_id)

    def test_reset_password_limits_invalid_attempts_before_hashing(self):
        self.store.create_account("Alice", "alice-password-123")
        with patch.object(type(self.store.password_hasher), "hash", side_effect=AssertionError("unexpected hash")) as hashed:
            for _ in range(self.store.RESET_LIMIT):
                response = self.client.post("/api/account/reset-password", json={
                    "username": "Alice", "recovery_code": "invalid", "new_password": "new-password-123",
                })
                self.assertEqual(response.status_code, 401)
            self.assertEqual(hashed.call_count, 0)
            response = self.client.post("/api/account/reset-password", json={
                "username": "Alice", "recovery_code": "invalid", "new_password": "new-password-123",
            })
            self.assertEqual(response.status_code, 429)
            self.assertEqual(hashed.call_count, 0)

    def test_cross_origin_join_is_rejected(self):
        bad = TestClient(app, headers={"Origin": "https://evil.example"})
        response = bad.post("/api/join", json={"name": "甲", "room_code": self.game.room_code})
        self.assertEqual(response.status_code, 403)

    def test_account_recovery_and_logout_all(self):
        created = self.client.post(
            "/api/account/register", json={"username": "Alice", "password": "old-password-123"}
        )
        self.assertEqual(created.status_code, 200)
        code = created.json()["recovery_code"]
        second = TestClient(app, headers={"Origin": "http://testserver"})
        self.assertEqual(second.post(
            "/api/account/login", json={"username": "Alice", "password": "old-password-123"}
        ).status_code, 200)
        csrf = self.client.get("/api/session").json()["csrf_token"]
        self.assertEqual(self.client.post(
            "/api/account/logout-all", headers={"X-CSRF-Token": csrf}
        ).status_code, 200)
        self.assertEqual(second.get("/api/session").status_code, 401)
        reset = self.client.post("/api/account/reset-password", json={
            "username": "Alice", "recovery_code": code, "new_password": "new-password-123"
        })
        self.assertEqual(reset.status_code, 200)
        self.assertTrue(reset.json()["recovery_code"])
        self.assertEqual(self.client.post("/api/account/reset-password", json={
            "username": "Alice", "recovery_code": code, "new_password": "newer-password-123"
        }, headers={"X-CSRF-Token": self.client.get("/api/session").json()["csrf_token"]}).status_code, 401)
        fresh = TestClient(app, headers={"Origin": "http://testserver"})
        self.assertEqual(fresh.post(
            "/api/account/login", json={"username": "Alice", "password": "old-password-123"}
        ).status_code, 401)

    def test_session_expiry_is_not_a_guest_credential(self):
        token, _ = self.store.issue_session(player_id="not-a-player", game_id=self.game.game_id, now=1, ttl=1)
        self.client.cookies.set("botc_session", token)
        self.assertEqual(self.client.get("/api/session").status_code, 401)

    def test_stale_guest_cookie_does_not_block_registration_without_csrf(self):
        token, _ = self.store.issue_session(player_id="old-player", game_id="old-game")
        self.client.cookies.set("botc_session", token)
        created = self.client.post("/api/account/register", json={"username": "Alice", "password": "four"})
        self.assertEqual(created.status_code, 200)
        self.assertRegex(created.json()["uid"], r"^[1-9][0-9]{3}$")

    def test_removed_guest_session_cannot_be_used(self):
        player_id = self.client.post("/api/join", json={
            "name": "甲", "room_code": self.game.room_code
        }).json()["player_id"]
        self.game.remove_player(player_id)
        self.assertEqual(self.client.get("/api/session").status_code, 401)


if __name__ == "__main__":
    unittest.main()
