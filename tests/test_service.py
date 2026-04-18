from __future__ import annotations

import pytest

from dynawatermark.config import WatermarkAssetConfig
from dynawatermark.errors import AssetError, RenderCanceledError
from dynawatermark.service import RenderCancelToken, resolve_asset_paths, render_outputs


def test_resolve_asset_paths_requires_fallback_watermark_when_no_assets(tmp_path):
    with pytest.raises(AssetError, match="請提供 --watermark"):
        resolve_asset_paths([], tmp_path, None)


def test_resolve_asset_paths_rejects_missing_fallback_watermark(tmp_path):
    with pytest.raises(AssetError, match="找不到浮水印圖片"):
        resolve_asset_paths([], tmp_path, tmp_path / "missing.png")


def test_resolve_asset_paths_uses_config_relative_paths(tmp_path):
    asset_path = tmp_path / "assets" / "logo.png"
    asset_path.parent.mkdir()
    asset_path.write_bytes(b"placeholder")

    paths = resolve_asset_paths(
        [WatermarkAssetConfig(asset_id="logo", path=asset_path.relative_to(tmp_path))],
        tmp_path,
        None,
    )

    assert paths == {"logo": asset_path}


def test_render_cancel_token_tracks_canceled_state():
    token = RenderCancelToken()

    assert not token.canceled
    token.cancel()
    assert token.canceled


def test_render_outputs_rejects_pre_canceled_token(tmp_path):
    token = RenderCancelToken()
    token.cancel()

    with pytest.raises(RenderCanceledError):
        render_outputs(
            input_video=tmp_path / "input.mp4",
            event_assets=[],
            events=[],
            output_video=tmp_path / "output.mp4",
            inspection_video=None,
            duration_sec=1,
            show_progress=False,
            cancel_token=token,
        )
