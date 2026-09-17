"""FastAPI 入口:REST 操作 + WebSocket 实时推送 + 前端静态托管。"""

import io
import os
from pathlib import Path
from typing import Any

import qrcode
from fastapi import Depends, FastAPI, Header, HTTPException, Response, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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
                continue
            view = game.player_view(player_id)
            for ws in list(sockets):
                await self._send(ws, view)

    @staticmethod
    async def _send(ws: WebSocket, view: dict) -> None:
        try:
            await ws.send_json(view)
        except Exception:
            pass  # 断开的连接由 disconnect() 清理


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


class NominationBody(BaseModel):
    nominator: int
    nominee: int


class VoteBody(BaseModel):
    seat: int


class ResolveBody(BaseModel):
    executed: bool


class GotoBody(BaseModel):
    idx: int


class SentinelBody(BaseModel):
    value: int  # -1 / 0 / +1 / 2:哨兵对外来者数量的调整(0 = 关,2 = 在场但不调整)


class RoomBody(BaseModel):
    code: str  # 4 位数字房间号


def require_storyteller(x_password: str = Header(default="", alias="X-Storyteller-Password")) -> None:
    if x_password != STORYTELLER_PASSWORD:
        raise HTTPException(status_code=401, detail="说书人密码错误")


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
    """状态标记:中毒/醉酒/疯狂/角色转变/阵营转变。阵营转变会通知玩家本人。"""
    try:
        game.set_marker(body.seat, body.marker, body.on, body.role)
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
        game.resolve_nomination(body.executed)
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
    return game.storyteller_view()


@app.post("/api/night/prev", dependencies=[Depends(require_storyteller)])
async def night_prev() -> dict[str, Any]:
    try:
        game.night_prev()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/night/goto", dependencies=[Depends(require_storyteller)])
async def night_goto(body: GotoBody) -> dict[str, Any]:
    try:
        game.night_goto(body.idx)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    await hub.push_all()
    return game.storyteller_view()


@app.post("/api/day/end", dependencies=[Depends(require_storyteller)])
async def end_day() -> dict[str, Any]:
    try:
        game.end_day()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
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


# ---- 前端静态托管(frontend/ 无构建,直接托管) ----

_FRONTEND = Path(__file__).resolve().parent.parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(_FRONTEND), html=True), name="frontend")
