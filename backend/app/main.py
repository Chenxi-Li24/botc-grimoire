"""FastAPI 入口:REST 操作 + WebSocket 实时推送 + 前端静态托管。"""

import io
import os
from pathlib import Path
from typing import Any

import qrcode
from fastapi.responses import FileResponse
from fastapi import Depends, FastAPI, Header, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from .api import NightCommandError, create_night_router, night_error_response
from .game import GameManager
from .net import get_lan_ip

STORYTELLER_PASSWORD = os.environ.get("STORYTELLER_PASSWORD", "grimoire")

game = GameManager()
app = FastAPI(title="BOTC Grimoire")


class Hub:
    """WebSocket 连接池:按「说书人 / 玩家id」分组,推送各自的视图。"""

    def __init__(self) -> None:
        self.storytellers: set[WebSocket] = set()
        self.players: dict[str, set[WebSocket]] = {}

    async def connect(self, who: str, ws: WebSocket) -> None:
        await ws.accept()
        if who == "storyteller":
            self.storytellers.add(ws)
            await ws.send_json(game.storyteller_view())
        elif who in game.players:
            self.players.setdefault(who, set()).add(ws)
            await ws.send_json(game.player_view(who))
            if game.mark_private_deliveries_delivered(who):
                game.save()
        else:
            await ws.close(code=4001, reason="未知身份")
            return

    def disconnect(self, who: str, ws: WebSocket) -> None:
        if who == "storyteller":
            self.storytellers.discard(ws)
        else:
            self.players.get(who, set()).discard(ws)

    async def push_all(self) -> None:
        """任何状态变化后向所有在线设备推送各自的视图。"""
        view = game.storyteller_view()
        for ws in list(self.storytellers):
            await self._send(ws, view)
        for player_id, sockets in list(self.players.items()):
            if player_id not in game.players:
                for ws in list(sockets):
                    try:
                        await ws.close(code=4001, reason="未知身份")
                    except Exception:
                        pass
                self.players.pop(player_id, None)
                continue
            view = game.player_view(player_id)
            delivered = False
            for ws in list(sockets):
                delivered = await self._send(ws, view) or delivered
            if delivered and game.mark_private_deliveries_delivered(player_id):
                game.save()

    @staticmethod
    async def _send(ws: WebSocket, view: dict) -> bool:
        try:
            await ws.send_json(view)
            return True
        except Exception:
            return False  # 断开的连接由 disconnect() 清理


hub = Hub()


class JoinBody(BaseModel):
    name: str
    room_code: str  # 4 位数字房间号,须与说书人设定一致


class SitBody(BaseModel):
    seat: int


class ConfigBody(BaseModel):
    script: str
    player_count: int


class PasswordBody(BaseModel):
    password: str


class ManualAssignBody(BaseModel):
    assignments: list[dict]  # [{"seat": int, "role": str}, ...]
    bluffs: list[str] | None = None  # 伪装:3 个不在场好角色 id(可选,缺省自动抽取)
    fakes: list[dict] | None = None  # 认知覆盖:[{"seat": int, "role": str}],疯子/酒鬼看到的假身份


class FakeBody(BaseModel):
    seat: int
    role: str | None = None  # 玩家看到的假角色;None 表示清除认知覆盖
    minions: list[int] | None = None  # 疯子:以为的爪牙座位(说书人选,不一定是真的)
    bluffs: list[str] | None = None  # 疯子:3 个伪装(说书人选,不一定是恶魔的真伪装)


class MarkerBody(BaseModel):
    seat: int
    marker: str  # poisoned | drunk | mad | role-change | team-change
    on: bool
    role: str | None = None  # role-change 时必填:变成的角色 id
    team: str | None = None  # team-change 时必填:新阵营 good/evil
    about: str | None = None  # mad 时必填:疯狂宣称的善良角色 id


class NominationBody(BaseModel):
    nominator: int | str  # 座位号或旅行者 id("t1")
    nominee: int | str


class VoteBody(BaseModel):
    seat: int | str  # 座位号或旅行者 id("t1")


class NomineeBody(BaseModel):
    nominee: int | str  # 被提名者:座位号或旅行者 id("t1")


