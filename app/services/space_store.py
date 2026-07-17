"""駐車枠定義（data/parking_spaces.json）の読み書き。"""

from __future__ import annotations

import json
import logging
import threading

from app.config import PARKING_SPACES_PATH
from app.models import ParkingSpace

logger = logging.getLogger(__name__)

_lock = threading.Lock()


def load_spaces() -> list[ParkingSpace]:
    """駐車枠一覧を読み込む。ファイルが無い/壊れている場合は空リストを返す。"""
    if not PARKING_SPACES_PATH.exists():
        logger.warning("parking_spaces.json not found at %s", PARKING_SPACES_PATH)
        return []
    try:
        raw = json.loads(PARKING_SPACES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("failed to read parking_spaces.json: %s", exc)
        return []

    if not isinstance(raw, list):
        logger.error("parking_spaces.json is not a list")
        return []

    spaces: list[ParkingSpace] = []
    for item in raw:
        try:
            spaces.append(ParkingSpace.from_dict(item))
        except (KeyError, ValueError, TypeError) as exc:
            logger.error("skipping invalid parking space entry %s: %s", item, exc)
    return spaces


def save_spaces(spaces: list[ParkingSpace]) -> bool:
    try:
        PARKING_SPACES_PATH.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = PARKING_SPACES_PATH.with_suffix(".json.tmp")
        tmp_path.write_text(
            json.dumps([s.to_dict() for s in spaces], ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        tmp_path.replace(PARKING_SPACES_PATH)
        return True
    except OSError as exc:
        logger.error("failed to save parking_spaces.json: %s", exc)
        return False


def next_space_id(spaces: list[ParkingSpace]) -> int:
    if not spaces:
        return 1
    return max(s.id for s in spaces) + 1


def add_space(name: str, x: int, y: int, width: int, height: int) -> ParkingSpace:
    with _lock:
        spaces = load_spaces()
        new_space = ParkingSpace(
            id=next_space_id(spaces), name=name, x=x, y=y, width=width, height=height
        )
        spaces.append(new_space)
        save_spaces(spaces)
        return new_space


def update_space(
    space_id: int,
    name: str,
    x: int,
    y: int,
    width: int,
    height: int,
) -> ParkingSpace | None:
    with _lock:
        spaces = load_spaces()
        for i, space in enumerate(spaces):
            if space.id == space_id:
                updated = ParkingSpace(id=space_id, name=name, x=x, y=y, width=width, height=height)
                spaces[i] = updated
                save_spaces(spaces)
                return updated
        return None


def delete_space(space_id: int) -> bool:
    with _lock:
        spaces = load_spaces()
        remaining = [s for s in spaces if s.id != space_id]
        if len(remaining) == len(spaces):
            return False
        save_spaces(remaining)
        return True
