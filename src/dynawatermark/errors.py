from __future__ import annotations


class DynawatermarkError(Exception):
    """Base exception for user-facing dynawatermark failures."""


class AssetError(DynawatermarkError):
    pass


class FfmpegNotFoundError(DynawatermarkError):
    pass


class FfmpegRenderError(DynawatermarkError):
    pass


class RenderCanceledError(DynawatermarkError):
    pass


class VideoProbeError(DynawatermarkError):
    pass
