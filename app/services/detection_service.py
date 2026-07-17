"""判定パイプライン全体をまとめるオーケストレーション層。

画像デコード → 駐車枠ごとの切り出し → 判定 → 連続判定による確定
→ DB保存 → 結果画像の一時保存、までを担当する。
"""

from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from datetime import datetime

import cv2
import numpy as np

from app.config import TMP_DIR, settings
from app.database import save_detection
from app.models import DetectionResult, ParkingSpace, SpaceDetectionResult
from app.services import reference_manager, space_store
from app.services.image_processor import crop_space, decode_image, resize_max_width
from app.services.parking_detector import ParkingDetector
from app.services.state_manager import StateManager
from app.services.yolo_detector import YoloParkingDetector

logger = logging.getLogger(__name__)

ANNOTATED_IMAGE_PATH = TMP_DIR / "latest_annotated.jpg"

STATUS_COLORS_BGR = {
    "empty": (0, 170, 0),
    "occupied": (0, 0, 220),
    "unknown": (0, 210, 230),
}


def _build_detector() -> tuple[ParkingDetector | YoloParkingDetector, str]:
    """設定に応じた判定バックエンドを組み立てる。

    YOLOが要求されているのに初期化できない場合（未インストール等）は、
    アプリ全体を止めずに従来の画像差分方式へフォールバックする。
    """
    if settings.detector_backend == "yolo":
        try:
            yolo_detector = YoloParkingDetector(
                model_path=settings.yolo_model_path,
                confidence_threshold=settings.yolo_confidence_threshold,
                overlap_threshold=settings.yolo_overlap_threshold,
                uncertain_margin=settings.yolo_uncertain_margin,
            )
            return yolo_detector, "yolo"
        except Exception:
            logger.exception(
                "failed to initialize YOLO detector; falling back to diff-based detector"
            )

    diff_detector = ParkingDetector(
        occupied_threshold=settings.occupied_threshold,
        uncertain_margin=settings.uncertain_margin,
    )
    return diff_detector, "diff"


detector, detector_backend = _build_detector()
state_manager = StateManager(required_consecutive_results=settings.required_consecutive_results)


@dataclass
class SystemStatus:
    updated_at: str | None = None
    spaces: list[SpaceDetectionResult] = field(default_factory=list)


_status = SystemStatus()
_status_lock = threading.Lock()


def get_status() -> SystemStatus:
    with _status_lock:
        return SystemStatus(updated_at=_status.updated_at, spaces=list(_status.spaces))


def _run_raw_detection(image: np.ndarray, spaces: list[ParkingSpace]) -> dict[int, DetectionResult]:
    """設定された判定バックエンドで、駐車枠ごとの生の判定結果を得る。"""
    if isinstance(detector, YoloParkingDetector):
        return detector.detect_all(image, spaces)

    results: dict[int, DetectionResult] = {}
    for space in spaces:
        reference = reference_manager.load_reference(space.id)
        current_crop = crop_space(image, space)
        results[space.id] = detector.detect(reference, current_crop)
    return results


def run_detection(image_bytes: bytes) -> list[SpaceDetectionResult] | None:
    """アップロードされた駐車場全体画像1枚から、全駐車枠を判定する。

    戻り値はNone: 画像デコード失敗。空リスト: 駐車枠が未登録。
    """
    logger.info("received image for detection (%d bytes)", len(image_bytes))
    image = decode_image(image_bytes)
    if image is None:
        logger.error("uploaded image could not be decoded")
        return None

    image = resize_max_width(image, settings.image_max_width)
    spaces = space_store.load_spaces()
    if not spaces:
        logger.warning("no parking spaces registered; skipping detection")
        return []

    logger.info("detection started for %d spaces (backend=%s)", len(spaces), detector_backend)

    raw_by_space = _run_raw_detection(image, spaces)

    raw_results: list[SpaceDetectionResult] = []
    confirmed_results: list[SpaceDetectionResult] = []

    for space in spaces:
        result = raw_by_space[space.id]
        state = state_manager.update(space.id, result.status)

        logger.info(
            "space %s (%s): raw=%s confirmed=%s ratio=%s",
            space.id,
            space.name,
            result.status,
            state.confirmed_status,
            result.difference_ratio,
        )

        raw_results.append(
            SpaceDetectionResult(
                space_id=space.id,
                name=space.name,
                status=result.status,
                difference_ratio=result.difference_ratio,
            )
        )
        confirmed_results.append(
            SpaceDetectionResult(
                space_id=space.id,
                name=space.name,
                status=state.confirmed_status,
                difference_ratio=result.difference_ratio,
            )
        )

    counts = _count_by_status(confirmed_results)
    save_detection(
        empty_count=counts["empty"],
        occupied_count=counts["occupied"],
        unknown_count=counts["unknown"],
        space_results=raw_results,
    )

    with _status_lock:
        _status.updated_at = datetime.now().isoformat(timespec="seconds")
        _status.spaces = confirmed_results

    _save_annotated_image(image, spaces, confirmed_results)

    logger.info("detection finished: %s", counts)
    return confirmed_results


def _count_by_status(results: list[SpaceDetectionResult]) -> dict[str, int]:
    counts = {"empty": 0, "occupied": 0, "unknown": 0}
    for r in results:
        counts[r.status] = counts.get(r.status, 0) + 1
    return counts


def build_status_payload() -> dict:
    """/api/status および /api/detect のレスポンス用データを組み立てる。"""
    status = get_status()
    counts = _count_by_status(status.spaces)
    return {
        "updated_at": status.updated_at,
        "total": len(status.spaces),
        "empty": counts["empty"],
        "occupied": counts["occupied"],
        "unknown": counts["unknown"],
        "spaces": [
            {
                "id": s.space_id,
                "name": s.name,
                "status": s.status,
                "difference_ratio": s.difference_ratio,
            }
            for s in status.spaces
        ],
    }


def _save_annotated_image(
    image: np.ndarray,
    spaces: list[ParkingSpace],
    results: list[SpaceDetectionResult],
) -> None:
    """駐車枠を色分けした矩形で重ね描きし、一時ファイルとして保存する（上書き運用）。"""
    try:
        annotated = image.copy()
        status_by_id = {r.space_id: r.status for r in results}
        for space in spaces:
            status = status_by_id.get(space.id, "unknown")
            color = STATUS_COLORS_BGR.get(status, STATUS_COLORS_BGR["unknown"])
            top_left = (space.x, space.y)
            bottom_right = (space.x + space.width, space.y + space.height)
            cv2.rectangle(annotated, top_left, bottom_right, color, thickness=3)
            cv2.putText(
                annotated,
                space.name,
                (space.x + 4, max(space.y + 18, 18)),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2,
                cv2.LINE_AA,
            )
        TMP_DIR.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(ANNOTATED_IMAGE_PATH), annotated)
    except Exception as exc:  # 描画失敗は判定結果に影響させない
        logger.error("failed to save annotated image: %s", exc)
