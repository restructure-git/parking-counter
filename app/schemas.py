"""APIの入出力に使うPydanticスキーマ。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Status = Literal["empty", "occupied", "unknown"]


class SpaceStatus(BaseModel):
    id: int
    name: str
    status: Status
    difference_ratio: float | None = None


class ParkingStatusResponse(BaseModel):
    updated_at: str | None
    total: int
    empty: int
    occupied: int
    unknown: int
    spaces: list[SpaceStatus]


class ParkingSpaceIn(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class ParkingSpaceOut(ParkingSpaceIn):
    id: int


class DetectionHistoryItem(BaseModel):
    id: int
    detected_at: str
    total_spaces: int
    empty_count: int
    occupied_count: int
    unknown_count: int


class HealthResponse(BaseModel):
    status: str = "ok"
