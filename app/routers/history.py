"""判定履歴の一覧表示。"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR
from app.database import get_recent_detections

router = APIRouter(tags=["history"])
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


@router.get("/history", response_class=HTMLResponse)
def history_page(request: Request) -> HTMLResponse:
    records = get_recent_detections(limit=100)
    return templates.TemplateResponse(request, "history.html", {"records": records})
