"""Storyteller authentication shared by HTTP and WebSocket routes."""

import os
from urllib.parse import urlsplit

from fastapi import Header, HTTPException, Request

from ..application import runtime
from ..application.identity import Session

STORYTELLER_PASSWORD = os.environ.get("STORYTELLER_PASSWORD", "grimoire")

def require_storyteller(x_password: str = Header(default="", alias="X-Storyteller-Password")) -> None:
    if x_password != STORYTELLER_PASSWORD:
        raise HTTPException(status_code=401, detail="说书人密码错误")


def validate_origin(request: Request) -> None:
    """Reject cross-site writes even when the browser carries our cookie."""
    origin = request.headers.get("origin", "")
    parsed = urlsplit(origin)
    expected = urlsplit(str(request.base_url))
    if not origin or (parsed.scheme, parsed.netloc) != (expected.scheme, expected.netloc):
        raise HTTPException(status_code=403, detail="请求来源无效")


def optional_session(request: Request) -> Session | None:
    token = request.cookies.get("botc_session")
    return runtime.identity_store.resolve_session(token) if token else None


def require_session(request: Request) -> Session:
    session = optional_session(request)
    if session is None:
        raise HTTPException(status_code=401, detail="请先登录或加入本局")
    if request.method not in {"GET", "HEAD", "OPTIONS"}:
        validate_origin(request)
        if request.headers.get("x-csrf-token") != session.csrf:
            raise HTTPException(status_code=403, detail="安全令牌无效")
    return session


def resolve_participant(game, session: Session) -> str | None:
    if session.account_id:
        return next((p.id for p in game.players.values() if p.account_id == session.account_id), None)
    if session.game_id != game.game_id or session.player_id not in game.players:
        return None
    player = game.players[session.player_id]
    return player.id if player.account_id is None else None


def require_player(request: Request) -> str:
    player_id = resolve_participant(runtime.game, require_session(request))
    if player_id is None:
        raise HTTPException(status_code=403, detail="本局身份已失效")
    return player_id


def require_matching_player(player_id: str, request: Request) -> str:
    actual = require_player(request)
    if actual != player_id:
        raise HTTPException(status_code=403, detail="无权访问该玩家")
    return actual
