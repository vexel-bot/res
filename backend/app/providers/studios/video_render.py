"""Retired renderer registry retained only for migration-aware legacy readers.

All execution goes through providers.studios.craft. Configuration cannot register
FFmpeg, HyperFrames, Motion Canvas, Remotion or Alight as Studio editors.
"""
from ...domain.studios.providers import VideoRenderProvider

VIDEO_RENDER_PROVIDERS: dict[str, VideoRenderProvider] = {}
