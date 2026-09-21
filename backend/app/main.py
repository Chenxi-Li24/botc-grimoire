"""Application assembly and Vue static hosting."""

from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .api import NightCommandError, create_night_router, night_error_response
from .api import player, storyteller, chat, websocket, qr
from .api.dependencies import STORYTELLER_PASSWORD, require_storyteller
from .application.runtime import game, hub
from .application.realtime import Hub

app = FastAPI(title="BOTC Grimoire")
app.add_exception_handler(NightCommandError, night_error_response)
app.include_router(create_night_router(game, hub, require_storyteller))
app.include_router(player.router)
app.include_router(storyteller.router)
app.include_router(chat.router)
app.include_router(websocket.router)
app.include_router(qr.router)


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
