"""Authenticated storyteller commands and legacy night adapters."""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from ..application.runtime import game, hub
from .dependencies import STORYTELLER_PASSWORD, require_storyteller
from .schemas_legacy import *

router = APIRouter()

def deprecated_storyteller_view(replacement: str) -> dict[str, Any]:
    return {
        **game.storyteller_view(),
        "deprecation": {
            "deprecated": True,
            "replacement": replacement,
        },
    }



@router.post("/api/night/transform", dependencies=[Depends(require_storyteller)])
async def revert_pithag(body: TransformBody) -> dict[str, Any]:
    """说书人撤销已生效的麻脸巫婆变身(容错):角色恢复、注入步骤移除、「死亡由说书人决定」标记清除。"""
    try:
        game.revert_pithag(body.seat)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return deprecated_storyteller_view("/api/night/undo")



@router.post("/api/night/reply", dependencies=[Depends(require_storyteller)])
async def reply_night_choice(body: NightReplyBody) -> dict[str, Any]:
    """说书人电子回复玩家夜里的选择(实时推送到该玩家手机);也可直接发信息(教父首夜等)。"""
    try:
        game.reply_night_choice(body.seat, body.text, body.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return deprecated_storyteller_view("/api/night/information")



@router.post("/api/seat/{seat}/kill", dependencies=[Depends(require_storyteller)])
async def seat_kill(seat: int, body: SeatKillBody) -> dict[str, Any]:
    """说书人按座位代操作刀人(空座角色也可,便于测试人未齐开局)。"""
    try:
        game.submit_night_kill_seat(seat, body.target)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return deprecated_storyteller_view("/api/night/select")



@router.post("/api/seat/{seat}/alive", dependencies=[Depends(require_storyteller)])
async def seat_alive(seat: int) -> dict[str, Any]:
    """说书人按座位标记生死(空座同样可以):以说书人标记为准,而不是是否在座。"""
    try:
        game.toggle_seat_alive(seat)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/seat/{seat}/choice", dependencies=[Depends(require_storyteller)])
async def seat_choice(seat: int, body: SeatChoiceBody) -> dict[str, Any]:
    """说书人按座位代操作夜晚选人(空座角色也可,便于测试人未齐开局)。"""
    try:
        game.submit_night_choice_seat(seat, body.targets, body.char)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return deprecated_storyteller_view("/api/night/select")



@router.post("/api/traveler/add", dependencies=[Depends(require_storyteller)])
async def add_traveler(body: TravelerAddBody) -> dict[str, Any]:
    """说书人直接添加旅行者(无手机关联,说书人代管投票/生死)。"""
    try:
        game.add_traveler_st(body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/traveler/assign", dependencies=[Depends(require_storyteller)])
async def assign_traveler(body: TravelerAssignBody) -> dict[str, Any]:
    try:
        game.assign_traveler(body.id, body.role, body.align)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/traveler/exile", dependencies=[Depends(require_storyteller)])
async def exile_traveler(body: TravelerExileBody) -> dict[str, Any]:
    """流放/撤销流放:白天投票流放由 resolve 处理,这里供说书人随时直接流放(早退玩家)。"""
    try:
        game.exile_traveler(body.id, body.exiled)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/traveler/alive", dependencies=[Depends(require_storyteller)])
async def toggle_traveler_alive(body: TravelerAliveBody) -> dict[str, Any]:
    try:
        game.toggle_traveler_alive(body.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/fortuneteller/red", dependencies=[Depends(require_storyteller)])
async def set_fortuneteller_red(body: RedHerringBody) -> dict[str, Any]:
    """占卜师宿敌(红鲱鱼):说书人私下标记一名善良玩家,只有说书人知道。"""
    try:
        game.set_fortuneteller_red(body.seat)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/login")
def login(body: PasswordBody) -> dict[str, bool]:
    return {"ok": body.password == STORYTELLER_PASSWORD}



@router.post("/api/config", dependencies=[Depends(require_storyteller)])
async def config(body: ConfigBody) -> dict[str, Any]:
    try:
        game.configure(body.script, body.player_count)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.get("/api/state", dependencies=[Depends(require_storyteller)])
def state() -> dict[str, Any]:
    return game.storyteller_view()



@router.post("/api/assign", dependencies=[Depends(require_storyteller)])
async def assign() -> dict[str, Any]:
    try:
        game.assign_roles()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/assign/manual", dependencies=[Depends(require_storyteller)])
async def assign_manual(body: ManualAssignBody) -> dict[str, Any]:
    try:
        game.assign_manual(body.assignments, body.bluffs, body.fakes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/sentinel", dependencies=[Depends(require_storyteller)])
async def set_sentinel(body: SentinelBody) -> dict[str, Any]:
    """哨兵(神职角色):说书人调整外来者 +1/−1。方向保密,玩家只知哨兵在场。"""
    try:
        game.set_sentinel(body.value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/room", dependencies=[Depends(require_storyteller)])
async def set_room(body: RoomBody) -> dict[str, Any]:
    """说书人设定 4 位数字房间号,玩家加入时须匹配。"""
    try:
        game.set_room_code(body.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/start", dependencies=[Depends(require_storyteller)])
async def start() -> dict[str, Any]:
    """人未齐强制开局:空座需已预发身份,迟到玩家入座自动继承。"""
    try:
        game.start_game()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/fake", dependencies=[Depends(require_storyteller)])
async def set_fake(body: FakeBody) -> dict[str, Any]:
    """认知覆盖:说书人标记某座位玩家看到的假角色(酒鬼看到镇民/疯子以为自己是恶魔)。"""
    try:
        game.set_fake(body.seat, body.role, body.minions, body.bluffs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/marker", dependencies=[Depends(require_storyteller)])
async def set_marker(body: MarkerBody) -> dict[str, Any]:
    """状态标记:中毒/醉酒/疯狂/角色转变/阵营转变。疯狂附内容(善良角色),被疯狂者手机被告知。"""
    try:
        game.set_marker(body.seat, body.marker, body.on, body.role, body.team, body.about)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/nomination", dependencies=[Depends(require_storyteller)])
async def start_nomination(body: NominationBody) -> dict[str, Any]:
    try:
        game.start_nomination(body.nominator, body.nominee)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/nomination/vote", dependencies=[Depends(require_storyteller)])
async def toggle_vote(body: VoteBody) -> dict[str, Any]:
    try:
        game.toggle_vote(body.seat)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/nomination/resolve", dependencies=[Depends(require_storyteller)])
async def resolve_nomination(body: ResolveBody) -> dict[str, Any]:
    try:
        game.resolve_nomination(body.passed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/night/next", dependencies=[Depends(require_storyteller)])
async def night_next() -> dict[str, Any]:
    try:
        game.night_next()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return deprecated_storyteller_view("/api/night/step")



@router.post("/api/night/prev", dependencies=[Depends(require_storyteller)])
async def night_prev() -> dict[str, Any]:
    try:
        game.night_prev()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return deprecated_storyteller_view("/api/night/step")



@router.post("/api/night/goto", dependencies=[Depends(require_storyteller)])
async def night_goto(body: GotoBody) -> dict[str, Any]:
    try:
        game.night_goto(body.idx)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return deprecated_storyteller_view("/api/night/step")



@router.post("/api/day/end", dependencies=[Depends(require_storyteller)])
async def end_day() -> dict[str, Any]:
    try:
        game.end_day()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/day/stage", dependencies=[Depends(require_storyteller)])
async def set_day_stage(body: DayStageBody) -> dict[str, Any]:
    """说书人切换白天子阶段:talk 公聊私聊 / nom 提名阶段。"""
    try:
        game.set_day_stage(body.stage)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/end", dependencies=[Depends(require_storyteller)])
async def end_game(body: EndBody) -> dict[str, Any]:
    """说书人宣布游戏结束并判定获胜方(good/evil);winner=None 撤销结算。"""
    try:
        game.end_game(body.winner)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/review/mark", dependencies=[Depends(require_storyteller)])
async def mark_reply(body: ReviewMarkBody) -> dict[str, Any]:
    """说书人复盘标注:该夜该座位的回复信息是错的(实时同步到玩家复盘页)。"""
    try:
        game.mark_reply_wrong(body.seat, body.night, body.wrong)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/fabled", dependencies=[Depends(require_storyteller)])
async def toggle_fabled(body: FabledBody) -> dict[str, Any]:
    """传奇角色(Fabled,公开信息):说书人勾选在场,玩家手机可见列表。"""
    try:
        game.toggle_fabled(body.id, body.on)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/load", dependencies=[Depends(require_storyteller)])
async def load() -> dict[str, Any]:
    """放弃当前内存状态,从磁盘恢复上次自动存档。"""
    game.load()
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/player/{player_id}/alive", dependencies=[Depends(require_storyteller)])
async def toggle_alive(player_id: str) -> dict[str, Any]:
    if player_id not in game.players:
        raise HTTPException(status_code=404, detail="玩家不存在")
    game.toggle_alive(player_id)
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/player/{player_id}/remove", dependencies=[Depends(require_storyteller)])
async def remove_player(player_id: str) -> dict[str, Any]:
    game.remove_player(player_id)
    await hub.push_all()
    return game.storyteller_view()



@router.post("/api/reset", dependencies=[Depends(require_storyteller)])
async def reset() -> dict[str, Any]:
    game.reset()
    await hub.push_all()
    return game.storyteller_view()

