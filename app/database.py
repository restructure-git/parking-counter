"""SQLiteアクセス層。SQLAlchemyは使わず標準sqlite3を利用する。"""

from __future__ import annotations

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Iterator

from app.config import DB_PATH, ensure_data_dirs
from app.models import SpaceDetectionResult

logger = logging.getLogger(__name__)

_SCHEMA = """
CREATE TABLE IF NOT EXISTS detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    detected_at TEXT NOT NULL,
    total_spaces INTEGER NOT NULL,
    empty_count INTEGER NOT NULL,
    occupied_count INTEGER NOT NULL,
    unknown_count INTEGER NOT NULL
);

CREATE TABLE IF NOT EXISTS space_detections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    detection_id INTEGER NOT NULL,
    space_id INTEGER NOT NULL,
    status TEXT NOT NULL,
    difference_ratio REAL,
    FOREIGN KEY (detection_id) REFERENCES detections (id)
);

CREATE INDEX IF NOT EXISTS idx_space_detections_detection_id
    ON space_detections (detection_id);
"""


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    ensure_data_dirs()
    conn = sqlite3.connect(str(db_path or DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


@contextmanager
def connect(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    conn = get_connection(db_path)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db(db_path: Path | None = None) -> None:
    try:
        with connect(db_path) as conn:
            conn.executescript(_SCHEMA)
        logger.info("database initialized at %s", db_path or DB_PATH)
    except sqlite3.Error as exc:
        logger.error("failed to initialize database: %s", exc)
        raise


def save_detection(
    empty_count: int,
    occupied_count: int,
    unknown_count: int,
    space_results: list[SpaceDetectionResult],
    db_path: Path | None = None,
) -> int | None:
    """1回分の判定サイクルを履歴テーブルへ保存する。失敗してもアプリは継続する。"""
    detected_at = datetime.now().isoformat(timespec="seconds")
    total = empty_count + occupied_count + unknown_count
    try:
        with connect(db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO detections
                    (detected_at, total_spaces, empty_count, occupied_count, unknown_count)
                VALUES (?, ?, ?, ?, ?)
                """,
                (detected_at, total, empty_count, occupied_count, unknown_count),
            )
            detection_id = cursor.lastrowid
            conn.executemany(
                """
                INSERT INTO space_detections
                    (detection_id, space_id, status, difference_ratio)
                VALUES (?, ?, ?, ?)
                """,
                [(detection_id, r.space_id, r.status, r.difference_ratio) for r in space_results],
            )
        logger.info("saved detection %s (total=%s)", detection_id, total)
        return detection_id
    except sqlite3.Error as exc:
        logger.error("failed to save detection history: %s", exc)
        return None


def get_recent_detections(limit: int = 100, db_path: Path | None = None) -> list[dict]:
    try:
        with connect(db_path) as conn:
            rows = conn.execute(
                """
                SELECT id, detected_at, total_spaces, empty_count, occupied_count, unknown_count
                FROM detections
                ORDER BY id DESC
                LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]
    except sqlite3.Error as exc:
        logger.error("failed to read detection history: %s", exc)
        return []
