from dynawatermark.config import WatermarkConfig
from dynawatermark.event_generator import generate_events
from dynawatermark.video_probe import VideoInfo
from dynawatermark.watermark_asset import WatermarkAsset


def asset_map() -> dict[str, WatermarkAsset]:
    return {
        "logo_01": WatermarkAsset(
            asset_id="logo_01",
            filename="watermark.png",
            type="image/png",
            width=500,
            height=200,
        )
    }


def test_generate_events_is_stable_for_same_seed():
    video = VideoInfo(filename="input.mp4", duration_sec=60, width=1920, height=1080, fps=30)
    config = WatermarkConfig(seed=123, max_events=5)

    first = generate_events(video, config, assets=asset_map())
    second = generate_events(video, config, assets=asset_map())

    assert first == second


def test_generate_events_stays_inside_video_frame_and_duration():
    video = VideoInfo(filename="input.mp4", duration_sec=10, width=640, height=360, fps=30)
    config = WatermarkConfig(
        seed=123,
        max_events=10,
        duration_range_sec=(0.8, 2.0),
        size_range_ratio=(0.1, 0.2),
    )

    events = generate_events(video, config, assets=asset_map())

    assert len(events) == 10
    for event in events:
        assert 0 <= event.start_time_sec <= event.end_time_sec <= video.duration_sec
        assert event.x + event.width <= video.width
        assert event.y + event.height <= video.height
        assert 0 <= event.opacity <= 1


def test_generate_events_uses_asset_specific_opacity_and_weight():
    video = VideoInfo(filename="input.mp4", duration_sec=10, width=640, height=360, fps=30)
    config = WatermarkConfig.model_validate(
        {
            "seed": 123,
            "max_events": 5,
            "assets": [
                {"asset_id": "logo_01", "frequency_weight": 0.001, "opacity": 0.2},
                {"asset_id": "logo_02", "frequency_weight": 100, "opacity": 0.7},
            ],
        }
    )
    assets = asset_map()
    assets["logo_02"] = WatermarkAsset(
        asset_id="logo_02",
        filename="second.png",
        type="image/png",
        width=300,
        height=100,
    )

    events = generate_events(video, config, assets=assets)

    assert {event.asset_id for event in events} == {"logo_02"}
    assert {event.opacity for event in events} == {0.7}


def test_generate_scheduled_events_uses_specified_time_and_position():
    video = VideoInfo(filename="input.mp4", duration_sec=10, width=640, height=360, fps=30)
    config = WatermarkConfig.model_validate(
        {
            "mode": "scheduled",
            "assets": [{"asset_id": "logo_01"}],
            "scheduled_events": [
                {
                    "asset_id": "logo_01",
                    "start_time_sec": 2,
                    "duration_sec": 1.5,
                    "x": 100,
                    "y": 120,
                    "width": 80,
                    "height": 32,
                    "opacity": 0.45,
                }
            ],
        }
    )

    events = generate_events(video, config, assets=asset_map())

    assert len(events) == 1
    assert events[0].start_time_sec == 2
    assert events[0].end_time_sec == 3.5
    assert events[0].x == 100
    assert events[0].y == 120
    assert events[0].opacity == 0.45
