from __future__ import annotations

import json
import subprocess
from fractions import Fraction
from pathlib import Path

from pydantic import BaseModel, Field

from dynawatermark.errors import FfmpegNotFoundError, VideoProbeError


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
    try:
        result = subprocess.run(command, capture_output=True, text=True, check=True)
    except FileNotFoundError as error:
        raise FfmpegNotFoundError("找不到 ffprobe，請先安裝 FFmpeg 並確認 ffprobe 在 PATH 內。") from error
    except subprocess.CalledProcessError as error:
        message = error.stderr.strip() or error.stdout.strip() or str(error)
        raise VideoProbeError(f"ffprobe 無法讀取影片：{path}。{message}") from error

    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise VideoProbeError(f"ffprobe 輸出不是合法 JSON：{path}") from error
    streams = payload.get("streams") or []
    if not streams:
        raise VideoProbeError(f"找不到影片串流：{path}")

    stream = streams[0]
    duration = stream.get("duration")
    if duration is None:
        raise VideoProbeError(f"無法取得影片長度：{path}")

    return VideoInfo(
        filename=path.name,
        duration_sec=round(float(duration), 6),
        width=int(stream["width"]),
        height=int(stream["height"]),
        fps=round(_parse_fps(stream["avg_frame_rate"]), 6),
    )
