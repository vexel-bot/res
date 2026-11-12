"""Retired renderer registry retained only for migration-aware legacy readers.

All execution goes through providers.studios.craft. Configuration cannot register
legacy renderers as Studio editors.
"""
from ...domain.studios.providers import VideoRenderProvider

VIDEO_RENDER_PROVIDERS: dict[str, VideoRenderProvider] = {}
