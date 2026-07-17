"""駐車枠の登録・編集・削除、および基準画像の登録。"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, File, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates

from app.config import BASE_DIR, settings
from app.schemas import ParkingSpaceIn, ParkingSpaceOut
from app.services import reference_manager, space_store
from app.services.detection_service import state_manager
from app.services.image_processor import decode_image, resize_max_width

logger = logging.getLogger(__name__)

router = APIRouter(tags=["admin"])
templates = Jinja2Templates(directory=str(BASE_DIR / "app" / "templates"))

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp"}


def _has_reference(space_id: int) -> bool:
    return reference_manager.reference_path(space_id).exists()


@router.get("/admin/spaces", response_class=HTMLResponse)
def spaces_page(request: Request) -> HTMLResponse:
    spaces = space_store.load_spaces()
    spaces_view = [{**s.to_dict(), "has_reference": _has_reference(s.id)} for s in spaces]
    spaces_json = json.dumps([s.to_dict() for s in spaces], ensure_ascii=False).replace(
        "</", "<\\/"
    )
    return templates.TemplateResponse(
        request,
        "spaces.html",
        {
            "spaces": spaces_view,
            "spaces_json": spaces_json,
            "image_max_width": settings.image_max_width,
        },
    )


@router.post("/admin/spaces/api", response_model=ParkingSpaceOut)
def create_space(payload: ParkingSpaceIn) -> ParkingSpaceOut:
    space = space_store.add_space(
        name=payload.name, x=payload.x, y=payload.y, width=payload.width, height=payload.height
    )
    return ParkingSpaceOut(**space.to_dict())


@router.put("/admin/spaces/api/{space_id}", response_model=ParkingSpaceOut)
def update_space(space_id: int, payload: ParkingSpaceIn) -> ParkingSpaceOut:
    space = space_store.update_space(
        space_id,
        name=payload.name,
        x=payload.x,
        y=payload.y,
        width=payload.width,
        height=payload.height,
    )
    if space is None:
        raise HTTPException(status_code=404, detail="指定された駐車枠が見つかりません。")
    return ParkingSpaceOut(**space.to_dict())


@router.delete("/admin/spaces/api/{space_id}")
def delete_space(space_id: int) -> dict:
    deleted = space_store.delete_space(space_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="指定された駐車枠が見つかりません。")
    reference_manager.delete_reference(space_id)
    state_manager.remove_space(space_id)
    return {"deleted": True}


@router.post("/api/reference")
async def register_reference(file: UploadFile = File(...)) -> JSONResponse:  # noqa: B008
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

    image = decode_image(data)
    if image is None:
        raise HTTPException(
            status_code=400,
            detail="画像を読み込めませんでした。ファイルが壊れている可能性があります。",
        )

    image = resize_max_width(image, settings.image_max_width)
    spaces = space_store.load_spaces()
    if not spaces:
        raise HTTPException(
            status_code=400, detail="駐車枠が登録されていません。先に駐車枠を登録してください。"
        )

    results = reference_manager.register_references_from_full_image(image, spaces)
    state_manager.reset()
    logger.info("reference registration results: %s", results)

    succeeded = [sid for sid, ok in results.items() if ok]
    failed = [sid for sid, ok in results.items() if not ok]
    return JSONResponse({"registered": succeeded, "failed": failed})
