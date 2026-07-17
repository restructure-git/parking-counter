"""YOLO判定バックエンドの純粋な幾何計算部分のテスト。

ultralyticsパッケージ自体は重い依存（torch等）なので、ここでは
YoloParkingDetectorクラスは使わず、`from ultralytics import YOLO` を
一切要求しないモジュールレベル関数（overlap_ratio / best_overlap /
classify_overlap）だけを対象にする。
"""

from __future__ import annotations

from app.models import ParkingSpace
from app.services.yolo_detector import best_overlap, classify_overlap, overlap_ratio


def make_space(x: int = 0, y: int = 0, width: int = 100, height: int = 100) -> ParkingSpace:
    return ParkingSpace(id=1, name="A-01", x=x, y=y, width=width, height=height)


def test_overlap_ratio_full_coverage() -> None:
    space = make_space(0, 0, 100, 100)
    box = (0.0, 0.0, 100.0, 100.0)

    assert overlap_ratio(space, box) == 1.0


def test_overlap_ratio_no_overlap() -> None:
    space = make_space(0, 0, 100, 100)
    box = (200.0, 200.0, 300.0, 300.0)

    assert overlap_ratio(space, box) == 0.0


def test_overlap_ratio_partial_coverage() -> None:
    space = make_space(0, 0, 100, 100)
    # 右半分(50x100)だけ重なる矩形
    box = (50.0, 0.0, 150.0, 100.0)

    assert overlap_ratio(space, box) == 0.5


def test_overlap_ratio_zero_area_space_is_zero() -> None:
    space = make_space(0, 0, 0, 0)
    box = (0.0, 0.0, 100.0, 100.0)

    assert overlap_ratio(space, box) == 0.0


def test_best_overlap_picks_maximum() -> None:
    space = make_space(0, 0, 100, 100)
    boxes = [
        (0.0, 0.0, 10.0, 10.0),  # わずかな重なり
        (0.0, 0.0, 100.0, 100.0),  # 完全に重なる
    ]

    assert best_overlap(space, boxes) == 1.0


def test_best_overlap_with_no_boxes_is_zero() -> None:
    space = make_space(0, 0, 100, 100)

    assert best_overlap(space, []) == 0.0


def test_classify_overlap_occupied() -> None:
    assert classify_overlap(0.5, threshold=0.3, uncertain_margin=0.1) == "occupied"


def test_classify_overlap_empty() -> None:
    assert classify_overlap(0.05, threshold=0.3, uncertain_margin=0.1) == "empty"


def test_classify_overlap_unknown_in_margin() -> None:
    assert classify_overlap(0.25, threshold=0.3, uncertain_margin=0.1) == "unknown"
