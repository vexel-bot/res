"""Import versioned local font files into the existing tenant catalog."""

import hashlib
import json
from pathlib import Path

from ...domain.studios.editing_resources import ResourceMetadataV1
from .editing_resources import store_resource

ROOT = Path(__file__).resolve().parents[2] / "resources" / "editorial_fonts"


def import_pack(db, workspace_id, user_id):
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    result = []
    for item in manifest["fonts"]:
        path = ROOT / item["file"]
        license_path = ROOT / item["license"]
        if hashlib.sha256(path.read_bytes()).hexdigest() != item["sha256"] or (
            hashlib.sha256(license_path.read_bytes()).hexdigest() != item["licenseSha256"]
        ):
            raise ValueError("editorial_font_pack_checksum_conflict")
        metadata = ResourceMetadataV1(
            kind="font",
            family=item["family"],
            version=str(manifest["version"]),
            description="Editorial font; available axes: " + json.dumps(item["axes"]),
            usage_evidence=license_path.read_text(encoding="utf-8")[:3900],
            tags=["editorial", "motion", "portuguese"],
        )
        asset = store_resource(db, workspace_id, item["family"], path, metadata, user_id)
        asset.object_metadata = {
            **(asset.object_metadata or {}),
            "fontLicense": {
                "filename": item["license"],
                "checksumSha256": item["licenseSha256"],
                "text": license_path.read_bytes().decode("utf-8"),
            },
            "fontAxes": item["axes"],
            "fontPackVersion": manifest["version"],
        }
        result.append({"assetId": asset.id, **item})
    return {"version": manifest["version"], "fonts": result, "missingAssets": manifest["missingAssets"]}
