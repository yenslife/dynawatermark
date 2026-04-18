from __future__ import annotations

import subprocess
from pathlib import Path

from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn, TimeRemainingColumn

from dynawatermark.event_generator import WatermarkEvent


def render_video(
    *,
    input_video: Path,
    event_asset_paths: list[Path],
    events: list[WatermarkEvent],
    output_video: Path,
    duration_sec: float | None = None,
) -> None:
    output_video.parent.mkdir(parents=True, exist_ok=True)
    if len(event_asset_paths) != len(events):
        raise ValueError("event_asset_paths and events must have the same length")

    command = [
        "ffmpeg",
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostats",
        "-progress",
        "pipe:1",
        "-y",
        "-i",
        str(input_video),
    ]
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
    _run_with_progress(command, duration_sec=duration_sec)


def _run_with_progress(command: list[str], *, duration_sec: float | None) -> None:
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    assert process.stdout is not None

    total = duration_sec if duration_sec and duration_sec > 0 else None
    columns = [
        TextColumn("[bold blue]FFmpeg[/bold blue]"),
        BarColumn(),
        TextColumn("{task.percentage:>3.0f}%") if total else TextColumn("處理中"),
        TimeElapsedColumn(),
    ]
    if total:
        columns.append(TimeRemainingColumn())

    with Progress(*columns) as progress:
        task_id = progress.add_task("render", total=total)
        for line in process.stdout:
            key, _, value = line.strip().partition("=")
            if key in {"out_time_ms", "out_time_us"}:
                seconds = _parse_progress_time(value)
                if seconds is not None:
                    progress.update(task_id, completed=min(seconds, total) if total else seconds)
            elif key == "progress" and value == "end" and total:
                progress.update(task_id, completed=total)

    stderr = process.stderr.read() if process.stderr else ""
    return_code = process.wait()
    if return_code != 0:
        message = stderr.strip() or f"FFmpeg failed with exit code {return_code}"
        raise RuntimeError(message)


def _parse_progress_time(value: str) -> float | None:
    try:
        return int(value) / 1_000_000
    except ValueError:
        return None
