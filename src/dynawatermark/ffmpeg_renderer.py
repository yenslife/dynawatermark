from __future__ import annotations

import subprocess
from pathlib import Path

from dynawatermark.event_generator import WatermarkEvent


def render_video(
    *,
    input_video: Path,
    event_asset_paths: list[Path],
    events: list[WatermarkEvent],
    output_video: Path,
) -> None:
    output_video.parent.mkdir(parents=True, exist_ok=True)
    if len(event_asset_paths) != len(events):
        raise ValueError("event_asset_paths and events must have the same length")

    command = ["ffmpeg", "-y", "-i", str(input_video)]
    for path in event_asset_paths:
        command.extend(["-i", str(path)])

    filter_parts: list[str] = []
    current_label = "[0:v]"
    for index, event in enumerate(events, start=1):
        output_label = f"[v{index}]"
        start = f"{event.start_time_sec:.3f}"
        end = f"{event.end_time_sec:.3f}"
        filter_parts.append(
            f"{current_label}[{index}:v]overlay="
            f"x={event.x}:y={event.y}:enable='between(t,{start},{end})'"
            f"{output_label}"
        )
        current_label = output_label

    if filter_parts:
        command.extend(["-filter_complex", ";".join(filter_parts), "-map", current_label])
    else:
        command.extend(["-map", "0:v"])

    command.extend(["-map", "0:a?", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy", str(output_video)])
    subprocess.run(command, check=True)
