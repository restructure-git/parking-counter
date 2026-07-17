"""画像の読み込み・切り出し・前処理を行うユーティリティ。

すべての関数は失敗時に例外を投げるのではなく、Noneを返す方針とする
（呼び出し側でunknown判定に落とし込むため）。
"""

from __future__ import annotations

import logging

import cv2
import numpy as np

from app.models import ParkingSpace

logger = logging.getLogger(__name__)

PIXEL_DIFF_THRESHOLD = 25
BLUR_KERNEL = (5, 5)
TARGET_BRIGHTNESS = 128.0


def decode_image(data: bytes) -> np.ndarray | None:
    """バイト列から画像をデコードする。失敗した場合はNone。"""
    if not data:
        return None
    try:
        array = np.frombuffer(data, dtype=np.uint8)
        image = cv2.imdecode(array, cv2.IMREAD_COLOR)
    except cv2.error as exc:
        logger.error("failed to decode image: %s", exc)
        return None
    if image is None or image.size == 0:
        logger.error("decoded image is empty")
        return None
    return image


def resize_max_width(image: np.ndarray, max_width: int) -> np.ndarray:
    """幅がmax_widthを超える場合のみ縮小する（アスペクト比維持）。"""
    height, width = image.shape[:2]
    if width <= max_width or max_width <= 0:
        return image
    scale = max_width / width
    new_size = (max_width, max(1, int(height * scale)))
    return cv2.resize(image, new_size, interpolation=cv2.INTER_AREA)


def crop_space(image: np.ndarray, space: ParkingSpace) -> np.ndarray | None:
    """画像から駐車枠部分を切り出す。範囲外の場合はNoneを返す。"""
    height, width = image.shape[:2]
    x1, y1 = space.x, space.y
    x2, y2 = space.x + space.width, space.y + space.height

    if x1 < 0 or y1 < 0 or space.width <= 0 or space.height <= 0:
        logger.warning("space %s has invalid geometry", space.id)
        return None

    if x1 >= width or y1 >= height:
        logger.warning("space %s is outside image bounds", space.id)
        return None

    x2 = min(x2, width)
    y2 = min(y2, height)

    cropped = image[y1:y2, x1:x2]
    if cropped.size == 0:
        logger.warning("space %s produced an empty crop", space.id)
        return None
    return cropped


def normalize_brightness(gray: np.ndarray, target_mean: float = TARGET_BRIGHTNESS) -> np.ndarray:
    """平均輝度をtarget_meanに合わせることで、日照差の影響を軽減する。"""
    current_mean = float(gray.mean())
    if current_mean <= 1e-6:
        return gray
    diff = target_mean - current_mean
    shifted = gray.astype(np.float32) + diff
    return np.clip(shifted, 0, 255).astype(np.uint8)


def preprocess(image: np.ndarray, size: tuple[int, int]) -> np.ndarray:
    """グレースケール化 + リサイズ + GaussianBlur + 明るさ正規化。"""
    resized = cv2.resize(image, size, interpolation=cv2.INTER_AREA)
    gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, BLUR_KERNEL, 0)
    return normalize_brightness(blurred)


def compute_difference_ratio(reference: np.ndarray, current: np.ndarray) -> float:
    """前処理済みの2画像から差分ピクセル率を計算する。"""
    diff = cv2.absdiff(reference, current)
    _, thresholded = cv2.threshold(diff, PIXEL_DIFF_THRESHOLD, 255, cv2.THRESH_BINARY)
    changed_pixels = int(np.count_nonzero(thresholded))
    total_pixels = thresholded.size
    if total_pixels == 0:
        return 0.0
    return changed_pixels / total_pixels
