from __future__ import annotations

import argparse
import json
from pathlib import Path
from uuid import uuid4

from app.services.studios.worker_runtime import load_worker_manifest, manifest_digest
from app.tasks import probe_studio_worker


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Dispatch an attested probe to a dedicated Studio worker queue."
    )
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--timeout", type=float, default=30.0)
    args = parser.parse_args()

    manifest = load_worker_manifest(args.manifest)
    digest = manifest_digest(manifest)
    queue = manifest.queues[0]
    result = probe_studio_worker.apply_async(
        args=[manifest.capability, queue, digest],
        queue=queue,
        task_id=f"worker-probe-{uuid4()}",
        soft_time_limit=max(10, int(args.timeout)),
        time_limit=max(15, int(args.timeout) + 5),
    ).get(timeout=args.timeout)
    runtime = result.get("runtime", {})
    if (
        result.get("status") != "ready"
        or runtime.get("mode") != "isolated"
        or runtime.get("attested") is not True
        or runtime.get("manifestDigestSha256") != digest
        or runtime.get("capability") != manifest.capability
        or runtime.get("queueName") != queue
    ):
        raise SystemExit("Studio worker probe returned an incompatible runtime")
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
