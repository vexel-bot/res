"""CLI for the physical-device boundary; no driver or XML compiler is bundled."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))

from app.providers.studios.alight_worker import main  # noqa: E402

if __name__ == "__main__":
    main()
