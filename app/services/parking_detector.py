"""駐車枠1つ分の画像差分判定。

将来YOLO等の別方式に差し替えられるよう、detect()のインターフェースを
シンプルに保つ（基準画像・現在画像 → DetectionResult）。
"""

from __future__ import annotations

import logging

import numpy as np

from app.models import DetectionResult, DetectionStatus
from app.services.image_processor import compute_difference_ratio, preprocess

logger = logging.getLogger(__name__)


class ParkingDetector:
    """基準画像との画像差分で空き/使用中を判定するシンプルな検出器。"""

    def __init__(self, occupied_threshold: float, uncertain_margin: float) -> None:
        self.occupied_threshold = occupied_threshold
        self.uncertain_margin = uncertain_margin

    def detect(
        self,
        reference_image: np.ndarray | None,
        current_image: np.ndarray | None,
    ) -> DetectionResult:
        """切り出し済みの駐車枠画像同士を比較する。

        いずれかがNone、またはサイズ不正・処理失敗の場合はunknownとする。
        """
        if reference_image is None or reference_image.size == 0:
            return DetectionResult(status="unknown", difference_ratio=None)
        if current_image is None or current_image.size == 0:
            return DetectionResult(status="unknown", difference_ratio=None)

        try:
            ref_height, ref_width = reference_image.shape[:2]
            if ref_width <= 0 or ref_height <= 0:
                return DetectionResult(status="unknown", difference_ratio=None)

            ref_processed = preprocess(reference_image, (ref_width, ref_height))
            cur_processed = preprocess(current_image, (ref_width, ref_height))
            difference_ratio = compute_difference_ratio(ref_processed, cur_processed)
        except Exception as exc:  # OpenCV/NumPy処理失敗を握りつぶしてunknownにする
            logger.error("detection failed: %s", exc)
            return DetectionResult(status="unknown", difference_ratio=None)

        status = self._classify(difference_ratio)
        return DetectionResult(status=status, difference_ratio=round(difference_ratio, 4))

    def _classify(self, difference_ratio: float) -> DetectionStatus:
        upper = self.occupied_threshold + self.uncertain_margin
        lower = self.occupied_threshold - self.uncertain_margin
        if difference_ratio >= upper:
            return "occupied"
        if difference_ratio <= lower:
            return "empty"
        return "unknown"
