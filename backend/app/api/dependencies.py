"""Storyteller authentication shared by HTTP and WebSocket routes."""

import os
from fastapi import Header, HTTPException

STORYTELLER_PASSWORD = os.environ.get("STORYTELLER_PASSWORD", "grimoire")

def require_storyteller(x_password: str = Header(default="", alias="X-Storyteller-Password")) -> None:
    if x_password != STORYTELLER_PASSWORD:
        raise HTTPException(status_code=401, detail="说书人密码错误")

