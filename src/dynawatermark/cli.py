from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import typer
from rich.console import Console
from rich.progress import BarColumn, Progress, TextColumn, TimeElapsedColumn, TimeRemainingColumn

from dynawatermark.config import ConfigError, WatermarkAssetConfig, load_config
from dynawatermark.event_generator import WatermarkEvent, generate_events
from dynawatermark.ffmpeg_renderer import render_inspection_video, render_video
from dynawatermark.metadata import build_metadata, make_job_id, write_metadata
from dynawatermark.video_probe import probe_video
from dynawatermark.watermark_asset import inspect_watermark_asset, prepare_event_assets

app = typer.Typer(help="Dynamic traceable video watermarking CLI.")
console = Console()


@app.callback()
def main() -> None:
    """Dynamic traceable video watermarking CLI."""


@app.command()
def render(
    input: Path = typer.Option(..., "--input", exists=True, readable=True, help="輸入影片路徑。"),
    config: Path = typer.Option(..., "--config", exists=True, readable=True, help="JSON 設定檔路徑。"),
    output_dir: Path = typer.Option(..., "--output-dir", help="輸出資料夾。"),
    watermark: Path | None = typer.Option(None, "--watermark", exists=True, readable=True, help="簡易模式 PNG 浮水印路徑。"),
    inspection: bool = typer.Option(True, "--inspection/--no-inspection", help="是否輸出紅色區塊人工核對版影片。"),
) -> None:
    try:
        settings = load_config(config)
    except ConfigError as error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(code=1) from error
    video = probe_video(input)
    asset_paths = _resolve_asset_paths(settings.assets, config.parent, watermark)
    assets = {
        asset_id: inspect_watermark_asset(path, asset_id=asset_id)
        for asset_id, path in asset_paths.items()
    }
    events = generate_events(
        video,
        settings,
        assets=assets,
    )

    job_id = make_job_id()
    job_dir = output_dir / job_id
    temp_dir = job_dir / "temp"
    output_video = job_dir / "output_watermarked.mp4"
    inspection_video = job_dir / "inspection_red_boxes.mp4"
    metadata_path = job_dir / "metadata.json"

    console.print(f"產生 {len(events)} 個浮水印事件")
    event_assets = prepare_event_assets(asset_paths, events, temp_dir)
    try:
        _render_outputs(
            input_video=input,
            event_assets=event_assets,
            events=events,
            output_video=output_video,
            inspection_video=inspection_video if inspection else None,
            duration_sec=video.duration_sec,
        )
    except RuntimeError as error:
        console.print(f"[red]FFmpeg 處理失敗：{error}[/red]")
        raise typer.Exit(code=1) from error
    metadata = build_metadata(
        job_id=job_id,
        input_path=input,
        output_path=output_video,
        inspection_path=inspection_video if inspection else None,
        video=video,
        assets=list(assets.values()),
        config=settings,
        events=events,
    )
    write_metadata(metadata, metadata_path)

    console.print(f"輸出影片：{output_video}")
    if inspection:
        console.print(f"人工核對版：{inspection_video}")
    console.print(f"Metadata：{metadata_path}")


def _resolve_asset_paths(
    configured_assets: list[WatermarkAssetConfig],
    config_dir: Path,
    fallback_watermark: Path | None,
) -> dict[str, Path]:
    if not configured_assets:
        if fallback_watermark is None:
            raise typer.BadParameter("請提供 --watermark，或在 config.assets 設定至少一張圖片。")
        return {"logo_01": fallback_watermark}

    paths: dict[str, Path] = {}
    for asset in configured_assets:
        if asset.path is None:
            raise typer.BadParameter(f"config.assets 裡的 {asset.asset_id} 缺少 path。")
        path = asset.path if asset.path.is_absolute() else config_dir / asset.path
        if not path.exists():
            raise typer.BadParameter(f"找不到浮水印圖片：{path}")
        paths[asset.asset_id] = path
    return paths


def _render_outputs(
    *,
    input_video: Path,
    event_assets: list[Path],
    events: list[WatermarkEvent],
    output_video: Path,
    inspection_video: Path | None,
    duration_sec: float,
) -> None:
    columns = [
        TextColumn("[bold blue]{task.description}[/bold blue]"),
        BarColumn(),
        TextColumn("{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        TimeRemainingColumn(),
    ]
    with Progress(*columns) as progress:
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
                    )
                ] = "Inspection"

            errors: list[str] = []
            for future in as_completed(futures):
                label = futures[future]
                try:
                    future.result()
                except RuntimeError as error:
                    errors.append(f"{label}: {error}")

        if errors:
            raise RuntimeError("\n".join(errors))


if __name__ == "__main__":
    app()
