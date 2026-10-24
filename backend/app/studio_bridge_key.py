"""Server-only signing key shared by the Studios bridge and financial admission."""

import os
import secrets
from pathlib import Path

from .config import get_settings


def bridge_secret():
    settings = get_settings()
    stored = settings.clicko_studios_bridge_secret
    configured = os.environ.get("CLICKO_STUDIOS_BRIDGE_SECRET") or (stored.get_secret_value() if stored else None)
    if configured:
        if len(configured) < 32:
            raise RuntimeError("STUDIOS_BRIDGE_KEY_INVALID")
        return configured
    if settings.environment == "production":
        raise RuntimeError("STUDIOS_BRIDGE_KEY_REQUIRED")
    filename = Path(__file__).resolve().parents[2] / ".clicko-data/studios/bridge-key"
    filename.parent.mkdir(parents=True, exist_ok=True)
    try:
        with filename.open("x", encoding="utf-8") as destination:
            destination.write(secrets.token_hex(48))
    except FileExistsError:
        pass
    value = filename.read_text(encoding="utf-8").strip()
    if len(value) < 32:
        raise RuntimeError("STUDIOS_BRIDGE_KEY_INVALID")
    return value
