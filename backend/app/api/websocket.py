"""WebSocket session endpoint."""

from urllib.parse import urlsplit

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..application import runtime
from ..application.runtime import hub
from .dependencies import STORYTELLER_PASSWORD, resolve_participant

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(ws: WebSocket, who: str = "", pw: str = "") -> None:
    origin = urlsplit(ws.headers.get("origin", ""))
    scheme = "https" if ws.url.scheme == "wss" else "http"
    if (origin.scheme, origin.netloc) != (scheme, ws.headers.get("host", "")):
        await ws.close(code=4003, reason="请求来源无效")
        return
    if who == "storyteller":
        if pw != STORYTELLER_PASSWORD:
            await ws.close(code=4003, reason="密码错误")
            return
        verified = "storyteller"
    else:
        if who:
            await ws.close(code=4003, reason="公开身份不能作为凭证")
            return
        token = ws.cookies.get("botc_session")
        session = runtime.identity_store.resolve_session(token) if token else None
        verified = resolve_participant(runtime.game, session) if session else None
        if verified is None:
            await ws.close(code=4001, reason="身份无效")
            return
    await hub.connect(verified, ws)
    try:
        while True:
            await ws.receive_text()  # 心跳/预留指令通道
    except WebSocketDisconnect:
        pass
    finally:
        hub.disconnect(verified, ws)
