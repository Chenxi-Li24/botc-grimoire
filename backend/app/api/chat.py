"""Player and storyteller private-chat HTTP endpoints."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from ..application.runtime import game, hub
from .dependencies import require_storyteller
from .schemas_legacy import *

router = APIRouter()

def _player_who(player_id: str) -> int | str:
    """玩家的私聊身份:座位号或旅行者 id。"""
    t = game.traveler_of(player_id)
    if t is not None:
        return t["id"]
    me = game.players[player_id]
    if me.seat is None:
        raise HTTPException(status_code=400, detail="你还没有入座")
    return me.seat



@router.post("/api/chat/create")
async def chat_create(player_id: str, body: ChatCreateBody) -> dict[str, Any]:
    try:
        game.create_chat(_player_who(player_id), body.invitees)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)



@router.post("/api/chat/{cid}/invite")
async def chat_invite(player_id: str, cid: int, body: ChatInviteBody) -> dict[str, Any]:
    try:
        game.respond_invite(_player_who(player_id), cid, body.accept)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)



@router.post("/api/chat/{cid}/request")
async def chat_request(player_id: str, cid: int) -> dict[str, Any]:
    try:
        game.request_join(_player_who(player_id), cid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)



@router.post("/api/chat/{cid}/invite-more")
async def chat_invite_more(player_id: str, cid: int, body: ChatCreateBody) -> dict[str, Any]:
    """私聊进行中,发起者邀请更多玩家加入。"""
    try:
        game.invite_to_chat(_player_who(player_id), cid, body.invitees)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)



@router.post("/api/chat/{cid}/approve")
async def chat_approve(player_id: str, cid: int, body: ChatApproveBody) -> dict[str, Any]:
    try:
        game.approve_request(_player_who(player_id), cid, body.who, body.approve)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)



@router.post("/api/chat/{cid}/send")
async def chat_send(player_id: str, cid: int, body: ChatSendBody) -> dict[str, Any]:
    try:
        game.send_message(_player_who(player_id), cid, body.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)



@router.post("/api/chat/{cid}/leave")
async def chat_leave(player_id: str, cid: int) -> dict[str, Any]:
    try:
        game.leave_chat(_player_who(player_id), cid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)



@router.post("/api/chat/{cid}/close")
async def chat_close(player_id: str, cid: int) -> dict[str, Any]:
    try:
        game.close_chat(_player_who(player_id), cid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)



@router.post("/api/chat-st/{cid}/invite", dependencies=[Depends(require_storyteller)])
async def st_chat_invite(cid: int, body: ChatInviteBody) -> dict[str, Any]:
    try:
        game.respond_invite("st", cid, body.accept)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/chat-st/{cid}/send", dependencies=[Depends(require_storyteller)])
async def st_chat_send(cid: int, body: ChatSendBody) -> dict[str, Any]:
    try:
        game.send_message("st", cid, body.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/chat-st/{cid}/leave", dependencies=[Depends(require_storyteller)])
async def st_chat_leave(cid: int) -> dict[str, Any]:
    try:
        game.leave_chat("st", cid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/chat-st/{cid}/close", dependencies=[Depends(require_storyteller)])
async def st_chat_close(cid: int) -> dict[str, Any]:
    try:
        game.close_chat("st", cid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/chat-st/recall", dependencies=[Depends(require_storyteller)])
async def st_chat_recall() -> dict[str, Any]:
    """说书人召回:关闭全部私聊。"""
    game.recall_chats()
    await hub.push_all()
    return game.storyteller_view()

