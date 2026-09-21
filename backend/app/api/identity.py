"""Guest entry and optional private account/session endpoints."""

import os
from io import BytesIO
from typing import Any

from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel
from PIL import Image, ImageOps, UnidentifiedImageError

from ..application import runtime
from ..application.identity import nickname_key, username_key, validate_nickname
from ..infrastructure.identity_store import LoginRateLimited
from .dependencies import optional_session, require_session, resolve_participant, validate_origin
from .schemas_legacy import JoinBody

router = APIRouter()
COOKIE_AGE = 30 * 24 * 60 * 60


class Credentials(BaseModel):
    username: str
    password: str
    nickname: str | None = None
    mode: str = "username"


class NicknameChange(BaseModel):
    nickname: str


class PasswordChange(BaseModel):
    old_password: str
    new_password: str


class PasswordReset(BaseModel):
    username: str
    recovery_code: str
    new_password: str


class ParticipantRecovery(BaseModel):
    room_code: str
    code: str


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        "botc_session", token, httponly=True, samesite="lax", path="/",
        max_age=COOKIE_AGE, secure=os.environ.get("BOTC_SECURE_COOKIE") == "1",
    )


def _check_write(request: Request) -> None:
    session = optional_session(request)
    if session is None:
        validate_origin(request)
    elif session.account_id is None and resolve_participant(runtime.game, session) is None:
        # A cookie from an earlier game is not a current participant session.
        # Retire it, then treat this as an origin-checked anonymous write.
        runtime.identity_store.revoke_session(request.cookies["botc_session"])
        validate_origin(request)
    else:
        require_session(request)


def _account_id(request: Request) -> str:
    account_id = require_session(request).account_id
    if not account_id:
        raise HTTPException(status_code=403, detail="需要账户")
    return account_id


def _name_taken(game, name: str, *, except_player_id: str | None = None) -> bool:
    key = nickname_key(name)
    return any(p.id != except_player_id and nickname_key(p.name) == key for p in game.players.values())


@router.get("/api/session")
def current_session(request: Request) -> dict[str, Any]:
    session = require_session(request)
    game = runtime.game
    player_id = resolve_participant(game, session)
    if session.account_id is None and player_id is None:
        raise HTTPException(status_code=401, detail="本局身份已失效")
    return {
        "account": runtime.identity_store.account_name(session.account_id) if session.account_id else None,
        "player_id": player_id,
        "csrf_token": session.csrf,
    }


@router.post("/api/join")
async def join(body: JoinBody, request: Request, response: Response) -> dict[str, str]:
    _check_write(request)
    game = runtime.game
    if body.room_code != game.room_code:
        raise HTTPException(status_code=400, detail="房间号错误")
    session = optional_session(request)
    player_id = resolve_participant(game, session) if session else None
    if player_id is None:
        if session and session.account_id:
            profile = runtime.identity_store.account_profile(session.account_id)
            clean_name = profile["nickname"]
        else:
            try:
                clean_name, _ = validate_nickname(body.name)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        if _name_taken(game, clean_name):
            raise HTTPException(status_code=409, detail="昵称已被使用，请重新选择")
        player = game.add_player(clean_name)
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
    if player_id and runtime.game.players[player_id].account_id:
        raise HTTPException(status_code=409, detail="该参与者已有账户")
    nickname = body.nickname if body.nickname is not None else (
        runtime.game.players[player_id].name if player_id else body.username
    )
    if _name_taken(runtime.game, nickname, except_player_id=player_id):
        raise HTTPException(status_code=409, detail="昵称已被使用，请重新选择")
    client_key = request.client.host if request.client else "unknown"
    try:
        runtime.identity_store.check_and_record_sensitive_attempt("register", client_key)
        account_id, recovery_code = runtime.identity_store.create_account(body.username, body.password, nickname)
    except LoginRateLimited as exc:
        raise HTTPException(status_code=429, detail="注册尝试过于频繁") from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if player_id:
        player = runtime.game.players[player_id]
        player.account_id = account_id
        player.name = runtime.identity_store.account_profile(account_id)["nickname"]
        runtime.game.save()
    if old:
        runtime.identity_store.revoke_session(request.cookies["botc_session"])
    token, _ = runtime.identity_store.issue_session(account_id=account_id)
    set_session_cookie(response, token)
    return {"account_id": account_id, "uid": runtime.identity_store.account_profile(account_id)["uid"],
            "recovery_code": recovery_code}


