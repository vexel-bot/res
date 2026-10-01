from __future__ import annotations

import json
import shutil
import sys
from datetime import UTC, datetime
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPOSITORY_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.database import SessionLocal  # noqa: E402
from app.domain.studios.contracts import CreateVideoRenderJobRequest  # noqa: E402
from app.models import CreativeDocument, LibraryAsset, StudioGenerationJob, User  # noqa: E402
from app.providers.studios.video_render import (  # noqa: E402
    HyperFramesCliVideoRenderProvider,
    VIDEO_RENDER_PROVIDERS,
)
from app.services.object_storage import get_object_storage  # noqa: E402
from app.services.studios.jobs import execute_job_once  # noqa: E402
from app.services.studios.video_render import create_video_render_job  # noqa: E402


STATE_PATH = REPOSITORY_ROOT / "artifacts" / "validation" / "distribuicao-motion-state.json"
OUTPUT_PATH = REPOSITORY_ROOT / "artifacts" / "validation" / "distribuicao-motion-clicko.mp4"
HYPERFRAMES_CLI = (
    Path.home()
    / "Downloads"
    / "clicko-oss-evaluation"
    / "hyperframes"
    / "packages"
    / "cli"
    / "bin"
    / "hyperframes.mjs"
)


def main() -> None:
    state = json.loads(STATE_PATH.read_text(encoding="utf-8-sig"))
    if not HYPERFRAMES_CLI.is_file():
        raise RuntimeError(f"hyperframes_cli_missing:{HYPERFRAMES_CLI}")

    VIDEO_RENDER_PROVIDERS["hyperframes.cli"] = HyperFramesCliVideoRenderProvider(
        node_path=shutil.which("node") or "node",
        cli_path=str(HYPERFRAMES_CLI),
        timeout_seconds=7_200,
    )

    with SessionLocal() as db:
        document = db.get(CreativeDocument, state["motionDocumentId"])
        if document is None or document.workspace_id != state["workspaceId"]:
            raise RuntimeError("motion_document_missing")
        user = db.get(User, document.created_by)
        if user is None:
            raise RuntimeError("motion_document_actor_missing")

        request = CreateVideoRenderJobRequest(
            workspace_id=state["workspaceId"],
            document_id=document.id,
            expected_document_revision=state["motionDocumentRevision"],
            expected_document_version=state["motionDocumentVersion"],
            page_ids=[state["motionPageId"]],
            provider="hyperframes.cli",
            motion_graph_id=state["motionGraphId"],
            motion_graph_digest_sha256=state["motionGraphDigestSha256"],
            output={
                "format": "mp4",
                "width": 1080,
                "height": 1920,
                "fps": 25,
                "videoCodec": "h264",
                "audioCodec": "aac",
                "quality": "draft",
            },
            correlation_id="distribuicao-motion-render-20260831",
        )
        job, _ = create_video_render_job(
            db,
            document,
            request,
            f"dist-motion-render-{datetime.now(UTC).strftime('%Y%m%d%H%M%S%f')}",
            user,
        )
        status = execute_job_once(db, job)
        db.refresh(job)
        if status != "succeeded":
            raise RuntimeError(f"motion_render_failed:{job.error_code}:{job.error_message}")

        result = job.result_payload or {}
        artifact = result.get("artifact") or {}
        asset = db.get(LibraryAsset, artifact.get("assetId"))
        if asset is None or not asset.storage_key:
            raise RuntimeError("motion_render_asset_missing")
        storage = get_object_storage(asset.storage_backend or "local")
        with storage.materialize(asset.storage_key) as rendered:
            shutil.copyfile(rendered, OUTPUT_PATH)

        print(
            json.dumps(
                {
                    "motionDocumentId": document.id,
                    "motionGraphId": state["motionGraphId"],
                    "motionRenderJobId": job.id,
                    "motionRenderAssetId": asset.id,
                    "motionOutput": str(OUTPUT_PATH),
                    "motionQualityStatus": (result.get("qualityEvaluation") or {}).get("status"),
                    "motionWarnings": result.get("warnings") or [],
                    "workerExecutionContext": result.get("workerExecutionContext"),
                },
                ensure_ascii=False,
                indent=2,
            )
        )


if __name__ == "__main__":
    main()
