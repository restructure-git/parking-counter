"""テスト・動作確認用のサンプル画像をプログラムで生成する。

実在する駐車場画像はリポジトリに含めない方針のため、単色矩形などの
合成画像のみを扱う。
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def make_flat_image(
    width: int = 100,
    height: int = 100,
    color: tuple[int, int, int] = (180, 180, 180),
) -> np.ndarray:
    """単色の「空き枠」を模した画像を作る（アスファルト風グレー）。"""
    image = np.full((height, width, 3), color, dtype=np.uint8)
    noise = np.random.default_rng(0).integers(-3, 3, image.shape, dtype=np.int16)
    return np.clip(image.astype(np.int16) + noise, 0, 255).astype(np.uint8)


def make_occupied_image(
    width: int = 100,
    height: int = 100,
    bg_color: tuple[int, int, int] = (180, 180, 180),
    car_color: tuple[int, int, int] = (30, 30, 200),
) -> np.ndarray:
    """空き画像の上に「車」を模した矩形を重ねた画像を作る。"""
    image = make_flat_image(width, height, bg_color)
    margin_x = max(1, width // 10)
    margin_y = max(1, height // 10)
    cv2.rectangle(
        image,
        (margin_x, margin_y),
        (width - margin_x, height - margin_y),
        car_color,
        thickness=-1,
    )
    return image


def make_slightly_brighter(image: np.ndarray, delta: int = 15) -> np.ndarray:
    """明るさだけ変化させた画像（誤検知しないことの確認用）。"""
    shifted = image.astype(np.int16) + delta
    return np.clip(shifted, 0, 255).astype(np.uint8)


def make_partial_occupied_image(
    width: int = 100,
    height: int = 100,
    bg_color: tuple[int, int, int] = (180, 180, 180),
    car_color: tuple[int, int, int] = (30, 30, 200),
    coverage: float = 0.5,
) -> np.ndarray:
    """枠の一部だけ覆う画像（境界値/unknown確認用）。"""
    image = make_flat_image(width, height, bg_color)
    covered_height = int(height * coverage)
    cv2.rectangle(
        image,
        (0, height - covered_height),
        (width, height),
        car_color,
        thickness=-1,
    )
    return image


def make_invalid_image_bytes() -> bytes:
    """画像として壊れているバイト列を返す。"""
    return b"not-a-real-image-file"


def _save_demo_set(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    cv2.imwrite(str(output_dir / "sample_empty.jpg"), make_flat_image())
    cv2.imwrite(str(output_dir / "sample_occupied.jpg"), make_occupied_image())
    cv2.imwrite(str(output_dir / "sample_partial.jpg"), make_partial_occupied_image())


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="サンプル画像を生成する")
    parser.add_argument(
        "--output",
        default="scratch/sample_images",
        help="出力先ディレクトリ（デフォルト: scratch/sample_images）",
    )
    args = parser.parse_args()
    _save_demo_set(Path(args.output))
    print(f"sample images written to {args.output}")
