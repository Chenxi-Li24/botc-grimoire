"""Identity primitives shared by the SQLite store and API layer."""

import hashlib
import unicodedata
from dataclasses import dataclass


def username_key(name: str) -> str:
    return unicodedata.normalize("NFKC", name.strip()).casefold()


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Session:
    account_id: str | None
    player_id: str | None
    game_id: str | None
    csrf: str
    expires_at: float
