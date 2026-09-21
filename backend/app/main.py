"""Application assembly and Vue static hosting."""

from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from .api import NightCommandError, create_night_router, night_error_response
from .api import player, storyteller, chat, websocket, qr, identity, inference
from .api.dependencies import STORYTELLER_PASSWORD, require_storyteller
from .application.runtime import game, hub
from .application.realtime import Hub

app = FastAPI(title="BOTC Grimoire")
app.add_exception_handler(NightCommandError, night_error_response)
app.include_router(create_night_router(game, hub, require_storyteller))
app.include_router(player.router)
app.include_router(identity.router)
app.include_router(inference.router)
app.include_router(storyteller.router)
app.include_router(chat.router)
app.include_router(websocket.router)
app.include_router(qr.router)


FRONTEND_ROOT = Path(__file__).resolve().parent.parent.parent / "frontend"
FRONTEND_DIST = FRONTEND_ROOT / "dist"


def require_frontend_build(directory: Path) -> None:
    if not (directory / "index.html").is_file():
        raise RuntimeError(
            "frontend/dist is missing; run `cd frontend && npm install && npm run build`"
        )


require_frontend_build(FRONTEND_DIST)


app.mount("/", StaticFiles(directory=str(FRONTEND_DIST), html=True), name="frontend")