class DayStageBody(BaseModel):
    stage: str  # talk 公聊私聊 | nom 提名阶段(说书人控节奏)


class KillBody(BaseModel):
    seat: int  # 刀杀目标座位


class NightChoiceBody(BaseModel):
    targets: list[int]  # 夜晚选择的目标座位(数量按角色配置)
    char: str | None = None  # 麻脸巫婆:变身后的角色 id(必须不在场)


class TransformBody(BaseModel):
    seat: int  # 麻脸巫婆的座位(说书人确认其变身)


class NightReplyBody(BaseModel):
    seat: int  # 回复给哪个座位
    text: str  # 回复内容(占卜师:有恶魔/无恶魔 等)
    role: str | None = None  # 无选择直接发信息时的角色标注(教父首夜信息等)


class RedHerringBody(BaseModel):
    seat: int | None = None  # 宿敌座位;None = 清除


class WishBody(BaseModel):
    wish: str | None = None  # 许愿内容(善良/邪恶或自定义);None/空 = 清除


class ResolveBody(BaseModel):
    passed: bool  # 结票:通过 → 待处决(天黑结算最多票者);旅行者通过 → 当场流放


class TravelerAddBody(BaseModel):
    name: str  # 旅行者名字(说书人直接添加,无手机关联)


class TravelerAssignBody(BaseModel):
    id: str  # 旅行者 id(t1..)
    role: str  # 旅行者角色 id(官方旅行者池)
    align: str | None = None  # good/evil,缺省保持原值(新增时默认 good)


class TravelerExileBody(BaseModel):
    id: str
    exiled: bool = True  # False = 撤销流放


class TravelerAliveBody(BaseModel):
    id: str


class GotoBody(BaseModel):
    idx: int


class SentinelBody(BaseModel):
    value: int  # -1 / 0 / +1 / 2:哨兵对外来者数量的调整(0 = 关,2 = 在场但不调整)


class RoomBody(BaseModel):
    code: str  # 4 位数字房间号


def require_storyteller(x_password: str = Header(default="", alias="X-Storyteller-Password")) -> None:
    if x_password != STORYTELLER_PASSWORD:
        raise HTTPException(status_code=401, detail="说书人密码错误")


app.add_exception_handler(NightCommandError, night_error_response)
app.include_router(create_night_router(game, hub, require_storyteller))


def deprecated_storyteller_view(replacement: str) -> dict[str, Any]:
    return {
        **game.storyteller_view(),
        "deprecation": {
            "deprecated": True,
            "replacement": replacement,
        },
    }


# ---- 玩家接口 ----

@app.post("/api/join")
async def join(body: JoinBody) -> dict[str, Any]:
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="请输入名字")
    if body.room_code != game.room_code:
        raise HTTPException(status_code=400, detail="房间号错误")
    player = game.add_player(body.name)
    await hub.push_all()
    return {"player_id": player.id}


@app.post("/api/player/{player_id}/sit")
async def sit(player_id: str, body: SitBody) -> dict[str, Any]:
    try:
        game.sit(player_id, body.seat)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)


@app.get("/api/info")
def info() -> dict[str, Any]:
    return {"lan_ip": get_lan_ip(), "status": game.status,
            "script": game.script_id, "player_count": game.player_count}


@app.get("/api/me/{player_id}")
def me(player_id: str) -> dict[str, Any]:
    if player_id not in game.players:
        raise HTTPException(status_code=404, detail="玩家不存在(说书人可能已重置本局)")
    return game.player_view(player_id)


@app.post("/api/player/{player_id}/traveler")
async def join_traveler(player_id: str) -> dict[str, Any]:
    """玩家以旅行者身份加入(开局后任意时刻,不占座位)。"""
    try:
        game.add_traveler(player_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)


@app.post("/api/player/{player_id}/nominate")
async def nominate(player_id: str, body: NomineeBody) -> dict[str, Any]:
    """玩家手机发起提名:提名者必须是本人(存活、今天未提名过、白天、无进行中提名)。"""
    try:
        game.player_nominate(player_id, body.nominee)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)


@app.post("/api/player/{player_id}/vote")
async def vote(player_id: str) -> dict[str, Any]:
    """玩家手机举手/放下:只能投自己(死者举手=交出唯一死票,未结算可收回)。"""
    try:
        game.player_vote(player_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)