@router.post("/api/account/login")
def login(body: Credentials, request: Request, response: Response) -> dict[str, bool]:
    _check_write(request)
    if body.mode not in {"username", "uid"}:
        raise HTTPException(status_code=400, detail="登录方式无效")
    try:
        client_key = request.client.host if request.client else "unknown"
        account_id = runtime.identity_store.authenticate(body.username, body.password,
                                                          mode=body.mode, client_key=client_key)
    except LoginRateLimited as exc:
        raise HTTPException(status_code=429, detail="登录尝试过于频繁") from exc
    if account_id is None:
        raise HTTPException(status_code=401, detail="账户或密码错误")
    existing = optional_session(request)
    if existing:
        if existing.account_id and existing.account_id != account_id:
            raise HTTPException(status_code=409, detail="请先退出当前账户再切换")
        guest_id = resolve_participant(runtime.game, existing)
        linked = next((p.id for p in runtime.game.players.values() if p.account_id == account_id), None)
        if guest_id and linked and guest_id != linked:
            raise HTTPException(status_code=409, detail="当前设备已有其他座位，请先退出")
        if existing.account_id is None and guest_id and not linked:
            player = runtime.game.players[guest_id]
            display = runtime.identity_store.account_profile(account_id)["nickname"]
            if _name_taken(runtime.game, display, except_player_id=guest_id):
                raise HTTPException(status_code=409, detail="本局昵称已被使用，请先选择其他座位")
            player.account_id = account_id
            player.name = display
            runtime.game.save()
        runtime.identity_store.revoke_session(request.cookies["botc_session"])
    token, _ = runtime.identity_store.issue_session(account_id=account_id)
    set_session_cookie(response, token)
    return {"ok": True}


@router.get("/api/account/profile")
def account_profile(request: Request) -> dict[str, Any]:
    account_id = _account_id(request)
    profile = runtime.identity_store.account_profile(account_id)
    return {**profile, "avatar_url": "/api/account/avatar"}


@router.post("/api/account/nickname")
async def change_nickname(body: NicknameChange, request: Request) -> dict[str, str]:
    account_id = _account_id(request)
    player = next((p for p in runtime.game.players.values() if p.account_id == account_id), None)
    if _name_taken(runtime.game, body.nickname, except_player_id=player.id if player else None):
        raise HTTPException(status_code=409, detail="本局昵称已被使用，请重新选择")
    try:
        nickname = runtime.identity_store.change_nickname(account_id, body.nickname)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    if player:
        player.name = nickname
        runtime.game.save()
        await runtime.hub.push_all()
    return {"nickname": nickname}


@router.put("/api/account/avatar")
async def upload_avatar(request: Request) -> dict[str, bool]:
    account_id = _account_id(request)
    raw = await request.body()
    if len(raw) > 2 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="头像不能超过 2 MiB")
    try:
        with Image.open(BytesIO(raw)) as image:
            if image.format not in {"PNG", "JPEG", "WEBP"} or image.width * image.height > 16_000_000:
                raise ValueError("不支持的头像图片")
            image.load()
            normalized = ImageOps.exif_transpose(image).convert("RGBA")
            normalized.thumbnail((512, 512))
            output = BytesIO()
            normalized.save(output, format="PNG")
    except (UnidentifiedImageError, OSError, ValueError, Image.DecompressionBombError) as exc:
        raise HTTPException(status_code=400, detail="仅支持 PNG、JPEG 或 WebP 图片") from exc
    runtime.identity_store.set_avatar(account_id, output.getvalue())
    await runtime.hub.push_all()
    return {"ok": True}


