"""駐車場空き台数カウントシステム FastAPIエントリポイント。"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.staticfiles import StaticFiles

from app.auth import auth_enabled, require_auth
from app.config import BASE_DIR, ensure_data_dirs, settings
from app.database import init_db
from app.schemas import HealthResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("app")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("application starting up")
    ensure_data_dirs()
    init_db()
    logger.info(
        "settings loaded: occupied_threshold=%s required_consecutive_results=%s",
        settings.occupied_threshold,
        settings.required_consecutive_results,
    )
    if auth_enabled():
        logger.info("admin authentication is enabled")
    else:
        logger.warning(
            "admin authentication is DISABLED (PARKING_ADMIN_USERNAME/PARKING_ADMIN_PASSWORD "
            "not set) - anyone who can reach this server can view and modify parking data"
        )
    yield


app = FastAPI(title="Parking Space Counter", version="0.1.0", lifespan=lifespan)

static_dir = BASE_DIR / "app" / "static"
static_dir.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


from app.routers import admin, dashboard, detection, history  # noqa: E402

_auth_dep = [Depends(require_auth)]
app.include_router(dashboard.router, dependencies=_auth_dep)
app.include_router(detection.router, dependencies=_auth_dep)
app.include_router(history.router, dependencies=_auth_dep)
app.include_router(admin.router, dependencies=_auth_dep)