@app.post("/api/player/{player_id}/wish")
async def set_wish(player_id: str, body: WishBody) -> dict[str, Any]:
    """许愿(仅大厅):开局前表达愿望——善良/邪恶或自定义文字;空 = 清除。"""
    try:
        game.set_wish(player_id, body.wish)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)


@app.post("/api/player/{player_id}/kill")
async def night_kill(player_id: str, body: KillBody) -> dict[str, Any]:
    """夜晚刀人(仅瓦釜雷鸣):恶魔手机选择目标,天亮自动执行;疯子选择只演戏。"""
    try:
        game.submit_night_kill(player_id, body.seat)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)


@app.post("/api/player/{player_id}/choice")
async def night_choice(player_id: str, body: NightChoiceBody) -> dict[str, Any]:
    """夜晚信息交互(仅瓦釜雷鸣):占卜师/筑梦师等手机选人,说书人看到后电子回复。"""
    try:
        game.submit_night_choice(player_id, body.targets, body.char)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)


@app.post("/api/night/transform", dependencies=[Depends(require_storyteller)])
async def revert_pithag(body: TransformBody) -> dict[str, Any]:
    """说书人撤销已生效的麻脸巫婆变身(容错):角色恢复、注入步骤移除、「死亡由说书人决定」标记清除。"""
    try:
        game.revert_pithag(body.seat)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return deprecated_storyteller_view("/api/night/undo")


@app.post("/api/night/reply", dependencies=[Depends(require_storyteller)])
async def reply_night_choice(body: NightReplyBody) -> dict[str, Any]:
    """说书人电子回复玩家夜里的选择(实时推送到该玩家手机);也可直接发信息(教父首夜等)。"""
    try:
        game.reply_night_choice(body.seat, body.text, body.role)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return deprecated_storyteller_view("/api/night/information")


class EndBody(BaseModel):
    winner: str | None = None  # good/evil;None = 撤销结算


class ReviewMarkBody(BaseModel):
    seat: int  # 回复接收者座位
    night: int  # 第几夜
    wrong: bool = True  # True 标注错误 / False 撤销标注


class FabledBody(BaseModel):
    id: str  # 传奇角色 id
    on: bool = True  # True 勾选在场 / False 移除


class ChatCreateBody(BaseModel):
    invitees: list  # 被邀请者:座位号(int)/旅行者 id(str)/说书人 "st"


class ChatInviteBody(BaseModel):
    accept: bool  # 接受邀请


class ChatApproveBody(BaseModel):
    who: int | str  # 申请者
    approve: bool  # 同意


class ChatSendBody(BaseModel):
    text: str


class SeatKillBody(BaseModel):
    target: int  # 刀杀目标座位


class SeatChoiceBody(BaseModel):
    targets: list[int]
    char: str | None = None  # 麻脸巫婆/洗脑师的角色选择


@app.post("/api/seat/{seat}/kill", dependencies=[Depends(require_storyteller)])
async def seat_kill(seat: int, body: SeatKillBody) -> dict[str, Any]:
    """说书人按座位代操作刀人(空座角色也可,便于测试人未齐开局)。"""
    try:
        game.submit_night_kill_seat(seat, body.target)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return deprecated_storyteller_view("/api/night/select")


@app.post("/api/seat/{seat}/alive", dependencies=[Depends(require_storyteller)])
async def seat_alive(seat: int) -> dict[str, Any]:
    """说书人按座位标记生死(空座同样可以):以说书人标记为准,而不是是否在座。"""
    try:
        game.toggle_seat_alive(seat)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/seat/{seat}/choice", dependencies=[Depends(require_storyteller)])
async def seat_choice(seat: int, body: SeatChoiceBody) -> dict[str, Any]:
    """说书人按座位代操作夜晚选人(空座角色也可,便于测试人未齐开局)。"""
    try:
        game.submit_night_choice_seat(seat, body.targets, body.char)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return deprecated_storyteller_view("/api/night/select")


# ---- 旅行者接口(说书人) ----