@router.get("/api/account/avatar")
def own_avatar(request: Request) -> Response:
    account_id = _account_id(request)
    png = runtime.identity_store.avatar(account_id)
    if png is None:
        raise HTTPException(status_code=404, detail="尚未设置头像")
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.get("/api/avatar/{player_id}")
def player_avatar(player_id: str) -> Response:
    player = runtime.game.players.get(player_id)
    png = runtime.identity_store.avatar(player.account_id) if player and player.account_id else None
    if png is None:
        raise HTTPException(status_code=404, detail="没有头像")
    return Response(content=png, media_type="image/png", headers={"Cache-Control": "no-store"})


@router.post("/api/account/logout")
async def logout(request: Request, response: Response) -> dict[str, bool]:
    require_session(request)
    runtime.identity_store.revoke_session(request.cookies["botc_session"])
    await runtime.hub.push_all()
    response.delete_cookie("botc_session", path="/")
    return {"ok": True}


@router.post("/api/account/logout-all")
async def logout_all(request: Request, response: Response) -> dict[str, bool]:
    session = require_session(request)
    if not session.account_id:
        raise HTTPException(status_code=403, detail="需要账户")
    runtime.identity_store.revoke_account_sessions(session.account_id)
    await runtime.hub.push_all()
    response.delete_cookie("botc_session", path="/")
    return {"ok": True}


@router.post("/api/account/change-password")
def change_password(body: PasswordChange, request: Request) -> dict[str, bool]:
    session = require_session(request)
    if not session.account_id:
        raise HTTPException(status_code=403, detail="需要账户")
    try:
        changed = runtime.identity_store.change_password(session.account_id, body.old_password, body.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not changed:
        raise HTTPException(status_code=401, detail="原密码错误")
    return {"ok": True}


@router.post("/api/account/reset-password")
async def reset_password(body: PasswordReset, request: Request, response: Response) -> dict[str, Any]:
    _check_write(request)
    client_key = request.client.host if request.client else "unknown"
    try:
        runtime.identity_store.check_and_record_sensitive_attempt(
            "reset", f"{client_key}:{username_key(body.username)}"
        )
    except LoginRateLimited as exc:
        raise HTTPException(status_code=429, detail="找回尝试过于频繁") from exc
    try:
        recovered = runtime.identity_store.reset_password(body.username, body.recovery_code, body.new_password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not recovered:
        raise HTTPException(status_code=401, detail="账户或恢复码错误")
    account_id, recovery_code = recovered
    old_token = request.cookies.get("botc_session")
    if old_token:
        runtime.identity_store.revoke_session(old_token)
    await runtime.hub.push_all()
    token, _ = runtime.identity_store.issue_session(account_id=account_id)
    set_session_cookie(response, token)
    return {"ok": True, "recovery_code": recovery_code}


@router.post("/api/recover-participant")
def recover_participant(body: ParticipantRecovery, request: Request, response: Response) -> dict[str, str]:
    _check_write(request)
    game = runtime.game
    client_key = request.client.host if request.client else "unknown"
    try:
        runtime.identity_store.check_recovery_limit(client_key)
    except LoginRateLimited as exc:
        raise HTTPException(status_code=429, detail="续接尝试过于频繁") from exc
    if body.room_code != game.room_code:
        runtime.identity_store.record_recovery_failure(client_key)
        raise HTTPException(status_code=400, detail="房间号错误")
    result = runtime.identity_store.redeem_participant_recovery_session(game.game_id, body.code)
    if result is None:
        runtime.identity_store.record_recovery_failure(client_key)
        raise HTTPException(status_code=401, detail="续接码无效或已过期")
    player_id, token, _ = result
    if player_id not in game.players or game.players[player_id].account_id is not None:
        runtime.identity_store.revoke_session(token)
        raise HTTPException(status_code=403, detail="原身份已不存在")
    old_token = request.cookies.get("botc_session")
    if old_token:
        runtime.identity_store.revoke_session(old_token)
    set_session_cookie(response, token)
    return {"player_id": player_id}


@router.get("/api/account/history")
def account_history(request: Request) -> list[dict[str, Any]]:
    session = require_session(request)
    if session.account_id is None:
        raise HTTPException(status_code=403, detail="需要账户")
    return runtime.identity_store.list_archives(session.account_id)
