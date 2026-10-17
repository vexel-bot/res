"""Create an additive semantic receipt for a stored production snapshot."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.services.studios.historical_semantic_reevaluation import reevaluate_file  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    receipt = reevaluate_file(args.source.resolve(), args.destination.resolve())
    print(json.dumps({"status": receipt["status"], "destination": str(args.destination.resolve())}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