@app.post("/api/traveler/add", dependencies=[Depends(require_storyteller)])
async def add_traveler(body: TravelerAddBody) -> dict[str, Any]:
    """说书人直接添加旅行者(无手机关联,说书人代管投票/生死)。"""
    try:
        game.add_traveler_st(body.name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/traveler/assign", dependencies=[Depends(require_storyteller)])
async def assign_traveler(body: TravelerAssignBody) -> dict[str, Any]:
    try:
        game.assign_traveler(body.id, body.role, body.align)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/traveler/exile", dependencies=[Depends(require_storyteller)])
async def exile_traveler(body: TravelerExileBody) -> dict[str, Any]:
    """流放/撤销流放:白天投票流放由 resolve 处理,这里供说书人随时直接流放(早退玩家)。"""
    try:
        game.exile_traveler(body.id, body.exiled)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/traveler/alive", dependencies=[Depends(require_storyteller)])
async def toggle_traveler_alive(body: TravelerAliveBody) -> dict[str, Any]:
    try:
        game.toggle_traveler_alive(body.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/fortuneteller/red", dependencies=[Depends(require_storyteller)])
async def set_fortuneteller_red(body: RedHerringBody) -> dict[str, Any]:
    """占卜师宿敌(红鲱鱼):说书人私下标记一名善良玩家,只有说书人知道。"""
    try:
        game.set_fortuneteller_red(body.seat)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


# ---- 说书人接口(需 X-Storyteller-Password 头) ----

@app.post("/api/login")
def login(body: PasswordBody) -> dict[str, bool]:
    return {"ok": body.password == STORYTELLER_PASSWORD}


@app.post("/api/config", dependencies=[Depends(require_storyteller)])
async def config(body: ConfigBody) -> dict[str, Any]:
    try:
        game.configure(body.script, body.player_count)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.get("/api/state", dependencies=[Depends(require_storyteller)])
def state() -> dict[str, Any]:
    return game.storyteller_view()


@app.post("/api/assign", dependencies=[Depends(require_storyteller)])
async def assign() -> dict[str, Any]:
    try:
        game.assign_roles()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/assign/manual", dependencies=[Depends(require_storyteller)])
async def assign_manual(body: ManualAssignBody) -> dict[str, Any]:
    try:
        game.assign_manual(body.assignments, body.bluffs, body.fakes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/sentinel", dependencies=[Depends(require_storyteller)])
async def set_sentinel(body: SentinelBody) -> dict[str, Any]:
    """哨兵(神职角色):说书人调整外来者 +1/−1。方向保密,玩家只知哨兵在场。"""
    try:
        game.set_sentinel(body.value)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/room", dependencies=[Depends(require_storyteller)])
async def set_room(body: RoomBody) -> dict[str, Any]:
    """说书人设定 4 位数字房间号,玩家加入时须匹配。"""
    try:
        game.set_room_code(body.code)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/start", dependencies=[Depends(require_storyteller)])
async def start() -> dict[str, Any]:
    """人未齐强制开局:空座需已预发身份,迟到玩家入座自动继承。"""
    try:
        game.start_game()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/fake", dependencies=[Depends(require_storyteller)])
async def set_fake(body: FakeBody) -> dict[str, Any]:
    """认知覆盖:说书人标记某座位玩家看到的假角色(酒鬼看到镇民/疯子以为自己是恶魔)。"""
    try:
        game.set_fake(body.seat, body.role, body.minions, body.bluffs)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/marker", dependencies=[Depends(require_storyteller)])
async def set_marker(body: MarkerBody) -> dict[str, Any]:
    """状态标记:中毒/醉酒/疯狂/角色转变/阵营转变。疯狂附内容(善良角色),被疯狂者手机被告知。"""
    try:
        game.set_marker(body.seat, body.marker, body.on, body.role, body.team, body.about)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


# ---- 提名 / 投票 / 处决(说书人记录,票型公开推送) ----

@app.post("/api/nomination", dependencies=[Depends(require_storyteller)])
async def start_nomination(body: NominationBody) -> dict[str, Any]:
    try:
        game.start_nomination(body.nominator, body.nominee)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/nomination/vote", dependencies=[Depends(require_storyteller)])
async def toggle_vote(body: VoteBody) -> dict[str, Any]:
    try:
        game.toggle_vote(body.seat)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/nomination/resolve", dependencies=[Depends(require_storyteller)])
async def resolve_nomination(body: ResolveBody) -> dict[str, Any]:
    try:
        game.resolve_nomination(body.passed)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


# ---- 夜晚流程 / 存档 ----

@app.post("/api/night/next", dependencies=[Depends(require_storyteller)])
async def night_next() -> dict[str, Any]:
    try:
        game.night_next()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return deprecated_storyteller_view("/api/night/step")


@app.post("/api/night/prev", dependencies=[Depends(require_storyteller)])
async def night_prev() -> dict[str, Any]:
    try:
        game.night_prev()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return deprecated_storyteller_view("/api/night/step")


@app.post("/api/night/goto", dependencies=[Depends(require_storyteller)])
async def night_goto(body: GotoBody) -> dict[str, Any]:
    try:
        game.night_goto(body.idx)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return deprecated_storyteller_view("/api/night/step")


@app.post("/api/day/end", dependencies=[Depends(require_storyteller)])
async def end_day() -> dict[str, Any]:
    try:
        game.end_day()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/day/stage", dependencies=[Depends(require_storyteller)])
async def set_day_stage(body: DayStageBody) -> dict[str, Any]:
    """说书人切换白天子阶段:talk 公聊私聊 / nom 提名阶段。"""
    try:
        game.set_day_stage(body.stage)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/end", dependencies=[Depends(require_storyteller)])
async def end_game(body: EndBody) -> dict[str, Any]:
    """说书人宣布游戏结束并判定获胜方(good/evil);winner=None 撤销结算。"""
    try:
        game.end_game(body.winner)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/review/mark", dependencies=[Depends(require_storyteller)])
async def mark_reply(body: ReviewMarkBody) -> dict[str, Any]:
    """说书人复盘标注:该夜该座位的回复信息是错的(实时同步到玩家复盘页)。"""
    try:
        game.mark_reply_wrong(body.seat, body.night, body.wrong)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/fabled", dependencies=[Depends(require_storyteller)])
async def toggle_fabled(body: FabledBody) -> dict[str, Any]:
    """传奇角色(Fabled,公开信息):说书人勾选在场,玩家手机可见列表。"""
    try:
        game.toggle_fabled(body.id, body.on)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


# ---- 白天私聊(内存态;说书人作为特殊玩家 "st") ----

def _player_who(player_id: str) -> int | str:
    """玩家的私聊身份:座位号或旅行者 id。"""
    t = game.traveler_of(player_id)
    if t is not None:
        return t["id"]
    me = game.players[player_id]
    if me.seat is None:
        raise HTTPException(status_code=400, detail="你还没有入座")
    return me.seat


@app.post("/api/chat/create")
async def chat_create(player_id: str, body: ChatCreateBody) -> dict[str, Any]:
    try:
        game.create_chat(_player_who(player_id), body.invitees)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)


@app.post("/api/chat/{cid}/invite")
async def chat_invite(player_id: str, cid: int, body: ChatInviteBody) -> dict[str, Any]:
    try:
        game.respond_invite(_player_who(player_id), cid, body.accept)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)


@app.post("/api/chat/{cid}/request")
async def chat_request(player_id: str, cid: int) -> dict[str, Any]:
    try:
        game.request_join(_player_who(player_id), cid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)


@app.post("/api/chat/{cid}/invite-more")
async def chat_invite_more(player_id: str, cid: int, body: ChatCreateBody) -> dict[str, Any]:
    """私聊进行中,发起者邀请更多玩家加入。"""
    try:
        game.invite_to_chat(_player_who(player_id), cid, body.invitees)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)


