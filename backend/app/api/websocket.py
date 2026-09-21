"""WebSocket session endpoint."""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from ..application.runtime import hub
from .dependencies import STORYTELLER_PASSWORD

router = APIRouter()

@router.websocket("/ws")
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

