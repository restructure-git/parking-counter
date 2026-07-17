"""駐車枠ごとの基準画像（空車状態）の保存・読み込み。

元の駐車場全体画像は保存せず、駐車枠部分を切り出したものだけを
data/reference/ 配下に保存する。
"""

from __future__ import annotations

import logging
from pathlib import Path

import cv2
import numpy as np

from app.config import REFERENCE_DIR
from app.models import ParkingSpace
from app.services.image_processor import crop_space

logger = logging.getLogger(__name__)


def reference_path(space_id: int) -> Path:
    return REFERENCE_DIR / f"space_{space_id:03d}.jpg"


def save_reference(space_id: int, cropped_image: np.ndarray) -> bool:
    path = reference_path(space_id)
    try:
        REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
        success = cv2.imwrite(str(path), cropped_image)
        if not success:
            logger.error("cv2.imwrite failed for space %s", space_id)
        return bool(success)
    except OSError as exc:
        logger.error("failed to save reference image for space %s: %s", space_id, exc)
        return False


def load_reference(space_id: int) -> np.ndarray | None:
    path = reference_path(space_id)
    if not path.exists():
        return None
    try:
        image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    except cv2.error as exc:
        logger.error("failed to load reference image for space %s: %s", space_id, exc)
        return None
    if image is None or image.size == 0:
        logger.error("reference image for space %s is invalid", space_id)
        return None
    return image


def delete_reference(space_id: int) -> None:
    path = reference_path(space_id)
    try:
        if path.exists():
            path.unlink()
    except OSError as exc:
        logger.error("failed to delete reference image for space %s: %s", space_id, exc)


def register_references_from_full_image(
    full_image: np.ndarray, spaces: list[ParkingSpace]
) -> dict[int, bool]:
    """駐車場全体画像から各駐車枠を切り出し、基準画像として保存する。

    全体画像自体はここでも保存しない。
    """
    results: dict[int, bool] = {}
    for space in spaces:
        cropped = crop_space(full_image, space)
        if cropped is None:
            results[space.id] = False
            continue
        results[space.id] = save_reference(space.id, cropped)
    return results
