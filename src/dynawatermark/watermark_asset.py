from __future__ import annotations

import mimetypes
from pathlib import Path

from PIL import Image
from pydantic import BaseModel, Field


class WatermarkAsset(BaseModel):
    asset_id: str
    filename: str
    type: str
    width: int = Field(gt=0)
    height: int = Field(gt=0)


def inspect_watermark_asset(path: Path, *, asset_id: str = "logo_01") -> WatermarkAsset:
    with Image.open(path) as image:
        width, height = image.size
    return WatermarkAsset(
        asset_id=asset_id,
        filename=path.name,
        type=mimetypes.guess_type(path.name)[0] or "application/octet-stream",
        width=width,
        height=height,
    )


def prepare_event_assets(
    watermark_paths: dict[str, Path],
    events: list[WatermarkEvent],
    temp_dir: Path,
) -> list[Path]:
    temp_dir.mkdir(parents=True, exist_ok=True)
    source_images: dict[str, Image.Image] = {}
    for asset_id, path in watermark_paths.items():
        with Image.open(path) as source:
            source_images[asset_id] = source.convert("RGBA")

    output_paths: list[Path] = []
    for event in events:
        base = source_images[event.asset_id]
        image = base.resize((event.width, event.height), Image.Resampling.LANCZOS)
        if event.opacity < 1:
            alpha = image.getchannel("A").point(lambda value: int(value * event.opacity))
            image.putalpha(alpha)
        output_path = temp_dir / f"{event.event_id}.png"
        image.save(output_path)
        output_paths.append(output_path)
    return output_paths
