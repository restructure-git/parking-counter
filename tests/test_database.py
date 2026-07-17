from __future__ import annotations

from pathlib import Path

from app.database import get_recent_detections, init_db, save_detection
from app.models import SpaceDetectionResult


def test_save_and_read_detection(tmp_path: Path) -> None:
    db_path = tmp_path / "test.db"
    init_db(db_path)

    results = [
        SpaceDetectionResult(space_id=1, name="A-01", status="empty", difference_ratio=0.02),
        SpaceDetectionResult(space_id=2, name="A-02", status="occupied", difference_ratio=0.3),
    ]

    detection_id = save_detection(
        empty_count=1, occupied_count=1, unknown_count=0, space_results=results, db_path=db_path
    )

    assert detection_id is not None

    history = get_recent_detections(limit=10, db_path=db_path)
    assert len(history) == 1
    assert history[0]["total_spaces"] == 2
    assert history[0]["empty_count"] == 1
    assert history[0]["occupied_count"] == 1


def test_get_recent_detections_empty_db(tmp_path: Path) -> None:
    db_path = tmp_path / "empty.db"
    init_db(db_path)

    history = get_recent_detections(limit=10, db_path=db_path)

    assert history == []


def test_get_recent_detections_missing_db_does_not_raise(tmp_path: Path) -> None:
    db_path = tmp_path / "does_not_exist.db"

    history = get_recent_detections(limit=10, db_path=db_path)

    assert history == []
