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


class SitBody(BaseModel):
    seat: int


class ConfigBody(BaseModel):
    script: str
    player_count: int


class PasswordBody(BaseModel):
    password: str


def require_storyteller(x_password: str = Header(default="", alias="X-Storyteller-Password")) -> None:
    if x_password != STORYTELLER_PASSWORD:
        raise HTTPException(status_code=401, detail="说书人密码错误")


# ---- 玩家接口 ----

@app.post("/api/join")
async def join(body: JoinBody) -> dict[str, Any]:
    if not body.name.strip():
        raise HTTPException(status_code=400, detail="请输入名字")
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
    url = f"http://{get_lan_ip()}:8000/"
    buf = io.BytesIO()
    qrcode.make(url).save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")


# ---- 前端静态托管(frontend/ 无构建,直接托管) ----

_FRONTEND = Path(__file__).resolve().parent.parent.parent / "frontend"
app.mount("/", StaticFiles(directory=str(_FRONTEND), html=True), name="frontend")
