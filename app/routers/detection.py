"""画像アップロードと判定実行のエンドポイント。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR, settings
from app.schemas import ParkingStatusResponse
from app.services import detection_service

logger = logging.getLogger(__name__)

router = APIRouter(tags=["detection"])
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


@router.get("/upload", response_class=HTMLResponse)
def upload_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "upload.html")


@router.post("/api/detect", response_model=ParkingStatusResponse)
async def api_detect(file: UploadFile = File(...)) -> ParkingStatusResponse:  # noqa: B008
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail="対応していない画像形式です。JPEG、PNG、WebPのいずれかを使用してください。",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="画像データが空です。")
    if len(data) > settings.max_upload_size_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"画像サイズが上限（{settings.max_upload_size_mb}MB）を超えています。",
        )

    try:
        results = detection_service.run_detection(data)
    except Exception:
        logger.exception("unexpected error during detection")
        raise HTTPException(status_code=500, detail="判定処理中にエラーが発生しました。") from None

    if results is None:
        raise HTTPException(
            status_code=400,
            detail="画像を読み込めませんでした。ファイルが壊れている可能性があります。",
        )

    return ParkingStatusResponse(**detection_service.build_status_payload())


@router.get("/api/status", response_model=ParkingStatusResponse)
def api_status() -> ParkingStatusResponse:
    return ParkingStatusResponse(**detection_service.build_status_payload())
