from __future__ import annotations

import random

from pydantic import BaseModel, Field

from dynawatermark.config import ScheduledWatermarkConfig, WatermarkAssetConfig, WatermarkConfig
from dynawatermark.video_probe import VideoInfo
from dynawatermark.watermark_asset import WatermarkAsset


class WatermarkEvent(BaseModel):
    event_id: str
    start_time_sec: float = Field(ge=0)
    end_time_sec: float = Field(ge=0)
    duration_sec: float = Field(gt=0)
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    opacity: float = Field(ge=0, le=1)
    rotation_deg: float = 0.0
    asset_id: str


def generate_events(
    video: VideoInfo,
    config: WatermarkConfig,
    *,
    assets: dict[str, WatermarkAsset],
) -> list[WatermarkEvent]:
    if video.duration_sec <= 0:
        return []
    if not assets:
        raise ValueError("At least one watermark asset is required")

    if config.mode == "scheduled":
        return generate_scheduled_events(video, config, assets=assets)

    rng = random.Random(config.seed)
    margin_x = int(video.width * config.margin_ratio)
    margin_y = int(video.height * config.margin_ratio)
    usable_width = max(1, video.width - margin_x * 2)
    usable_height = max(1, video.height - margin_y * 2)
    asset_configs = _asset_configs(config, assets)
    events: list[WatermarkEvent] = []

    for index in range(config.max_events):
        asset_config = _choose_asset_config(rng, asset_configs)
        asset = assets[asset_config.asset_id]
        aspect_ratio = asset.height / asset.width
        duration = min(
            rng.uniform(*config.duration_range_sec),
            max(0.001, video.duration_sec),
        )
        max_start = max(0.0, video.duration_sec - duration)
        start = rng.uniform(0, max_start) if max_start > 0 else 0.0
        ratio = _pick_size_ratio(rng, config, asset_config)
        width, height = _fit_size(
            width=max(1, int(round(video.width * ratio))),
            height=max(1, int(round(video.width * ratio * aspect_ratio))),
            max_width=usable_width,
            max_height=usable_height,
        )

        if width > usable_width:
            scale = usable_width / width
            width = max(1, int(round(width * scale)))
            height = max(1, int(round(height * scale)))
        if height > usable_height:
            scale = usable_height / height
            width = max(1, int(round(width * scale)))
            height = max(1, int(round(height * scale)))

        max_x = max(margin_x, video.width - margin_x - width)
        max_y = max(margin_y, video.height - margin_y - height)
        x = rng.randint(margin_x, max_x) if max_x >= margin_x else 0
        y = rng.randint(margin_y, max_y) if max_y >= margin_y else 0
        opacity = _pick_opacity(rng, config, asset_config)

        events.append(
            WatermarkEvent(
                event_id=f"evt_{index + 1:04d}",
                start_time_sec=round(start, 3),
                end_time_sec=round(start + duration, 3),
                duration_sec=round(duration, 3),
                x=x,
                y=y,
                width=width,
                height=height,
                opacity=round(opacity, 3),
                rotation_deg=0.0,
                asset_id=asset.asset_id,
            )
        )

    return sorted(events, key=lambda event: event.start_time_sec)


