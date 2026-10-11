"""Restore only line endings whose bytes match the supplied pack manifest."""
import hashlib
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FONTS = (ROOT / "backend/app/resources/editorial_fonts").resolve()
manifest = json.loads((FONTS / "manifest.json").read_text(encoding="utf-8"))
repair = "--repair" in sys.argv
records = []
for item in manifest["fonts"]:
    path = (FONTS / item["license"]).resolve()
    if path.parent != FONTS:
        raise SystemExit("License path escaped supplied pack")
    raw = path.read_bytes()
    expected = item["licenseSha256"]
    sha = lambda value: hashlib.sha256(value).hexdigest()  # noqa: E731
    lf = raw.replace(b"\r\n", b"\n")
    candidate = next((value for value in [raw, lf, lf.replace(b"\n", b"\r\n")]
                      if sha(value) == expected), None)
    if candidate is None:
        raise SystemExit("Divergence is not a verified line-ending conversion: " + item["license"])
    repaired = repair and candidate != raw
    if repair:
        # Refresh stat metadata even for already-correct originals, so Git
        # rechecks them under -text instead of trusting the old clean filter.
        path.write_bytes(candidate)
    records.append({"license": item["license"], "expectedSha256": expected,
                    "beforeSha256": sha(raw), "afterSha256": sha(path.read_bytes()),
                    "repaired": repaired, "textContentChanged": False})
report = {"scope": "supplied_pack_exact_license_bytes", "repairRequested": repair, "licenses": records,
          "manifestChanged": False, "fontFilesChanged": False, "checksumGateDisabled": False}
output = ROOT / "docs/studios/research/editor-oss-20261002/font-license-integrity.json"
output.write_text(json.dumps(report, indent=2), encoding="utf-8")
print(json.dumps({"output": str(output), "repaired": sum(item["repaired"] for item in records)}))
