from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from dynawatermark.config import WatermarkConfig
from dynawatermark.event_generator import WatermarkEvent
from dynawatermark.video_probe import VideoInfo
from dynawatermark.watermark_asset import WatermarkAsset


class VideoFileInfo(BaseModel):
    filename: str


class InputVideoMetadata(VideoFileInfo):
    duration_sec: float
    width: int
    height: int
    fps: float


class RenderJobMetadata(BaseModel):
    version: str = "1.0"
    job_id: str
    created_at: str
    input_video: InputVideoMetadata
    output_video: VideoFileInfo
    inspection_video: VideoFileInfo | None = None
    watermark_assets: list[WatermarkAsset]
    config: WatermarkConfig
    events: list[WatermarkEvent]


def make_job_id(created_at: datetime | None = None) -> str:
    timestamp = created_at or datetime.now(timezone.utc).astimezone()
    return f"wm_{timestamp.strftime('%Y%m%d_%H%M%S')}"


def build_metadata(
    *,
    job_id: str,
    input_path: Path,
    output_path: Path,
    inspection_path: Path | None,
    video: VideoInfo,
    assets: list[WatermarkAsset],
    config: WatermarkConfig,
    events: list[WatermarkEvent],
    created_at: datetime | None = None,
) -> RenderJobMetadata:
    created = created_at or datetime.now(timezone.utc).astimezone()
    return RenderJobMetadata(
        job_id=job_id,
        created_at=created.isoformat(timespec="seconds"),
        input_video=InputVideoMetadata(
            filename=input_path.name,
            duration_sec=video.duration_sec,
            width=video.width,
            height=video.height,
            fps=video.fps,
        ),
        output_video=VideoFileInfo(filename=output_path.name),
        inspection_video=(
            VideoFileInfo(filename=inspection_path.name)
            if inspection_path is not None
            else None
        ),
        watermark_assets=assets,
        config=config,
        events=events,
    )


def write_metadata(metadata: RenderJobMetadata, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = metadata.model_dump(mode="json")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_metadata(path: Path) -> RenderJobMetadata:
    with path.open("r", encoding="utf-8") as file:
        return RenderJobMetadata.model_validate(json.load(file))
