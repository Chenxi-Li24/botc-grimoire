import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.infrastructure.identity_store import IdentityStore, LoginRateLimited


class IdentityStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp.name) / "accounts.sqlite3"
        self.store = IdentityStore(self.db_path)

    def tearDown(self):
        self.temp.cleanup()

    def test_account_normalization_and_persistent_session(self):
        account_id, recovery = self.store.create_account("Alice", "test-only-password")
        self.assertTrue(recovery)
        self.assertIsNone(self.store.authenticate("Ａｌｉｃｅ", "wrong"))
        self.assertEqual(self.store.authenticate("alice", "test-only-password"), account_id)
        with self.assertRaises(ValueError):
            self.store.create_account("ＡＬＩＣＥ", "another-password")
        token, csrf = self.store.issue_session(account_id=account_id)
        raw = self.db_path.read_bytes().decode("latin1")
        self.assertNotIn(token, raw)
        self.assertNotIn("test-only-password", raw)
        session = IdentityStore(self.db_path).resolve_session(token)
        self.assertEqual(session.account_id, account_id)
        self.assertEqual(session.csrf, csrf)

    def test_session_expiry_and_revocation(self):
        account_id, _ = self.store.create_account("Bob", "test-only-password")
        token, _ = self.store.issue_session(account_id=account_id, now=1000, ttl=60)
        self.assertIsNotNone(self.store.resolve_session(token, now=1059))
        self.assertIsNone(self.store.resolve_session(token, now=1060))
        token, _ = self.store.issue_session(account_id=account_id, now=1000, ttl=60)
        self.store.revoke_session(token)
        self.assertIsNone(self.store.resolve_session(token, now=1001))
        first, _ = self.store.issue_session(account_id=account_id, now=1000, ttl=60)
        second, _ = self.store.issue_session(account_id=account_id, now=1000, ttl=60)
        self.store.revoke_account_sessions(account_id)
        self.assertIsNone(self.store.resolve_session(first, now=1001))
        self.assertIsNone(self.store.resolve_session(second, now=1001))

    def test_login_failures_are_rate_limited(self):
        self.store.create_account("Carol", "test-only-password")
        for _ in range(5):
            self.assertIsNone(self.store.authenticate("Carol", "wrong", now=1000))
        with self.assertRaises(LoginRateLimited):
            self.store.authenticate("Carol", "test-only-password", now=1001)
        self.assertIsNotNone(self.store.authenticate("Carol", "test-only-password", now=1901))

    def test_schema_contains_recovery_and_archive_tables(self):
        with sqlite3.connect(self.db_path) as db:
            names = {row[0] for row in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"accounts", "sessions", "login_attempts", "recovery_codes", "archives"} <= names)

    def test_account_recovery_code_is_one_time_and_password_can_change(self):
        account_id, recovery = self.store.create_account("Dana", "test-only-password")
        self.assertEqual(self.store.account_name(account_id), "Dana")
        self.assertFalse(self.store.change_password(account_id, "wrong", "new-password-123"))
        self.assertTrue(self.store.change_password(account_id, "test-only-password", "new-password-123"))
        self.assertIsNone(self.store.authenticate("Dana", "test-only-password"))
        self.assertEqual(self.store.authenticate("Dana", "new-password-123"), account_id)
        self.assertIsNone(self.store.reset_password("Dana", "wrong", "again-password-123"))
        recovered = self.store.reset_password("Dana", recovery, "again-password-123")
        self.assertEqual(recovered[0], account_id)
        self.assertTrue(recovered[1])
        self.assertIsNone(self.store.reset_password("Dana", recovery, "third-password-123"))

    def test_registration_errors_do_not_reveal_account_existence(self):
        self.store.create_account("Alice", "test-only-password")
        with self.assertRaisesRegex(ValueError, "无法注册账户"):
            self.store.create_account("alice", "another-password")

    def test_registration_attempts_are_rate_limited(self):
        for _ in range(self.store.REGISTER_LIMIT):
            self.store.check_and_record_sensitive_attempt("register", "client-1")
        with self.assertRaises(LoginRateLimited):
            self.store.check_and_record_sensitive_attempt("register", "client-1")
        self.store.check_and_record_sensitive_attempt("register", "client-2")

    def test_uid_is_four_digits_persistent_and_requires_explicit_login_mode(self):
        account_id, _ = self.store.create_account("Alice", "four")
        profile = self.store.account_profile(account_id)
        self.assertRegex(profile["uid"], r"^[1-9][0-9]{3}$")
        self.assertEqual(IdentityStore(self.db_path).account_profile(account_id)["uid"], profile["uid"])
        self.assertIsNone(self.store.authenticate(profile["uid"], "four"))
        self.assertIsNone(self.store.authenticate(profile["uid"], "wrong", mode="uid"))
        self.assertEqual(self.store.authenticate(profile["uid"], "four", mode="uid"), account_id)

    def test_uid_collision_retries_and_exhaustion_rejects_without_reuse(self):
        with patch("app.infrastructure.identity_store.secrets.randbelow", side_effect=[0, 0, 1]):
            first, _ = self.store.create_account("Alice", "four")
            second, _ = self.store.create_account("Bob", "four")
        self.assertEqual(self.store.account_profile(first)["uid"], "1000")
        self.assertEqual(self.store.account_profile(second)["uid"], "1001")
        with sqlite3.connect(self.db_path) as db:
            db.executemany("INSERT OR IGNORE INTO allocated_uids(uid) VALUES (?)", ((str(i),) for i in range(1000, 10000)))
        with self.assertRaisesRegex(ValueError, "UID 已用尽"):
            self.store.create_account("Carol", "four")

    def test_legacy_migration_preserves_ids_sessions_and_marks_nickname_conflict(self):
        first, _ = self.store.create_account("Alice", "four")
        second, _ = self.store.create_account("Bob", "four")
        token, _ = self.store.issue_session(account_id=first)
        with sqlite3.connect(self.db_path) as db:
            db.execute("UPDATE accounts SET uid = NULL, nickname = 'Ａ', nickname_key = NULL WHERE id = ?", (first,))
            db.execute("UPDATE accounts SET uid = NULL, nickname = 'a', nickname_key = NULL WHERE id = ?", (second,))
        reopened = IdentityStore(self.db_path)
        self.assertNotEqual(reopened.account_profile(first)["uid"], reopened.account_profile(second)["uid"])
        self.assertEqual(reopened.resolve_session(token).account_id, first)
        self.assertTrue(reopened.account_profile(first)["nickname_conflict"])
        self.assertTrue(reopened.account_profile(second)["nickname_conflict"])

    def test_pre_uid_sqlite_schema_is_upgraded_without_changing_legacy_nickname(self):
        legacy_path = Path(self.temp.name) / "legacy.sqlite3"
        with sqlite3.connect(legacy_path) as db:
            db.execute("CREATE TABLE accounts (id TEXT PRIMARY KEY, username TEXT NOT NULL, "
                       "username_key TEXT NOT NULL UNIQUE, password_hash TEXT NOT NULL, recovery_digest TEXT NOT NULL)")
            db.execute("CREATE TABLE login_attempts (username_key TEXT NOT NULL, attempted_at REAL NOT NULL)")
            db.execute("INSERT INTO accounts VALUES (?, ?, ?, ?, ?)",
                       ("old-id", "LongLegacyName", "longlegacyname", self.store.password_hasher.hash("four"), "digest"))
        migrated = IdentityStore(legacy_path)
        profile = migrated.account_profile("old-id")
        self.assertEqual(profile["nickname"], "LongLegacyName")
        self.assertRegex(profile["uid"], r"^[1-9][0-9]{3}$")
        self.assertEqual(migrated.authenticate("LongLegacyName", "four"), "old-id")
        self.assertEqual(IdentityStore(legacy_path).account_profile("old-id")["uid"], profile["uid"])

    def test_password_bounds_apply_to_registration_change_and_recovery(self):
        with self.assertRaises(ValueError):
            self.store.create_account("Alice", "abc")
        account_id, recovery = self.store.create_account("Alice", "abcd")
        self.assertTrue(self.store.change_password(account_id, "abcd", "a" * 128))
        with self.assertRaises(ValueError):
            self.store.change_password(account_id, "a" * 128, "a" * 129)
        with self.assertRaises(ValueError):
            self.store.reset_password("Alice", recovery, "abc")

    def test_nickname_counts_graphemes_and_reserves_nfkc_casefold_names(self):
        first, _ = self.store.create_account("Alice", "four", nickname="👩‍👩‍👧‍👦Ab中文123")
        self.assertEqual(self.store.account_profile(first)["nickname"], "👩‍👩‍👧‍👦Ab中文123")
        with self.assertRaisesRegex(ValueError, "8"):
            self.store.change_nickname(first, "👩‍👩‍👧‍👦Ab中文1234")
        with self.assertRaises(ValueError):
            self.store.change_nickname(first, "  ")
        second, _ = self.store.create_account("Bob", "four", nickname="Ａ")
        with self.assertRaisesRegex(ValueError, "昵称已被使用"):
            self.store.change_nickname(first, "a")
        self.assertEqual(self.store.account_profile(second)["nickname"], "Ａ")

    def test_login_rate_limits_by_source_and_identifier(self):
        self.store.create_account("Alice", "four")
        self.store.create_account("Bob", "four")
        for _ in range(self.store.LOGIN_LIMIT):
            self.assertIsNone(self.store.authenticate("Alice", "wrong", client_key="remote", now=1000))
        with self.assertRaises(LoginRateLimited):
            self.store.authenticate("Bob", "four", client_key="remote", now=1001)

    def test_deferred_runtime_store_does_not_migrate_on_module_import(self):
        from app.application.runtime import DeferredIdentityStore
        deferred_path = Path(self.temp.name) / "deferred.sqlite3"
        store = DeferredIdentityStore(deferred_path)
        self.assertFalse(deferred_path.exists())
        self.assertIsNone(store.account_name("missing"))
        self.assertTrue(deferred_path.exists())


if __name__ == "__main__":
    unittest.main()
