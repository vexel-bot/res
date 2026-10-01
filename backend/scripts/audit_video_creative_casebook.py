from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from app.domain.studios.creative_autonomy import (
    CreativePilotCasebookV1,
    audit_creative_casebook,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Audit the Clicko creative pilot casebook.")
    parser.add_argument(
        "--casebook",
        type=Path,
        default=Path("benchmarks/studios/creative/video-creative-pilot-casebook.v1.json"),
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    casebook = CreativePilotCasebookV1.model_validate_json(
        args.casebook.read_text(encoding="utf-8")
    )
    audit = audit_creative_casebook(casebook, audited_at=datetime.now(UTC))
    serialized = json.dumps(
        audit.model_dump(mode="json", by_alias=True), ensure_ascii=False, indent=2
    ) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(serialized, encoding="utf-8")
    print(serialized, end="")
    return 0 if audit.eligible else 1


if __name__ == "__main__":
    raise SystemExit(main())
