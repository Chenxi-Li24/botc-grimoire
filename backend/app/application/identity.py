"""Identity primitives shared by the SQLite store and API layer."""

import hashlib
import unicodedata
from dataclasses import dataclass

import regex


def username_key(name: str) -> str:
    return unicodedata.normalize("NFKC", name.strip()).casefold()


def nickname_key(name: str) -> str:
    return unicodedata.normalize("NFKC", name.strip()).casefold()


def validate_nickname(name: str) -> tuple[str, str]:
    nickname = name.strip()
    if not nickname or len(regex.findall(r"\X", nickname)) > 8:
        raise ValueError("昵称需为 1–8 个可见字符")
    return nickname, nickname_key(nickname)


def validate_password(password: str) -> None:
    if not 4 <= len(password) <= 128:
        raise ValueError("密码需为 4–128 个字符")


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Session:
    account_id: str | None
    player_id: str | None
    game_id: str | None
    csrf: str
    expires_at: float
