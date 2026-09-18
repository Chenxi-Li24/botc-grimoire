"""临时启动器:8001 端口跑新代码,SAVE_PATH 指向固定临时目录——绝不碰线上局(8000/真实存档)。

路径固定(非每次 mkdtemp)才能测「重启后存档恢复」。
用法:cd backend && .venv/bin/python tools/run_test_server.py
"""

import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import app.game as G  # noqa: E402

G.SAVE_PATH = Path(os.environ.get(
    "TEST_SAVE_PATH",
    str(Path(tempfile.gettempdir()) / "botc-e2e" / "game.json")))
print(f"SAVE_PATH -> {G.SAVE_PATH}", flush=True)

import uvicorn  # noqa: E402

uvicorn.run("app.main:app", host="127.0.0.1", port=8001, log_level="warning")
