"""Guest entry and optional private account/session endpoints."""

import os
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel

from ..application import runtime
from ..infrastructure.identity_store import LoginRateLimited
from .dependencies import optional_session, require_session, resolve_participant, validate_origin
from .schemas_legacy import JoinBody

router = APIRouter()
COOKIE_AGE = 30 * 24 * 60 * 60


class Credentials(BaseModel):
    username: str
    password: str


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class PasswordReset(BaseModel):
    username: str
    recovery_code: str
    new_password: str


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        "botc_session", token, httponly=True, samesite="lax", path="/",
        max_age=COOKIE_AGE, secure=os.environ.get("BOTC_SECURE_COOKIE") == "1",
    )


def _check_write(request: Request) -> None:
    session = optional_session(request)
    if session is None:
        validate_origin(request)
    else:
        require_session(request)


@router.get("/api/session")
def current_session(request: Request) -> dict[str, Any]:
    session = require_session(request)
    game = runtime.game
    if session.account_id is None and session.game_id != game.game_id:
        raise HTTPException(status_code=401, detail="本局身份已失效")
    return {
        "account": runtime.identity_store.account_name(session.account_id) if session.account_id else None,
        "player_id": resolve_participant(game, session),
        "csrf_token": session.csrf,
    }


@router.post("/api/join")
async def join(body: JoinBody, request: Request, response: Response) -> dict[str, str]:
    _check_write(request)
    game = runtime.game
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="请输入名字")
    if body.room_code != game.room_code:
        raise HTTPException(status_code=400, detail="房间号错误")
    session = optional_session(request)
    player_id = resolve_participant(game, session) if session else None
    if player_id is None:
        player = game.add_player(body.name)
        if session and session.account_id:
            player.account_id = session.account_id
            game.save()
        player_id = player.id
        await runtime.hub.push_all()
    if session is None or session.account_id is None:
        if session:
            runtime.identity_store.revoke_session(request.cookies["botc_session"])
        token, _ = runtime.identity_store.issue_session(player_id=player_id, game_id=game.game_id)
        set_session_cookie(response, token)
    return {"player_id": player_id}


@router.post("/api/account/register")
def register(body: Credentials, request: Request, response: Response) -> dict[str, str]:
    _check_write(request)
    old = optional_session(request)
    if old and old.account_id:
        raise HTTPException(status_code=409, detail="请先退出当前账户")
    player_id = resolve_participant(runtime.game, old) if old else None
    try:
        account_id, recovery_code = runtime.identity_store.create_account(body.username, body.password)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if player_id:
        player = runtime.game.players[player_id]
        if player.account_id:
            raise HTTPException(status_code=409, detail="该参与者已有账户")
        player.account_id = account_id
        runtime.game.save()
    if old:
        runtime.identity_store.revoke_session(request.cookies["botc_session"])
    token, _ = runtime.identity_store.issue_session(account_id=account_id)
    set_session_cookie(response, token)
    return {"account_id": account_id, "recovery_code": recovery_code}


@router.post("/api/account/login")
def login(body: Credentials, request: Request, response: Response) -> dict[str, bool]:
    _check_write(request)
    try:
        account_id = runtime.identity_store.authenticate(body.username, body.password)
    except LoginRateLimited as exc:
        raise HTTPException(status_code=429, detail="登录尝试过于频繁") from exc
    if account_id is None:
        raise HTTPException(status_code=401, detail="用户名或密码错误")
    existing = optional_session(request)
    if existing:
        guest_id = resolve_participant(runtime.game, existing)
        linked = next((p.id for p in runtime.game.players.values() if p.account_id == account_id), None)
        if guest_id and linked and guest_id != linked:
            raise HTTPException(status_code=409, detail="当前设备已有其他座位，请先退出")
        if guest_id and not linked:
            runtime.game.players[guest_id].account_id = account_id
            runtime.game.save()
        runtime.identity_store.revoke_session(request.cookies["botc_session"])
    token, _ = runtime.identity_store.issue_session(account_id=account_id)
    set_session_cookie(response, token)
    return {"ok": True}


@router.post("/api/account/logout")
def logout(request: Request, response: Response) -> dict[str, bool]:
    require_session(request)
    runtime.identity_store.revoke_session(request.cookies["botc_session"])
    response.delete_cookie("botc_session", path="/")
    return {"ok": True}


@router.post("/api/account/logout-all")
def logout_all(request: Request, response: Response) -> dict[str, bool]:
    session = require_session(request)
    if not session.account_id:
        raise HTTPException(status_code=403, detail="需要账户")
    runtime.identity_store.revoke_account_sessions(session.account_id)
    response.delete_cookie("botc_session", path="/")
    return {"ok": True}


@router.post("/api/account/change-password")
def change_password(body: PasswordChange, request: Request) -> dict[str, bool]:
    session = require_session(request)
    if not session.account_id:
        raise HTTPException(status_code=403, detail="需要账户")
    if not runtime.identity_store.change_password(session.account_id, body.old_password, body.new_password):
        raise HTTPException(status_code=401, detail="原密码错误")
    return {"ok": True}


@router.post("/api/account/reset-password")
def reset_password(body: PasswordReset, request: Request, response: Response) -> dict[str, Any]:
    _check_write(request)
    recovered = runtime.identity_store.reset_password(body.username, body.recovery_code, body.new_password)
    if not recovered:
        raise HTTPException(status_code=401, detail="账户或恢复码错误")
    account_id, recovery_code = recovered
    token, _ = runtime.identity_store.issue_session(account_id=account_id)
    set_session_cookie(response, token)
    return {"ok": True, "recovery_code": recovery_code}
