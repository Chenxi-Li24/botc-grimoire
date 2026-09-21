"""Join-code QR image endpoint."""

import io
import os
import qrcode
from fastapi import APIRouter, Response
from ..application.runtime import game
from ..net import get_lan_ip

router = APIRouter()

@router.get("/api/qr")
def qr() -> Response:
    # 公网穿透时设 PUBLIC_URL(如 https://xxx.sakurafrp.com),否则回退局域网 IP
    url = os.environ.get("PUBLIC_URL") or f"http://{get_lan_ip()}:8000/"
    url += f"#/?room={game.room_code}"  # 扫码自动预填房间号
    buf = io.BytesIO()
    qrcode.make(url).save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png")

