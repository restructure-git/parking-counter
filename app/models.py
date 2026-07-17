"""内部で使うドメインオブジェクト（DB ORMではなく単純なdataclass）。"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

DetectionStatus = Literal["empty", "occupied", "unknown"]


@dataclass
class ParkingSpace:
    id: int
    name: str
    x: int
    y: int
    width: int
    height: int

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ParkingSpace":
        return cls(
            id=int(data["id"]),
            name=str(data["name"]),
            x=int(data["x"]),
            y=int(data["y"]),
            width=int(data["width"]),
            height=int(data["height"]),
        )


@dataclass
class DetectionResult:
    status: DetectionStatus
    difference_ratio: float | None


@dataclass
class SpaceDetectionResult:
    space_id: int
    name: str
    status: DetectionStatus
    difference_ratio: float | None


@dataclass
class SpaceState:
    space_id: int
    confirmed_status: DetectionStatus
    pending_status: DetectionStatus | None = None
    pending_count: int = 0
