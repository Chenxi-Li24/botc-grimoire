"""Player HTTP endpoints; server game state remains authoritative."""

from typing import Any
from fastapi import APIRouter, HTTPException
from ..application.runtime import game, hub
from ..net import get_lan_ip
from ..night.player_actions import submit_player_night_action
from ..night.service import NavigationConflict
from .night import NightCommandError
from .schemas import PlayerNightActionBody
from .schemas_legacy import *

router = APIRouter()

@router.post("/api/join")
async def join(body: JoinBody) -> dict[str, Any]:
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="请输入名字")
    if body.room_code != game.room_code:
        raise HTTPException(status_code=400, detail="房间号错误")
    player = game.add_player(body.name)
    await hub.push_all()
    return {"player_id": player.id}



@router.post("/api/player/{player_id}/sit")
async def sit(player_id: str, body: SitBody) -> dict[str, Any]:
    try:
        game.sit(player_id, body.seat)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)



@router.get("/api/info")
def info() -> dict[str, Any]:
    return {"lan_ip": get_lan_ip(), "status": game.status,
            "script": game.script_id, "player_count": game.player_count}



@router.get("/api/me/{player_id}")
def me(player_id: str) -> dict[str, Any]:
    if player_id not in game.players:
        raise HTTPException(status_code=404, detail="玩家不存在(说书人可能已重置本局)")
    return game.player_view(player_id)



@router.post("/api/player/{player_id}/traveler")
async def join_traveler(player_id: str) -> dict[str, Any]:
    """玩家以旅行者身份加入(开局后任意时刻,不占座位)。"""
    try:
        game.add_traveler(player_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)



@router.post("/api/player/{player_id}/nominate")
async def nominate(player_id: str, body: NomineeBody) -> dict[str, Any]:
    """玩家手机发起提名:提名者必须是本人(存活、今天未提名过、白天、无进行中提名)。"""
    try:
        game.player_nominate(player_id, body.nominee)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)



@router.post("/api/player/{player_id}/vote")
async def vote(player_id: str) -> dict[str, Any]:
    """玩家手机举手/放下:只能投自己(死者举手=交出唯一死票,未结算可收回)。"""
    try:
        game.player_vote(player_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)



@router.post("/api/player/{player_id}/wish")
async def set_wish(player_id: str, body: WishBody) -> dict[str, Any]:
    """许愿(仅大厅):开局前表达愿望——善良/邪恶或自定义文字;空 = 清除。"""
    try:
        game.set_wish(player_id, body.wish)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)



@router.post("/api/player/{player_id}/kill")
async def night_kill(player_id: str, body: KillBody) -> dict[str, Any]:
    """夜晚刀人(仅瓦釜雷鸣):恶魔手机选择目标,天亮自动执行;疯子选择只演戏。"""
    try:
        game.submit_night_kill(player_id, body.seat)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)



@router.post("/api/player/{player_id}/choice")
async def night_choice(player_id: str, body: NightChoiceBody) -> dict[str, Any]:
    """夜晚信息交互(仅瓦釜雷鸣):占卜师/筑梦师等手机选人,说书人看到后电子回复。"""
    try:
        game.submit_night_choice(player_id, body.targets, body.char)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)



@router.post("/api/player/{player_id}/night-action")
async def player_night_action(player_id: str, body: PlayerNightActionBody) -> dict[str, Any]:
    """Submit the current seat-owned action to the canonical night workflow."""
    try:
        submit_player_night_action(game, player_id, body)
    except NavigationConflict as exc:
        raise NightCommandError(exc.code, str(exc), exc.details) from exc
    except ValueError as exc:
        raise NightCommandError("invalid_player_action", str(exc)) from exc
    game.save()
    await hub.push_all()
    return game.player_view(player_id)

