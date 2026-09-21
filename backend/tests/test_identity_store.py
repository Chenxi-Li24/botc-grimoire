import sqlite3
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
