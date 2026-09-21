"""Join-code QR image endpoint."""

import io
import os
from typing import Literal
import qrcode
from fastapi import APIRouter, HTTPException, Response
from ..application.runtime import game
from ..net import get_lan_ip

router = APIRouter()


@router.get("/api/join-links")
def join_links() -> dict[str, str | None]:
    room = game.room_code
    public_base = os.environ.get("PUBLIC_URL", "").strip().rstrip("/")
    return {
        "local_url": f"http://{get_lan_ip()}:8000/#/?room={room}",
        "public_url": f"{public_base}/#/?room={room}" if public_base else None,
    }


@router.get("/api/qr")
def qr(mode: Literal["local", "public"] = "local") -> Response:
    url = join_links()[f"{mode}_url"]
    if url is None:
        raise HTTPException(status_code=404, detail="公网地址未配置")
    buf = io.BytesIO()
    qrcode.make(url).save(buf, format="PNG")
    return Response(content=buf.getvalue(), media_type="image/png",
                    headers={"Cache-Control": "no-store"})
