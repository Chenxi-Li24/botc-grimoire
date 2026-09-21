"""Single-table process lifetime dependencies."""

import os
from pathlib import Path

from ..game import GameManager
from ..infrastructure.identity_store import IdentityStore
from .realtime import Hub

game = GameManager()
hub = Hub(game)
identity_store = IdentityStore(Path(os.environ.get("BOTC_IDENTITY_DB", Path(__file__).resolve().parents[2] / "data" / "accounts.sqlite3")))
