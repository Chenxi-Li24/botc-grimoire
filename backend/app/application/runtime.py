"""Single-table process lifetime dependencies."""

import os
import threading
from pathlib import Path

from ..game import GameManager
from ..infrastructure.identity_store import IdentityStore
from .realtime import Hub

game = GameManager()
hub = Hub(game)


class DeferredIdentityStore:
    """Avoid opening or migrating the account DB merely by importing the app."""

    def __init__(self, path: Path):
        self.path = path
        self._store: IdentityStore | None = None
        self._lock = threading.Lock()

    def __getattr__(self, name: str):
        if self._store is None:
            with self._lock:
                if self._store is None:
                    self._store = IdentityStore(self.path)
        return getattr(self._store, name)


identity_store = DeferredIdentityStore(Path(os.environ.get(
    "BOTC_IDENTITY_DB", Path(__file__).resolve().parents[2] / "data" / "accounts.sqlite3"
)))
