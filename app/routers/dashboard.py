"""ダッシュボード画面と判定結果画像の配信。"""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR
from app.services import detection_service

router = APIRouter(tags=["dashboard"])
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))


@router.get("/", response_class=HTMLResponse)
def dashboard(request: Request) -> HTMLResponse:
    payload = detection_service.build_status_payload()
    return templates.TemplateResponse(request, "dashboard.html", {"status": payload})


@router.get("/result-image")
def result_image() -> FileResponse:
    path = detection_service.ANNOTATED_IMAGE_PATH
    if not path.exists():
        raise HTTPException(status_code=404, detail="判定画像がまだありません。")
    return FileResponse(str(path), media_type="image/jpeg")
