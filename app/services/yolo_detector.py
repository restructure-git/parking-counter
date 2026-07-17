"""ローカル物体検出モデル（YOLO）による駐車枠判定。

画像差分方式（ParkingDetector）は、単色でベタ塗りの領域だと明るさ正規化で
差が打ち消されてしまう、明るさの変化に弱い、といった弱点がある。この実装は
基準画像を使わず、アップロードされた1枚の画像から検出した車両の矩形が、
駐車枠の矩形とどれだけ重なっているかだけで空き/使用中を判定する。

クラウドAPIやLLMは使わない。YOLOはテキスト生成モデルではなく、画像内の
物体を矩形で検出するだけの軽量なCNNで、CPU上でローカルに動作する。

ultralyticsパッケージは重い（torch等を含む）ため requirements.txt には含めず
requirements-yolo.txt に分離している。未インストールの場合は初期化時に
分かりやすいエラーメッセージを出す。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, cast

import numpy as np

from app.models import DetectionResult, DetectionStatus, ParkingSpace

if TYPE_CHECKING:
    from ultralytics.engine.results import Results

logger = logging.getLogger(__name__)

VEHICLE_CLASS_NAMES = {"car", "truck", "bus", "motorcycle"}

BoundingBox = tuple[float, float, float, float]


def overlap_ratio(space: ParkingSpace, box: BoundingBox) -> float:
    """駐車枠の面積に対する、駐車枠と矩形の重なり面積の割合を返す。"""
    space_area = space.width * space.height
    if space_area <= 0:
        return 0.0

    sx1, sy1 = space.x, space.y
    sx2, sy2 = space.x + space.width, space.y + space.height
    vx1, vy1, vx2, vy2 = box

    ix1, iy1 = max(sx1, vx1), max(sy1, vy1)
    ix2, iy2 = min(sx2, vx2), min(sy2, vy2)
    if ix2 <= ix1 or iy2 <= iy1:
        return 0.0

    intersection = (ix2 - ix1) * (iy2 - iy1)
    return intersection / space_area


def best_overlap(space: ParkingSpace, boxes: list[BoundingBox]) -> float:
    """駐車枠に最も重なっている車両矩形の重なり率を返す（車両なしなら0）。"""
    return max((overlap_ratio(space, box) for box in boxes), default=0.0)


def classify_overlap(ratio: float, threshold: float, uncertain_margin: float) -> DetectionStatus:
    upper = threshold + uncertain_margin
    lower = threshold - uncertain_margin
    if ratio >= upper:
        return "occupied"
    if ratio <= lower:
        return "empty"
    return "unknown"


class YoloParkingDetector:
    """YOLOで検出した車両の矩形と駐車枠の重なりで空き/使用中を判定する。"""

    def __init__(
        self,
        model_path: str,
        confidence_threshold: float,
        overlap_threshold: float,
        uncertain_margin: float,
    ) -> None:
        try:
            from ultralytics import YOLO
        except ImportError as exc:
            raise RuntimeError(
                "YOLO判定バックエンドには ultralytics が必要です。"
                "`pip install -r requirements-yolo.txt` を実行してください。"
            ) from exc

        self.model = YOLO(model_path)
        self.confidence_threshold = confidence_threshold
        self.overlap_threshold = overlap_threshold
        self.uncertain_margin = uncertain_margin
        logger.info("YOLO model loaded: %s", model_path)

    def detect_all(
        self, image: np.ndarray, spaces: list[ParkingSpace]
    ) -> dict[int, DetectionResult]:
        vehicle_boxes = self._detect_vehicles(image)
        results: dict[int, DetectionResult] = {}
        for space in spaces:
            ratio = best_overlap(space, vehicle_boxes)
            status = classify_overlap(ratio, self.overlap_threshold, self.uncertain_margin)
            results[space.id] = DetectionResult(status=status, difference_ratio=round(ratio, 4))
        return results

    def _detect_vehicles(self, image: np.ndarray) -> list[BoundingBox]:
        predictions = cast("list[Results]", self.model(image, verbose=False))
        prediction = predictions[0]
        names = prediction.names
        boxes: list[BoundingBox] = []
        if prediction.boxes is None:
            return boxes
        for box in prediction.boxes:  # type: ignore[attr-defined]  # Boxes is iterable at runtime; stub is incomplete
            class_name = names[int(box.cls[0])]
            confidence = float(box.conf[0])
            if class_name not in VEHICLE_CLASS_NAMES or confidence < self.confidence_threshold:
                continue
            x1, y1, x2, y2 = (float(v) for v in box.xyxy[0].tolist())
            boxes.append((x1, y1, x2, y2))
        return boxes
