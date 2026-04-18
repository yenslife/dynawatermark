from __future__ import annotations

import subprocess
from threading import Event
from pathlib import Path

from rich.progress import TaskID
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn, TimeRemainingColumn

from dynawatermark.errors import FfmpegNotFoundError, FfmpegRenderError, RenderCanceledError
from dynawatermark.event_generator import WatermarkEvent


def render_video(
    *,
    input_video: Path,
    event_asset_paths: list[Path],
    events: list[WatermarkEvent],
    output_video: Path,
    duration_sec: float | None = None,
    progress_label: str = "FFmpeg",
    progress: Progress | None = None,
    task_id: TaskID | None = None,
    cancel_event: Event | None = None,
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
    _run_with_progress(
        command,
        duration_sec=duration_sec,
        label=progress_label,
        progress=progress,
        task_id=task_id,
        cancel_event=cancel_event,
    )


def render_inspection_video(
    *,
    input_video: Path,
    events: list[WatermarkEvent],
    output_video: Path,
    duration_sec: float | None = None,
    progress_label: str = "Inspection",
    progress: Progress | None = None,
    task_id: TaskID | None = None,
    cancel_event: Event | None = None,
) -> None:
    output_video.parent.mkdir(parents=True, exist_ok=True)
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

    filter_parts: list[str] = []
    current_label = "[0:v]"
    for index, event in enumerate(events, start=1):
        output_label = f"[r{index}]"
        start = f"{event.start_time_sec:.3f}"
        end = f"{event.end_time_sec:.3f}"
        filter_parts.append(
            f"{current_label}drawbox="
            f"x={event.x}:y={event.y}:w={event.width}:h={event.height}:"
            f"color=red@0.85:t=fill:enable='between(t,{start},{end})'"
            f"{output_label}"
        )
        current_label = output_label

    if filter_parts:
        command.extend(["-filter_complex", ";".join(filter_parts), "-map", current_label])
    else:
        command.extend(["-map", "0:v"])

    command.extend(["-map", "0:a?", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "copy", str(output_video)])
    _run_with_progress(
        command,
        duration_sec=duration_sec,
        label=progress_label,
        progress=progress,
        task_id=task_id,
        cancel_event=cancel_event,
    )


def _run_with_progress(
    command: list[str],
    *,
    duration_sec: float | None,
    label: str,
    progress: Progress | None,
    task_id: TaskID | None,
    cancel_event: Event | None,
) -> None:
    try:
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except FileNotFoundError as error:
        raise FfmpegNotFoundError("找不到 ffmpeg，請先安裝 FFmpeg 並確認 ffmpeg 在 PATH 內。") from error
    assert process.stdout is not None

    total = duration_sec if duration_sec and duration_sec > 0 else None
    if progress is not None and task_id is not None:
        _consume_progress(
            process,
            duration_sec=total,
            progress=progress,
            task_id=task_id,
            cancel_event=cancel_event,
        )
        return

    columns = [
        TextColumn(f"[bold blue]{label}[/bold blue]"),
        BarColumn(),
        TextColumn("{task.percentage:>3.0f}%") if total else TextColumn("處理中"),
        TimeElapsedColumn(),
    ]
    if total:
        columns.append(TimeRemainingColumn())

    with Progress(*columns) as progress:
        task_id = progress.add_task("render", total=total)
        _consume_progress(
            process,
            duration_sec=total,
            progress=progress,
            task_id=task_id,
            cancel_event=cancel_event,
        )


def _consume_progress(
    process: subprocess.Popen[str],
    *,
    duration_sec: float | None,
    progress: Progress,
    task_id: TaskID,
    cancel_event: Event | None,
) -> None:
    assert process.stdout is not None
    for line in process.stdout:
        if cancel_event is not None and cancel_event.is_set():
            _terminate_process(process)
            raise RenderCanceledError("使用者已取消處理。")
        key, _, value = line.strip().partition("=")
        if key in {"out_time_ms", "out_time_us"}:
            seconds = _parse_progress_time(value)
            if seconds is not None:
                completed = min(seconds, duration_sec) if duration_sec else seconds
                progress.update(task_id, completed=completed)
        elif key == "progress" and value == "end" and duration_sec:
            progress.update(task_id, completed=duration_sec)

    stderr = process.stderr.read() if process.stderr else ""
    return_code = process.wait()
    if cancel_event is not None and cancel_event.is_set():
        raise RenderCanceledError("使用者已取消處理。")
    if return_code != 0:
        message = stderr.strip() or f"FFmpeg failed with exit code {return_code}"
        raise FfmpegRenderError(message)


def _terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()


def _parse_progress_time(value: str) -> float | None:
    try:
        return int(value) / 1_000_000
    except ValueError:
        return None
