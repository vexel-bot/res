from __future__ import annotations

import json
import os
from pathlib import Path

import numpy as np
import supervision as sv

from app.providers.studios.supervision_detection import (
    SupervisionAdapterConfig,
    SupervisionDetectionAdapter,
)


def main() -> int:
    manifest_path = Path(
        os.environ.get(
            "STUDIO_WORKER_MANIFEST_PATH",
            "/opt/clicko/worker-manifest.json",
        )
    )
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    adapter = SupervisionDetectionAdapter(
        SupervisionAdapterConfig(
            source_provider="probe.synthetic-detector",
            source_provider_version="1.0.0",
            source_code_digest_sha256="a" * 64,
            class_map={},
            render_overlays=False,
        ),
        supervision_module=sv,
    )
    detections = sv.Detections(xyxy=np.empty((0, 4), dtype=float))
    checks = {
        "adapter": adapter.version == "1.0.0+supervision.0.30.1",
        "detections": len(detections) == 0,
        "providers": manifest["providers"] == [],
        "runtimeUser": os.getuid() == 10001,
        "supervision": sv.__version__ == "0.30.1",
    }
    output = {
        "checks": checks,
        "providers": manifest["providers"],
        "status": "ready" if all(checks.values()) else "failed",
        "supervision": sv.__version__,
    }
    print(json.dumps(output, separators=(",", ":"), sort_keys=True))
    return 0 if output["status"] == "ready" else 2


if __name__ == "__main__":
    raise SystemExit(main())
