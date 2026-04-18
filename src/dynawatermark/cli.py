from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from dynawatermark.config import ConfigError
from dynawatermark.errors import DynawatermarkError
from dynawatermark.service import render_job

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
        result = render_job(
            input_video=input,
            config_path=config,
            output_dir=output_dir,
            watermark_path=watermark,
            inspection=inspection,
            show_progress=True,
        )
    except ConfigError as error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(code=1) from error
    except DynawatermarkError as error:
        console.print(f"[red]{error}[/red]")
        raise typer.Exit(code=1) from error

    console.print(f"產生 {result.events_count} 個浮水印事件")
    console.print(f"輸出影片：{result.output_video}")
    if result.inspection_video is not None:
        console.print(f"人工核對版：{result.inspection_video}")
    console.print(f"Metadata：{result.metadata_path}")


if __name__ == "__main__":
    app()