def generate_scheduled_events(
    video: VideoInfo,
    config: WatermarkConfig,
    *,
    assets: dict[str, WatermarkAsset],
) -> list[WatermarkEvent]:
    events: list[WatermarkEvent] = []
    asset_configs = {asset.asset_id: asset for asset in _asset_configs(config, assets)}
    margin_x = int(video.width * config.margin_ratio)
    margin_y = int(video.height * config.margin_ratio)

    for index, scheduled in enumerate(config.scheduled_events, start=1):
        if scheduled.asset_id not in assets:
            raise ValueError(f"Unknown scheduled asset_id: {scheduled.asset_id}")
        asset = assets[scheduled.asset_id]
        asset_config = asset_configs[scheduled.asset_id]
        duration = min(scheduled.duration_sec, max(0.001, video.duration_sec - scheduled.start_time_sec))
        if duration <= 0:
            raise ValueError(f"scheduled event starts after video end: {scheduled.asset_id}")
        width, height = _scheduled_size(video, asset, scheduled, asset_config, config)
        max_x = max(0, video.width - width)
        max_y = max(0, video.height - height)
        x = min(scheduled.x if scheduled.x is not None else margin_x, max_x)
        y = min(scheduled.y if scheduled.y is not None else margin_y, max_y)
        opacity = scheduled.opacity
        if opacity is None:
            opacity = asset_config.opacity if asset_config.opacity is not None else config.opacity_range[0]

        events.append(
            WatermarkEvent(
                event_id=f"evt_{index:04d}",
                start_time_sec=round(scheduled.start_time_sec, 3),
                end_time_sec=round(scheduled.start_time_sec + duration, 3),
                duration_sec=round(duration, 3),
                x=x,
                y=y,
                width=width,
                height=height,
                opacity=round(opacity, 3),
                rotation_deg=0.0,
                asset_id=asset.asset_id,
            )
        )

    return sorted(events, key=lambda event: event.start_time_sec)


def _asset_configs(config: WatermarkConfig, assets: dict[str, WatermarkAsset]) -> list[WatermarkAssetConfig]:
    configured = {asset.asset_id: asset for asset in config.assets}
    output: list[WatermarkAssetConfig] = []
    for asset_id in assets:
        output.append(configured.get(asset_id) or WatermarkAssetConfig(asset_id=asset_id))
    return output


def _choose_asset_config(rng: random.Random, assets: list[WatermarkAssetConfig]) -> WatermarkAssetConfig:
    total = sum(asset.frequency_weight for asset in assets)
    point = rng.uniform(0, total)
    cursor = 0.0
    for asset in assets:
        cursor += asset.frequency_weight
        if point <= cursor:
            return asset
    return assets[-1]


def _pick_opacity(rng: random.Random, config: WatermarkConfig, asset: WatermarkAssetConfig) -> float:
    if asset.opacity is not None:
        return asset.opacity
    if asset.opacity_range is not None:
        return rng.uniform(*asset.opacity_range)
    return rng.uniform(*config.opacity_range)


def _pick_size_ratio(rng: random.Random, config: WatermarkConfig, asset: WatermarkAssetConfig) -> float:
    if asset.size_ratio is not None:
        return asset.size_ratio
    if asset.size_range_ratio is not None:
        return rng.uniform(*asset.size_range_ratio)
    return rng.uniform(*config.size_range_ratio)


def _fit_size(*, width: int, height: int, max_width: int, max_height: int) -> tuple[int, int]:
    if width > max_width:
        scale = max_width / width
        width = max(1, int(round(width * scale)))
        height = max(1, int(round(height * scale)))
    if height > max_height:
        scale = max_height / height
        width = max(1, int(round(width * scale)))
        height = max(1, int(round(height * scale)))
    return width, height


def _scheduled_size(
    video: VideoInfo,
    asset: WatermarkAsset,
    scheduled: ScheduledWatermarkConfig,
    asset_config: WatermarkAssetConfig,
    config: WatermarkConfig,
) -> tuple[int, int]:
    if scheduled.width is not None and scheduled.height is not None:
        width, height = scheduled.width, scheduled.height
    else:
        ratio = scheduled.size_ratio or asset_config.size_ratio
        if ratio is None and asset_config.size_range_ratio is not None:
            ratio = asset_config.size_range_ratio[0]
        if ratio is None:
            ratio = config.size_range_ratio[0]
        width = max(1, int(round(video.width * ratio)))
        height = max(1, int(round(width * asset.height / asset.width)))
    return _fit_size(width=width, height=height, max_width=video.width, max_height=video.height)
