from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class ConfigError(ValueError):
    pass


class WatermarkAssetConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str
    path: Path | None = None
    frequency_weight: float = Field(default=1.0, gt=0)
    opacity: float | None = Field(default=None, ge=0, le=1)
    opacity_range: tuple[float, float] | None = None
    size_ratio: float | None = Field(default=None, gt=0)
    size_range_ratio: tuple[float, float] | None = None

    @field_validator("opacity_range")
    @classmethod
    def validate_opacity_range(cls, value: tuple[float, float] | None) -> tuple[float, float] | None:
        if value is None:
            return value
        low, high = value
        if low < 0 or high > 1:
            raise ValueError("opacity_range must be within 0..1")
        if low > high:
            raise ValueError("opacity_range minimum cannot exceed maximum")
        return value

    @field_validator("size_range_ratio")
    @classmethod
    def validate_size_range(cls, value: tuple[float, float] | None) -> tuple[float, float] | None:
        if value is None:
            return value
        low, high = value
        if low <= 0 or high <= 0:
            raise ValueError("size_range_ratio values must be positive")
        if low > high:
            raise ValueError("size_range_ratio minimum cannot exceed maximum")
        return value


class ScheduledWatermarkConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    asset_id: str
    start_time_sec: float = Field(ge=0)
    duration_sec: float = Field(gt=0)
    x: int | None = Field(default=None, ge=0)
    y: int | None = Field(default=None, ge=0)
    width: int | None = Field(default=None, gt=0)
    height: int | None = Field(default=None, gt=0)
    size_ratio: float | None = Field(default=None, gt=0)
    opacity: float | None = Field(default=None, ge=0, le=1)

    @model_validator(mode="after")
    def validate_size(self) -> ScheduledWatermarkConfig:
        if (self.width is None) != (self.height is None):
            raise ValueError("width and height must be set together")
        if self.size_ratio is not None and self.width is not None:
            raise ValueError("Use either size_ratio or width/height, not both")
        return self


class WatermarkConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["random", "scheduled"] = "random"
    seed: int = 0
    max_events: int = Field(default=25, ge=1, le=500)
    opacity_range: tuple[float, float] = (0.2, 0.4)
    duration_range_sec: tuple[float, float] = (0.8, 2.0)
    size_range_ratio: tuple[float, float] = (0.08, 0.15)
    position_strategy: Literal["random"] = "random"
    margin_ratio: float = Field(default=0.03, ge=0.0, lt=0.5)
    allow_rotation: bool = False
    assets: list[WatermarkAssetConfig] = Field(default_factory=list)
    scheduled_events: list[ScheduledWatermarkConfig] = Field(default_factory=list)

    @field_validator("opacity_range")
    @classmethod
    def validate_opacity_range(cls, value: tuple[float, float]) -> tuple[float, float]:
        low, high = value
        if low < 0 or high > 1:
            raise ValueError("opacity_range must be within 0..1")
        if low > high:
            raise ValueError("opacity_range minimum cannot exceed maximum")
        return value

    @field_validator("duration_range_sec", "size_range_ratio")
    @classmethod
    def validate_positive_range(cls, value: tuple[float, float]) -> tuple[float, float]:
        low, high = value
        if low <= 0 or high <= 0:
            raise ValueError("range values must be positive")
        if low > high:
            raise ValueError("range minimum cannot exceed maximum")
        return value

    @model_validator(mode="after")
    def validate_rotation(self) -> WatermarkConfig:
        if self.allow_rotation:
            raise ValueError("allow_rotation is reserved for a later version")
        if self.mode == "scheduled" and not self.scheduled_events:
            raise ValueError("scheduled mode requires scheduled_events")
        return self


def load_config(path: Path) -> WatermarkConfig:
    try:
        with path.open("r", encoding="utf-8") as file:
            payload = json.load(file)
    except json.JSONDecodeError as error:
        raise ConfigError(
            f"{path} 不是合法 JSON：第 {error.lineno} 行第 {error.colno} 欄，{error.msg}"
        ) from error
    try:
        return WatermarkConfig.model_validate(payload)
    except ValueError as error:
        raise ConfigError(f"{path} 設定不合法：{error}") from error
