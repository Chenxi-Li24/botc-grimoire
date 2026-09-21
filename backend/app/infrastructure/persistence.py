"""Atomic JSON snapshot I/O, independent of game rules and FastAPI."""

import json
import os
from pathlib import Path


def read_snapshot(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_snapshot(path: Path, payload: dict, *, backup_legacy: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    if backup_legacy and path.exists():
        backup = path.with_suffix(".v1.json")
        if not backup.exists():
            backup.write_bytes(path.read_bytes())
    os.replace(temporary, path)
