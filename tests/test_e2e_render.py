from __future__ import annotations

import json
import shutil
import subprocess

import pytest
from PIL import Image, ImageDraw

from dynawatermark.service import render_job


pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg and ffprobe are required for end-to-end render tests",
)


def test_render_job_outputs_normal_inspection_and_metadata(tmp_path):
    input_video = tmp_path / "input.mp4"
    watermark = tmp_path / "watermark.png"
    config = tmp_path / "config.json"
    output_dir = tmp_path / "outputs"

    subprocess.run(
        [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=320x180:rate=10",
            "-t",
            "1",
            "-pix_fmt",
            "yuv420p",
            str(input_video),
        ],
        check=True,
    )

    image = Image.new("RGBA", (120, 48), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 119, 47), fill=(255, 255, 255, 160))
    draw.text((18, 15), "WM", fill=(0, 0, 0, 220))
    image.save(watermark)

    config.write_text(
        json.dumps(
            {
                "mode": "random",
                "seed": 99,
                "max_events": 3,
                "opacity_range": [0.2, 0.3],
                "duration_range_sec": [0.2, 0.3],
                "size_range_ratio": [0.1, 0.12],
                "position_strategy": "random",
                "margin_ratio": 0.03,
                "allow_rotation": False,
            }
        ),
        encoding="utf-8",
    )

    result = render_job(
        input_video=input_video,
        config_path=config,
        output_dir=output_dir,
        watermark_path=watermark,
        inspection=True,
        show_progress=False,
    )

    assert result.output_video.exists()
    assert result.inspection_video is not None
    assert result.inspection_video.exists()
    assert result.metadata_path.exists()
    assert result.events_count == 3

    metadata = json.loads(result.metadata_path.read_text(encoding="utf-8"))
    assert metadata["output_video"]["filename"] == "output_watermarked.mp4"
    assert metadata["inspection_video"]["filename"] == "inspection_red_boxes.mp4"
    assert len(metadata["events"]) == 3
    assert "sha256" not in result.metadata_path.read_text(encoding="utf-8")
    assert "integrity" not in metadata
