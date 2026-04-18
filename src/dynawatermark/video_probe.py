from __future__ import annotations

import json
import subprocess
from fractions import Fraction
from pathlib import Path

from pydantic import BaseModel, Field


class VideoInfo(BaseModel):
    filename: str
    duration_sec: float = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    fps: float = Field(gt=0)


def _parse_fps(value: str) -> float:
    if "/" in value:
        fraction = Fraction(value)
        return float(fraction)
    return float(value)


def probe_video(path: Path) -> VideoInfo:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "v:0",
        "-show_entries",
        "stream=width,height,avg_frame_rate,duration",
        "-of",
        "json",
        str(path),
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=True)
    payload = json.loads(result.stdout)
    streams = payload.get("streams") or []
    if not streams:
        raise ValueError(f"No video stream found: {path}")

    stream = streams[0]
    duration = stream.get("duration")
    if duration is None:
        raise ValueError(f"Video duration is unavailable: {path}")

    return VideoInfo(
        filename=path.name,
        duration_sec=round(float(duration), 6),
        width=int(stream["width"]),
        height=int(stream["height"]),
        fps=round(_parse_fps(stream["avg_frame_rate"]), 6),
    )
