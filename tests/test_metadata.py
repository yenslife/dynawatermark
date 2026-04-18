from datetime import datetime, timezone

from dynawatermark.config import WatermarkConfig
from dynawatermark.event_generator import WatermarkEvent
from dynawatermark.metadata import build_metadata, read_metadata, write_metadata
from dynawatermark.video_probe import VideoInfo
from dynawatermark.watermark_asset import WatermarkAsset


def test_metadata_roundtrip(tmp_path):
    input_path = tmp_path / "input.mp4"
    output_path = tmp_path / "output.mp4"
    input_path.write_bytes(b"input")
    output_path.write_bytes(b"output")
    video = VideoInfo(filename="input.mp4", duration_sec=10, width=640, height=360, fps=30)
    config = WatermarkConfig(seed=123, max_events=1)
    asset = WatermarkAsset(
        asset_id="logo_01",
        filename="watermark.png",
        type="image/png",
        width=100,
        height=50,
    )
    event = WatermarkEvent(
        event_id="evt_0001",
        start_time_sec=1,
        end_time_sec=2,
        duration_sec=1,
        x=10,
        y=20,
        width=100,
        height=50,
        opacity=0.3,
        asset_id="logo_01",
    )

    metadata = build_metadata(
        job_id="wm_test",
        input_path=input_path,
        output_path=output_path,
        inspection_path=None,
        video=video,
        assets=[asset],
        config=config,
        events=[event],
        created_at=datetime(2026, 4, 19, tzinfo=timezone.utc),
    )
    metadata_path = tmp_path / "metadata.json"
    write_metadata(metadata, metadata_path)
    loaded = read_metadata(metadata_path)

    assert loaded == metadata
    assert loaded.output_video.filename == "output.mp4"