@app.post("/api/chat/{cid}/approve")
async def chat_approve(player_id: str, cid: int, body: ChatApproveBody) -> dict[str, Any]:
    try:
        game.approve_request(_player_who(player_id), cid, body.who, body.approve)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)


@app.post("/api/chat/{cid}/send")
async def chat_send(player_id: str, cid: int, body: ChatSendBody) -> dict[str, Any]:
    try:
        game.send_message(_player_who(player_id), cid, body.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)


@app.post("/api/chat/{cid}/leave")
async def chat_leave(player_id: str, cid: int) -> dict[str, Any]:
    try:
        game.leave_chat(_player_who(player_id), cid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)


@app.post("/api/chat/{cid}/close")
async def chat_close(player_id: str, cid: int) -> dict[str, Any]:
    try:
        game.close_chat(_player_who(player_id), cid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.player_view(player_id)


# 说书人作为特殊玩家:接受邀请/发消息/退出/关闭/召回
@app.post("/api/chat-st/{cid}/invite", dependencies=[Depends(require_storyteller)])
async def st_chat_invite(cid: int, body: ChatInviteBody) -> dict[str, Any]:
    try:
        game.respond_invite("st", cid, body.accept)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/chat-st/{cid}/send", dependencies=[Depends(require_storyteller)])
async def st_chat_send(cid: int, body: ChatSendBody) -> dict[str, Any]:
    try:
        game.send_message("st", cid, body.text)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/chat-st/{cid}/leave", dependencies=[Depends(require_storyteller)])
async def st_chat_leave(cid: int) -> dict[str, Any]:
    try:
        game.leave_chat("st", cid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/chat-st/{cid}/close", dependencies=[Depends(require_storyteller)])
async def st_chat_close(cid: int) -> dict[str, Any]:
    try:
        game.close_chat("st", cid)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/chat-st/recall", dependencies=[Depends(require_storyteller)])
async def st_chat_recall() -> dict[str, Any]:
    """说书人召回:关闭全部私聊。"""
    game.recall_chats()
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/load", dependencies=[Depends(require_storyteller)])
async def load() -> dict[str, Any]:
    """放弃当前内存状态,从磁盘恢复上次自动存档。"""
    game.load()
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/player/{player_id}/alive", dependencies=[Depends(require_storyteller)])
async def toggle_alive(player_id: str) -> dict[str, Any]:
    if player_id not in game.players:
        raise HTTPException(status_code=404, detail="玩家不存在")
    game.toggle_alive(player_id)
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/player/{player_id}/remove", dependencies=[Depends(require_storyteller)])
async def remove_player(player_id: str) -> dict[str, Any]:
    game.remove_player(player_id)
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/reset", dependencies=[Depends(require_storyteller)])
async def reset() -> dict[str, Any]:
    game.reset()
    await hub.push_all()
    return game.storyteller_view()


# ---- WebSocket ----

@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, who: str = "", pw: str = "") -> None:
    if who == "storyteller" and pw != STORYTELLER_PASSWORD:
        await ws.close(code=4003, reason="密码错误")
        return
    await hub.connect(who, ws)
    try:
        while True:
            await ws.receive_text()  # 心跳/预留指令通道
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(who, ws)


# ---- 加入二维码(后端生成,前端 <img src="/api/qr">) ----

@app.get("/api/qr")
def qr() -> Response:
    # 公网穿透时设 PUBLIC_URL(如 https://xxx.sakurafrp.com),否则回退局域网 IP
    url = os.environ.get("PUBLIC_URL") or f"http://{get_lan_ip()}:8000/"
    url += f"#/?room={game.room_code}"  # 扫码自动预填房间号
    buf = io.BytesIO()
    qrcode.make(url).save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")


# ---- 前端静态托管(Vue 构建产物 + 迁移期旧界面) ----

FRONTEND_ROOT = Path(__file__).resolve().parent.parent.parent / "frontend"
FRONTEND_DIST = FRONTEND_ROOT / "dist"
FRONTEND_LEGACY = FRONTEND_ROOT / "legacy"


def require_frontend_build(directory: Path) -> None:
    if not (directory / "index.html").is_file():
        raise RuntimeError(
            "frontend/dist is missing; run `cd frontend && npm install && npm run build`"
        )


require_frontend_build(FRONTEND_DIST)


@app.get("/app.js", include_in_schema=False)
async def serve_app_js() -> FileResponse:
    """迁移期旧前端脚本兼容入口。"""
    return FileResponse(FRONTEND_LEGACY / "app.js", headers={"Cache-Control": "no-cache"})


@app.get("/styles.css", include_in_schema=False)
async def serve_styles() -> FileResponse:
    return FileResponse(FRONTEND_LEGACY / "styles.css", headers={"Cache-Control": "no-cache"})


app.mount("/legacy", StaticFiles(directory=str(FRONTEND_LEGACY), html=True), name="legacy")
app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
