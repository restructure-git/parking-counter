from __future__ import annotations

import numpy as np

from app.models import ParkingSpace
from app.services.image_processor import crop_space, decode_image
from app.services.parking_detector import ParkingDetector
from scripts.create_sample_data import (
    make_flat_image,
    make_invalid_image_bytes,
    make_occupied_image,
    make_partial_occupied_image,
    make_slightly_brighter,
)


def make_detector(
    occupied_threshold: float = 0.12, uncertain_margin: float = 0.02
) -> ParkingDetector:
    return ParkingDetector(occupied_threshold=occupied_threshold, uncertain_margin=uncertain_margin)


def test_same_image_is_empty() -> None:
    detector = make_detector()
    reference = make_flat_image()
    current = make_flat_image()

    result = detector.detect(reference, current)

    assert result.status == "empty"
    assert result.difference_ratio is not None
    assert result.difference_ratio < 0.10


def test_brightness_change_alone_stays_empty() -> None:
    """日照変化程度の明るさ差では使用中と誤判定しないこと。"""
    detector = make_detector()
    reference = make_flat_image()
    current = make_slightly_brighter(reference, delta=20)

    result = detector.detect(reference, current)

    assert result.status == "empty"


def test_large_difference_is_occupied() -> None:
    detector = make_detector()
    reference = make_flat_image()
    current = make_occupied_image()

    result = detector.detect(reference, current)

    assert result.status == "occupied"
    assert result.difference_ratio is not None
    assert result.difference_ratio > 0.14


def test_boundary_difference_is_unknown() -> None:
    detector = make_detector(occupied_threshold=0.12, uncertain_margin=0.02)
    reference = make_flat_image()
    # 12%前後だけ覆われた画像 = しきい値の境界付近を狙う
    current = make_partial_occupied_image(coverage=0.12)

    result = detector.detect(reference, current)

    assert result.status == "unknown"


def test_missing_reference_returns_unknown() -> None:
    detector = make_detector()

    result = detector.detect(None, make_flat_image())

    assert result.status == "unknown"
    assert result.difference_ratio is None


def test_missing_current_returns_unknown() -> None:
    detector = make_detector()

    result = detector.detect(make_flat_image(), None)

    assert result.status == "unknown"
    assert result.difference_ratio is None


def test_empty_array_returns_unknown() -> None:
    detector = make_detector()
    empty_array = np.zeros((0, 0, 3), dtype=np.uint8)

    result = detector.detect(empty_array, make_flat_image())

    assert result.status == "unknown"


def test_decode_invalid_image_returns_none() -> None:
    assert decode_image(make_invalid_image_bytes()) is None


def test_decode_empty_bytes_returns_none() -> None:
    assert decode_image(b"") is None


def test_crop_space_out_of_bounds_returns_none() -> None:
    image = make_flat_image(width=100, height=100)
    space = ParkingSpace(id=1, name="A-01", x=500, y=500, width=50, height=50)

    assert crop_space(image, space) is None


def test_crop_space_within_bounds() -> None:
    image = make_flat_image(width=100, height=100)
    space = ParkingSpace(id=1, name="A-01", x=10, y=10, width=50, height=50)

    cropped = crop_space(image, space)

    assert cropped is not None
    assert cropped.shape[:2] == (50, 50)
