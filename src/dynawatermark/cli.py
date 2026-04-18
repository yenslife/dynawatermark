from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from dynawatermark.config import ConfigError, WatermarkAssetConfig, load_config
from dynawatermark.event_generator import generate_events
from dynawatermark.ffmpeg_renderer import render_video
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
    metadata_path = job_dir / "metadata.json"

    console.print(f"產生 {len(events)} 個浮水印事件")
    event_assets = prepare_event_assets(asset_paths, events, temp_dir)
    render_video(
        input_video=input,
        event_asset_paths=event_assets,
        events=events,
        output_video=output_video,
    )
    metadata = build_metadata(
        job_id=job_id,
        input_path=input,
        output_path=output_video,
        video=video,
        assets=list(assets.values()),
        config=settings,
        events=events,
    )
    write_metadata(metadata, metadata_path)

    console.print(f"輸出影片：{output_video}")
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


if __name__ == "__main__":
    app()
