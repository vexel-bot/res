"""Read-only API parity and small catalog/detail verification in the owned lab."""
import argparse
import hashlib
import json
import runpy
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/studios/research/editor-oss-20261002/catalog-loading"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", choices=["initial", "final"], default="initial")
    args = parser.parse_args()
    suffix = "-final" if args.stage == "final" else ""
    target = OUT / ("api-observation" + suffix + ".json")
    if target.exists():
        raise ValueError("preserve_existing_observation")
    helper = runpy.run_path(str(ROOT / "scripts/validation/visual-distance-study.py"))
    token, workspace_id = helper["identity"]()
    from sqlalchemy import select
    from app.database import SessionLocal
    from app.models import LibraryAsset
    from app.routers.assets import asset_out
    from app.services.studios.asset_read_projection import project_assets

    timings = {}
    values = {}
    for name, path in [
        ("catalog", f"/assets/catalog?workspace_id={workspace_id}"),
        ("resources", f"/studios/v1/editing/resources?workspace_id={workspace_id}&query="),
        ("quality", f"/studios/v1/workspaces/{workspace_id}/visual-quality"),
    ]:
        started = time.perf_counter()
        with urlopen(Request("http://127.0.0.1:8000/api/v1" + path,
                             headers={"Authorization": "Bearer " + token}), timeout=60) as response:
            raw = response.read()
            status = response.status
        elapsed = (time.perf_counter() - started) * 1000
        values[name] = json.loads(raw)
        assert status == 200
        timings[name] = {"elapsedMs": elapsed, "bytes": len(raw), "status": status,
                         "canonicalDigest": digest(values[name])}
        (OUT / (name + "-after" + suffix + ".json")).write_text(
            json.dumps(values[name], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        if name != "catalog":
            before = json.loads((OUT / (name + "-before.json")).read_text(encoding="utf-8"))
            assert values[name] == before["value"], name
            timings[name]["equalsPreviousFullApiProjection"] = True
        print(json.dumps({"endpoint": name, "elapsedMs": round(elapsed, 2), "bytes": len(raw)}), flush=True)
    catalog = values["catalog"]
    with SessionLocal() as db:
        statement = select(LibraryAsset).where(LibraryAsset.workspace_id == workspace_id,
            LibraryAsset.lifecycle_status == "active").order_by(LibraryAsset.created_at.desc())
        views = project_assets(db, statement, [("sourceAssetId",)])
        assert views is not None and len(catalog) == len(views) == 46
        for item, view in zip(catalog, views, strict=True):
            expected = asset_out(view).model_dump(mode="json", by_alias=True)
            assert {k: v for k, v in item.items() if k not in {
                "schemaVersion", "metadataDetail", "fullMetadataPath"}} == expected
            assert item["metadataDetail"] == "summary" and item["schemaVersion"] == "studio.asset-catalog-item.v1"
    # Verify one original font's full metadata without duplicating the giant
    # default bulk response. That existing route is checked by source/tests.
    detail_id = "83be05f7-bc4c-4531-8962-5a7085f730cf"
    chosen = next(item for item in catalog if item["id"] == detail_id)
    with urlopen(Request("http://127.0.0.1:8000" + chosen["fullMetadataPath"],
                         headers={"Authorization": "Bearer " + token}), timeout=60) as response:
        detail = json.load(response)
    with SessionLocal() as db:
        original = asset_out(db.get(LibraryAsset, detail_id)).model_dump(mode="json", by_alias=True)
        assert original["workspaceId"] == workspace_id and detail == original
    target.write_text(json.dumps({"observedAt": datetime.now(timezone.utc).isoformat(),
        "scope": "Three sequential real API requests; resource/quality full response equality, 46 catalog rows, full font detail",
        "timings": timings, "catalogRows": len(catalog), "nonMetadataFieldsAndSourceIdEqual": True,
        "fullFontDetailEqual": True, "noNewGenerationOrPaidCalls": True,
        "limits": ["One sample per endpoint, sequential, not p95 or controlled speedup experiment",
                   "Full old asset bulk response not downloaded again; source/tests preserve that route",
                   "Catalog shape checked against scalar view plus unchanged original serializer",
                   "Sparse metadata optimization is SQLite-specific; other dialects use original ORM reads"]},
        indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
