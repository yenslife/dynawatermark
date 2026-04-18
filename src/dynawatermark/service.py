from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum
from pathlib import Path
from threading import Event

from pydantic import BaseModel
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn, TimeRemainingColumn

from dynawatermark.config import ConfigError, WatermarkAssetConfig, load_config
from dynawatermark.errors import AssetError, DynawatermarkError, FfmpegRenderError, RenderCanceledError
from dynawatermark.event_generator import WatermarkEvent, generate_events
from dynawatermark.ffmpeg_renderer import render_inspection_video, render_video
from dynawatermark.metadata import build_metadata, make_job_id, write_metadata
from dynawatermark.video_probe import probe_video
from dynawatermark.watermark_asset import inspect_watermark_asset, prepare_event_assets


class RenderJobState(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class RenderJobStatus(BaseModel):
    state: RenderJobState
    message: str | None = None


class RenderCancelToken:
    def __init__(self) -> None:
        self._event = Event()

    @property
    def event(self) -> Event:
        return self._event

    def cancel(self) -> None:
        self._event.set()

    @property
    def canceled(self) -> bool:
        return self._event.is_set()


class RenderResult(BaseModel):
    job_id: str
    output_video: Path
    inspection_video: Path | None
    metadata_path: Path
    events_count: int


def render_job(
    *,
    input_video: Path,
    config_path: Path,
    output_dir: Path,
    watermark_path: Path | None = None,
    inspection: bool = True,
    show_progress: bool = True,
    cancel_token: RenderCancelToken | None = None,
) -> RenderResult:
    try:
        settings = load_config(config_path)
        video = probe_video(input_video)
        asset_paths = resolve_asset_paths(settings.assets, config_path.parent, watermark_path)
        assets = {
            asset_id: inspect_watermark_asset(path, asset_id=asset_id)
            for asset_id, path in asset_paths.items()
        }
        events = generate_events(video, settings, assets=assets)

        job_id = make_job_id()
        job_dir = output_dir / job_id
        temp_dir = job_dir / "temp"
        output_video = job_dir / "output_watermarked.mp4"
        inspection_video = job_dir / "inspection_red_boxes.mp4" if inspection else None
        metadata_path = job_dir / "metadata.json"

        event_assets = prepare_event_assets(asset_paths, events, temp_dir)
        render_outputs(
            input_video=input_video,
            event_assets=event_assets,
            events=events,
            output_video=output_video,
            inspection_video=inspection_video,
            duration_sec=video.duration_sec,
            show_progress=show_progress,
            cancel_token=cancel_token,
        )
        metadata = build_metadata(
            job_id=job_id,
            input_path=input_video,
            output_path=output_video,
            inspection_path=inspection_video,
            video=video,
            assets=list(assets.values()),
            config=settings,
            events=events,
        )
        write_metadata(metadata, metadata_path)
    except ConfigError:
        raise
    except DynawatermarkError:
        raise
    except OSError as error:
        raise DynawatermarkError(f"檔案處理失敗：{error}") from error

    return RenderResult(
        job_id=job_id,
        output_video=output_video,
        inspection_video=inspection_video,
        metadata_path=metadata_path,
        events_count=len(events),
    )


def resolve_asset_paths(
    configured_assets: list[WatermarkAssetConfig],
    config_dir: Path,
    fallback_watermark: Path | None,
) -> dict[str, Path]:
    if not configured_assets:
        if fallback_watermark is None:
            raise AssetError("請提供 --watermark，或在 config.assets 設定至少一張圖片。")
        if not fallback_watermark.exists():
            raise AssetError(f"找不到浮水印圖片：{fallback_watermark}")
        return {"logo_01": fallback_watermark}

    paths: dict[str, Path] = {}
    for asset in configured_assets:
        if asset.path is None:
            raise AssetError(f"config.assets 裡的 {asset.asset_id} 缺少 path。")
        path = asset.path if asset.path.is_absolute() else config_dir / asset.path
        if not path.exists():
            raise AssetError(f"找不到浮水印圖片：{path}")
        paths[asset.asset_id] = path
    return paths


def render_outputs(
    *,
    input_video: Path,
    event_assets: list[Path],
    events: list[WatermarkEvent],
    output_video: Path,
    inspection_video: Path | None,
    duration_sec: float,
    show_progress: bool = True,
    cancel_token: RenderCancelToken | None = None,
) -> None:
    cancel_event = cancel_token.event if cancel_token is not None else Event()
    if cancel_event.is_set():
        raise RenderCanceledError("使用者已取消處理。")

    columns = [
        TextColumn("[bold blue]{task.description}[/bold blue]"),
        BarColumn(),
        TextColumn("{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
    ]
    with Progress(*columns, disable=not show_progress) as progress:
        watermark_task = progress.add_task("Watermark", total=duration_sec)
        futures = {}
        with ThreadPoolExecutor(max_workers=2 if inspection_video else 1) as executor:
            futures[
                executor.submit(
                    render_video,
                    input_video=input_video,
                    event_asset_paths=event_assets,
                    events=events,
                    output_video=output_video,
                    duration_sec=duration_sec,
                    progress_label="Watermark",
                    progress=progress,
                    task_id=watermark_task,
                    cancel_event=cancel_event,
                )
            ] = "Watermark"
            if inspection_video is not None:
                inspection_task = progress.add_task("Inspection", total=duration_sec)
                futures[
                    executor.submit(
                        render_inspection_video,
                        input_video=input_video,
                        events=events,
                        output_video=inspection_video,
                        duration_sec=duration_sec,
                        progress_label="Inspection",
                        progress=progress,
                        task_id=inspection_task,
                        cancel_event=cancel_event,
                    )
                ] = "Inspection"

            errors: list[str] = []
            canceled = False
            for future in as_completed(futures):
                label = futures[future]
                try:
                    future.result()
                except RenderCanceledError as error:
                    cancel_event.set()
                    canceled = True
                    errors.append(f"{label}: {error}")
                except DynawatermarkError as error:
                    cancel_event.set()
                    errors.append(f"{label}: {error}")

        if errors:
            if canceled:
                raise RenderCanceledError("\n".join(errors))
            raise FfmpegRenderError("\n".join(errors))
