from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel

from dynawatermark.config import WatermarkConfig
from dynawatermark.event_generator import WatermarkEvent
from dynawatermark.hashing import canonical_json_sha256, file_sha256
from dynawatermark.video_probe import VideoInfo
from dynawatermark.watermark_asset import WatermarkAsset


class VideoHashInfo(BaseModel):
    filename: str
    sha256: str


class InputVideoMetadata(VideoHashInfo):
    duration_sec: float
    width: int
    height: int
    fps: float


class IntegrityInfo(BaseModel):
    config_sha256: str
    metadata_sha256: str | None = None


class RenderJobMetadata(BaseModel):
    version: str = "1.0"
    job_id: str
    created_at: str
    input_video: InputVideoMetadata
    output_video: VideoHashInfo
    watermark_assets: list[WatermarkAsset]
    config: WatermarkConfig
    events: list[WatermarkEvent]
    integrity: IntegrityInfo


def make_job_id(created_at: datetime | None = None) -> str:
    timestamp = created_at or datetime.now(timezone.utc).astimezone()
    return f"wm_{timestamp.strftime('%Y%m%d_%H%M%S')}"


def build_metadata(
    *,
    job_id: str,
    input_path: Path,
    output_path: Path,
    video: VideoInfo,
    assets: list[WatermarkAsset],
    config: WatermarkConfig,
    events: list[WatermarkEvent],
    created_at: datetime | None = None,
) -> RenderJobMetadata:
    created = created_at or datetime.now(timezone.utc).astimezone()
    metadata = RenderJobMetadata(
        job_id=job_id,
        created_at=created.isoformat(timespec="seconds"),
        input_video=InputVideoMetadata(
            filename=input_path.name,
            sha256=file_sha256(input_path),
            duration_sec=video.duration_sec,
            width=video.width,
            height=video.height,
            fps=video.fps,
        ),
        output_video=VideoHashInfo(filename=output_path.name, sha256=file_sha256(output_path)),
        watermark_assets=assets,
        config=config,
        events=events,
        integrity=IntegrityInfo(config_sha256=canonical_json_sha256(config)),
    )
    metadata.integrity.metadata_sha256 = metadata_sha256(metadata)
    return metadata


def metadata_sha256(metadata: RenderJobMetadata) -> str:
    payload = metadata.model_copy(deep=True)
    payload.integrity.metadata_sha256 = None
    return canonical_json_sha256(payload)


def write_metadata(metadata: RenderJobMetadata, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = metadata.model_dump(mode="json")
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def read_metadata(path: Path) -> RenderJobMetadata:
    with path.open("r", encoding="utf-8") as file:
        return RenderJobMetadata.model_validate(json.load(file))
