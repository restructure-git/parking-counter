"""アプリ設定の読み込み。

設定ファイルが存在しない、または壊れている場合でもアプリ全体が
停止しないよう、デフォルト値にフォールバックする。
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_PATH = BASE_DIR / "config" / "settings.json"
DATA_DIR = BASE_DIR / "data"
REFERENCE_DIR = DATA_DIR / "reference"
PARKING_SPACES_PATH = DATA_DIR / "parking_spaces.json"
DB_PATH = DATA_DIR / "parking.db"
TMP_DIR = DATA_DIR / "tmp"

DEFAULT_SETTINGS: dict = {
    "occupied_threshold": 0.12,
    "uncertain_margin": 0.02,
    "required_consecutive_results": 3,
    "image_max_width": 1280,
    "max_upload_size_mb": 10,
    "detector_backend": "diff",
    "yolo_model_path": "yolov8n.pt",
    "yolo_confidence_threshold": 0.4,
    "yolo_overlap_threshold": 0.3,
    "yolo_uncertain_margin": 0.1,
}


class Settings(BaseModel):
    occupied_threshold: float = 0.12
    uncertain_margin: float = 0.02
    required_consecutive_results: int = 3
    image_max_width: int = 1280
    max_upload_size_mb: int = 10
    # "diff": 既存の画像差分方式（追加依存なし）。
    # "yolo": ローカル物体検出モデルで車両を検出し、駐車枠との重なりで判定する方式
    #         （requirements-yolo.txt のインストールが別途必要）。
    detector_backend: Literal["diff", "yolo"] = "diff"
    yolo_model_path: str = "yolov8n.pt"
    yolo_confidence_threshold: float = 0.4
    yolo_overlap_threshold: float = 0.3
    yolo_uncertain_margin: float = 0.1

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


def load_settings(path: Path = CONFIG_PATH) -> Settings:
    """設定ファイルを読み込む。存在しない/壊れている場合はデフォルトを使う。"""
    if not path.exists():
        logger.warning("settings file not found at %s, using defaults", path)
        return Settings(**DEFAULT_SETTINGS)

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("failed to load settings from %s: %s", path, exc)
        return Settings(**DEFAULT_SETTINGS)

    merged = {**DEFAULT_SETTINGS, **raw}
    try:
        return Settings(**merged)
    except Exception as exc:  # pydantic ValidationError etc.
        logger.error("invalid settings content in %s: %s", path, exc)
        return Settings(**DEFAULT_SETTINGS)


def ensure_data_dirs() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    REFERENCE_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)


settings = load_settings()
