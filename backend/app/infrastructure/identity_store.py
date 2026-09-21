"""Persistent private identity data, kept separate from the public game save."""

import secrets
import sqlite3
import time
import json
from pathlib import Path

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.application.identity import (
    Session, token_digest, username_key, validate_nickname, validate_password,
)


class LoginRateLimited(Exception):
    """A username has exceeded the allowed login attempts."""


class IdentityStore:
    SESSION_TTL = 30 * 24 * 60 * 60
    LOGIN_WINDOW = 15 * 60
    LOGIN_LIMIT = 5
    REGISTER_LIMIT = 20
    RESET_LIMIT = 5

    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.password_hasher = PasswordHasher()
        with self._connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS accounts (
                    id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    username_key TEXT NOT NULL UNIQUE,
                    password_hash TEXT NOT NULL,
                    recovery_digest TEXT NOT NULL,
                    uid TEXT UNIQUE,
                    nickname TEXT,
                    nickname_key TEXT,
                    nickname_conflict INTEGER NOT NULL DEFAULT 0,
                    avatar_png BLOB
                );
                CREATE TABLE IF NOT EXISTS allocated_uids (
                    uid TEXT PRIMARY KEY
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    token_digest TEXT PRIMARY KEY,
                    account_id TEXT,
                    player_id TEXT,
                    game_id TEXT,
                    csrf TEXT NOT NULL,
                    expires_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS sessions_account ON sessions(account_id);
                CREATE TABLE IF NOT EXISTS login_attempts (
                    username_key TEXT NOT NULL,
                    client_key TEXT,
                    attempted_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS attempts_name_time ON login_attempts(username_key, attempted_at);
                CREATE TABLE IF NOT EXISTS recovery_attempts (
                    client_key TEXT NOT NULL,
                    attempted_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS recovery_attempts_client_time ON recovery_attempts(client_key, attempted_at);
                CREATE TABLE IF NOT EXISTS sensitive_attempts (
                    kind TEXT NOT NULL,
                    client_key TEXT NOT NULL,
                    attempted_at REAL NOT NULL
                );
                CREATE INDEX IF NOT EXISTS sensitive_attempts_kind_client_time
                    ON sensitive_attempts(kind, client_key, attempted_at);
                CREATE TABLE IF NOT EXISTS recovery_codes (
                    code_digest TEXT PRIMARY KEY,
                    game_id TEXT NOT NULL,
                    player_id TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    consumed_at REAL
                );
                CREATE TABLE IF NOT EXISTS archives (
                    game_id TEXT NOT NULL,
                    account_id TEXT NOT NULL,
                    record_json TEXT NOT NULL,
                    PRIMARY KEY(game_id, account_id)
                );
            """)
            self._migrate_accounts(db)

    @classmethod
    def _allocate_uid(cls, db: sqlite3.Connection) -> str:
        used = db.execute("SELECT COUNT(*) FROM allocated_uids").fetchone()[0]
        if used >= 9000:
            raise ValueError("UID 已用尽，暂时无法注册")
        for _ in range(32):
            uid = str(1000 + secrets.randbelow(9000))
            if db.execute("INSERT OR IGNORE INTO allocated_uids(uid) VALUES (?)", (uid,)).rowcount:
                return uid
        # The last free number remains reachable even when random draws collide.
        start = secrets.randbelow(9000)
        for offset in range(9000):
            uid = str(1000 + ((start + offset) % 9000))
            if db.execute("INSERT OR IGNORE INTO allocated_uids(uid) VALUES (?)", (uid,)).rowcount:
                return uid
        raise ValueError("UID 已用尽，暂时无法注册")

    @classmethod
    def _migrate_accounts(cls, db: sqlite3.Connection) -> None:
        columns = {row[1] for row in db.execute("PRAGMA table_info(accounts)")}
        for column, definition in (
            ("uid", "TEXT"), ("nickname", "TEXT"), ("nickname_key", "TEXT"),
            ("nickname_conflict", "INTEGER NOT NULL DEFAULT 0"), ("avatar_png", "BLOB"),
        ):
            if column not in columns:
                db.execute(f"ALTER TABLE accounts ADD COLUMN {column} {definition}")
        attempts_columns = {row[1] for row in db.execute("PRAGMA table_info(login_attempts)")}
        if "client_key" not in attempts_columns:
            db.execute("ALTER TABLE login_attempts ADD COLUMN client_key TEXT")
        db.execute("CREATE INDEX IF NOT EXISTS attempts_client_time ON login_attempts(client_key, attempted_at)")
        db.execute("CREATE UNIQUE INDEX IF NOT EXISTS accounts_uid_unique ON accounts(uid)")
        rows = db.execute("SELECT id, username, uid, nickname, nickname_key FROM accounts").fetchall()
        for row in rows:
            if row["uid"]:
                db.execute("INSERT OR IGNORE INTO allocated_uids(uid) VALUES (?)", (row["uid"],))
        for row in rows:
            if not row["uid"]:
                db.execute("UPDATE accounts SET uid = ? WHERE id = ?", (cls._allocate_uid(db), row["id"]))
            nickname = row["nickname"] if row["nickname"] is not None else row["username"]
            key = username_key(nickname)
            if row["nickname"] is None or row["nickname_key"] != key:
                db.execute("UPDATE accounts SET nickname = ?, nickname_key = ? WHERE id = ?", (nickname, key, row["id"]))
        db.execute("UPDATE accounts SET nickname_conflict = 0")
        db.execute("UPDATE accounts SET nickname_conflict = 1 WHERE nickname_key IN "
                   "(SELECT nickname_key FROM accounts GROUP BY nickname_key HAVING COUNT(*) > 1)")

    def _connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA busy_timeout = 5000")
        return db

    def create_account(self, username: str, password: str, nickname: str | None = None) -> tuple[str, str]:
        key = username_key(username)
        if not key or len(key) > 64:
            raise ValueError("用户名不符合要求")
        validate_password(password)
        display, display_key = validate_nickname(username if nickname is None else nickname)
        account_id = secrets.token_hex(16)
        recovery_code = secrets.token_urlsafe(32)
        password_hash = self.password_hasher.hash(password)
        try:
            with self._connect() as db:
                db.execute("BEGIN IMMEDIATE")
                if db.execute("SELECT 1 FROM accounts WHERE username_key = ?", (key,)).fetchone():
                    raise ValueError("无法注册账户，请检查用户名或稍后重试")
                if db.execute("SELECT 1 FROM accounts WHERE nickname_key = ?", (display_key,)).fetchone():
                    raise ValueError("昵称已被使用，请重新选择")
                uid = self._allocate_uid(db)
                db.execute(
                    "INSERT INTO accounts(id, username, username_key, password_hash, recovery_digest, uid, nickname, nickname_key) "
                    "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (account_id, username.strip(), key, password_hash, token_digest(recovery_code),
                     uid, display, display_key),
                )
        except sqlite3.IntegrityError as exc:
            raise ValueError("无法注册账户，请检查用户名或稍后重试") from exc
        return account_id, recovery_code

    def authenticate(
        self, username: str, password: str, *, mode: str = "username",
        client_key: str | None = None, now: float | None = None,
    ) -> str | None:
        if mode not in {"username", "uid"}:
            raise ValueError("登录方式无效")
        now = time.time() if now is None else now
        key = f"{mode}:{username_key(username) if mode == 'username' else username}"
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM login_attempts WHERE attempted_at <= ?", (now - self.LOGIN_WINDOW,))
            identifier_attempts = db.execute(
                "SELECT COUNT(*) FROM login_attempts WHERE username_key = ?", (key,),
            ).fetchone()[0]
            source_attempts = db.execute(
                "SELECT COUNT(*) FROM login_attempts WHERE client_key = ?", (client_key,),
            ).fetchone()[0] if client_key else 0
            if max(identifier_attempts, source_attempts) >= self.LOGIN_LIMIT:
                raise LoginRateLimited("登录尝试过于频繁")
            account = db.execute(
                f"SELECT id, password_hash FROM accounts WHERE {'username_key' if mode == 'username' else 'uid'} = ?",
                (username_key(username) if mode == "username" else username,),
            ).fetchone()
            if account is not None:
                try:
                    if self.password_hasher.verify(account["password_hash"], password):
                        db.execute("DELETE FROM login_attempts WHERE username_key = ?", (key,))
                        return account["id"]
                except VerifyMismatchError:
                    pass
            db.execute(
                "INSERT INTO login_attempts(username_key, client_key, attempted_at) VALUES (?, ?, ?)",
                (key, client_key, now),
            )
            return None

    def account_profile(self, account_id: str) -> dict | None:
        with self._connect() as db:
            row = db.execute(
                "SELECT uid, username, nickname, nickname_conflict, avatar_png IS NOT NULL AS has_avatar "
                "FROM accounts WHERE id = ?", (account_id,),
            ).fetchone()
        return dict(row) if row else None

    def change_nickname(self, account_id: str, nickname: str) -> str:
        display, key = validate_nickname(nickname)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            if db.execute("SELECT 1 FROM accounts WHERE nickname_key = ? AND id != ?", (key, account_id)).fetchone():
                raise ValueError("昵称已被使用，请重新选择")
            result = db.execute(
                "UPDATE accounts SET nickname = ?, nickname_key = ?, nickname_conflict = 0 WHERE id = ?",
                (display, key, account_id),
            )
            if result.rowcount != 1:
                raise ValueError("账户不存在")
            db.execute("UPDATE accounts SET nickname_conflict = 0 WHERE nickname_key NOT IN "
                       "(SELECT nickname_key FROM accounts GROUP BY nickname_key HAVING COUNT(*) > 1)")
        return display

    def set_avatar(self, account_id: str, png: bytes) -> None:
        with self._connect() as db:
            db.execute("UPDATE accounts SET avatar_png = ? WHERE id = ?", (png, account_id))

    def avatar(self, account_id: str) -> bytes | None:
        with self._connect() as db:
            row = db.execute("SELECT avatar_png FROM accounts WHERE id = ?", (account_id,)).fetchone()
        return row["avatar_png"] if row else None

    def issue_session(
        self,
        account_id: str | None = None,
        player_id: str | None = None,
        game_id: str | None = None,
        *,
        now: float | None = None,
        ttl: float = SESSION_TTL,
    ) -> tuple[str, str]:
        now = time.time() if now is None else now
        token = secrets.token_urlsafe(32)
        csrf = secrets.token_urlsafe(32)
        with self._connect() as db:
            db.execute(
                "INSERT INTO sessions(token_digest, account_id, player_id, game_id, csrf, expires_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (token_digest(token), account_id, player_id, game_id, csrf, now + ttl),
            )
        return token, csrf

    def resolve_session(self, token: str, *, now: float | None = None) -> Session | None:
        now = time.time() if now is None else now
        with self._connect() as db:
            row = db.execute(
                "SELECT account_id, player_id, game_id, csrf, expires_at "
                "FROM sessions WHERE token_digest = ? AND expires_at > ?",
                (token_digest(token), now),
            ).fetchone()
        return Session(**dict(row)) if row else None

    def revoke_session(self, token: str) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM sessions WHERE token_digest = ?", (token_digest(token),))

    def revoke_account_sessions(self, account_id: str) -> None:
        with self._connect() as db:
            db.execute("DELETE FROM sessions WHERE account_id = ?", (account_id,))

    def account_name(self, account_id: str) -> str | None:
        with self._connect() as db:
            row = db.execute("SELECT username FROM accounts WHERE id = ?", (account_id,)).fetchone()
        return row["username"] if row else None

    def change_password(self, account_id: str, old_password: str, new_password: str) -> bool:
        validate_password(new_password)
        with self._connect() as db:
            row = db.execute("SELECT password_hash FROM accounts WHERE id = ?", (account_id,)).fetchone()
            if row is None:
                return False
            try:
                self.password_hasher.verify(row["password_hash"], old_password)
            except VerifyMismatchError:
                return False
            db.execute(
                "UPDATE accounts SET password_hash = ? WHERE id = ?",
                (self.password_hasher.hash(new_password), account_id),
            )
        return True

    def reset_password(
        self, username: str, recovery_code: str, new_password: str
    ) -> tuple[str, str] | None:
        validate_password(new_password)
        key = username_key(username)
        digest = token_digest(recovery_code)
        with self._connect() as db:
            account = db.execute(
                "SELECT id FROM accounts WHERE username_key = ? AND recovery_digest = ?",
                (key, digest),
            ).fetchone()
        if account is None:
            return None
        new_code = secrets.token_urlsafe(32)
        new_hash = self.password_hasher.hash(new_password)
        with self._connect() as db:
            result = db.execute(
                "UPDATE accounts SET password_hash = ?, recovery_digest = ? "
                "WHERE username_key = ? AND recovery_digest = ?",
                (new_hash, token_digest(new_code), key, digest),
            )
            if result.rowcount != 1:
                return None
            db.execute("DELETE FROM sessions WHERE account_id = ?", (account["id"],))
        return account["id"], new_code

    def check_and_record_sensitive_attempt(
        self, kind: str, client_key: str, *, now: float | None = None
    ) -> None:
        if kind not in {"register", "reset"}:
            raise ValueError("Unknown sensitive operation")
        now = time.time() if now is None else now
        limit = self.REGISTER_LIMIT if kind == "register" else self.RESET_LIMIT
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("DELETE FROM sensitive_attempts WHERE attempted_at <= ?", (now - self.LOGIN_WINDOW,))
            count = db.execute(
                "SELECT COUNT(*) FROM sensitive_attempts WHERE kind = ? AND client_key = ? AND attempted_at > ?",
                (kind, client_key, now - self.LOGIN_WINDOW),
            ).fetchone()[0]
            if count >= limit:
                raise LoginRateLimited("尝试过于频繁")
            db.execute(
                "INSERT INTO sensitive_attempts(kind, client_key, attempted_at) VALUES (?, ?, ?)",
                (kind, client_key, now),
            )

    def issue_participant_recovery(
        self, game_id: str, player_id: str, *, now: float | None = None
    ) -> str:
        now = time.time() if now is None else now
        code = secrets.token_urlsafe(24)
        with self._connect() as db:
            db.execute(
                "DELETE FROM recovery_codes WHERE game_id = ? AND player_id = ?",
                (game_id, player_id),
            )
            db.execute(
                "INSERT INTO recovery_codes(code_digest, game_id, player_id, expires_at, consumed_at) "
                "VALUES (?, ?, ?, ?, NULL)",
                (token_digest(code), game_id, player_id, now + 600),
            )
        return code

    @staticmethod
    def _consume_recovery(db: sqlite3.Connection, game_id: str, code: str, now: float) -> str | None:
        digest = token_digest(code)
        row = db.execute(
            "SELECT player_id FROM recovery_codes WHERE code_digest = ? AND game_id = ? "
            "AND consumed_at IS NULL AND expires_at > ?",
            (digest, game_id, now),
        ).fetchone()
        if row is None:
            return None
        result = db.execute(
            "UPDATE recovery_codes SET consumed_at = ? WHERE code_digest = ? "
            "AND consumed_at IS NULL AND expires_at > ?",
            (now, digest, now),
        )
        return row["player_id"] if result.rowcount == 1 else None

    def redeem_participant_recovery(
        self, game_id: str, code: str, *, now: float | None = None
    ) -> str | None:
        now = time.time() if now is None else now
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            return self._consume_recovery(db, game_id, code, now)

    def redeem_participant_recovery_session(
        self, game_id: str, code: str, *, now: float | None = None
    ) -> tuple[str, str, str] | None:
        """Consume a code and issue a guest session in one SQLite transaction."""
        now = time.time() if now is None else now
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            player_id = self._consume_recovery(db, game_id, code, now)
            if player_id is None:
                return None
            token = secrets.token_urlsafe(32)
            csrf = secrets.token_urlsafe(32)
            db.execute(
                "INSERT INTO sessions(token_digest, account_id, player_id, game_id, csrf, expires_at) "
                "VALUES (?, NULL, ?, ?, ?, ?)",
                (token_digest(token), player_id, game_id, csrf, now + self.SESSION_TTL),
            )
        return player_id, token, csrf

    def revoke_guest_sessions(self, game_id: str, player_id: str) -> None:
        with self._connect() as db:
            db.execute(
                "DELETE FROM sessions WHERE game_id = ? AND player_id = ? AND account_id IS NULL",
                (game_id, player_id),
            )

    def check_recovery_limit(self, client_key: str, *, now: float | None = None) -> None:
        now = time.time() if now is None else now
        with self._connect() as db:
            db.execute("DELETE FROM recovery_attempts WHERE attempted_at <= ?", (now - self.LOGIN_WINDOW,))
            count = db.execute(
                "SELECT COUNT(*) FROM recovery_attempts WHERE client_key = ? AND attempted_at > ?",
                (client_key, now - self.LOGIN_WINDOW),
            ).fetchone()[0]
        if count >= self.LOGIN_LIMIT:
            raise LoginRateLimited("续接尝试过于频繁")

    def record_recovery_failure(self, client_key: str, *, now: float | None = None) -> None:
        now = time.time() if now is None else now
        with self._connect() as db:
            db.execute(
                "INSERT INTO recovery_attempts(client_key, attempted_at) VALUES (?, ?)",
                (client_key, now),
            )

    def upsert_archive(self, game_id: str, account_id: str, record: dict) -> None:
        payload = json.dumps(record, ensure_ascii=False, separators=(",", ":"))
        with self._connect() as db:
            db.execute(
                "INSERT INTO archives(game_id, account_id, record_json) VALUES (?, ?, ?) "
                "ON CONFLICT(game_id, account_id) DO UPDATE SET record_json = excluded.record_json",
                (game_id, account_id, payload),
            )

    def list_archives(self, account_id: str) -> list[dict]:
        with self._connect() as db:
            rows = db.execute(
                "SELECT record_json FROM archives WHERE account_id = ? ORDER BY rowid DESC",
                (account_id,),
            ).fetchall()
        return [json.loads(row["record_json"]) for row in rows]
