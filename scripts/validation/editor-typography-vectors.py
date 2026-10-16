"""Compile real canonical recipe manifests as input for the runtime study."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT / "backend"), str(ROOT / "backend/tests")]

from test_typography_units import typography_direction  # noqa: E402
from test_remotion_native import native_document  # noqa: E402
from app.providers.studios.remotion_projection import compile_remotion_composition  # noqa: E402

cases = []
for text in ["AÇÃO", "AC\u0327A\u0303O", "👨‍👩‍👧‍👦", "👍🏽🇧🇷", " A\u00a0\u202fB \t\r\n", "Uma palavra inteira"]:
    for unit in ["character", "word"]:
        document, projection = native_document(typography_direction(text, unit, duration=150))
        manifest = compile_remotion_composition(document, projection, {})
        hero = next(layer for layer in manifest["layers"] if layer["name"] == "hero")
        cases.append({"text": text, "spec": hero["properties"]["recipeTypography"],
                      "nativeCompositionDigest": manifest["nativeCompositionDigest"]})
path = ROOT / "docs/studios/research/editor-oss-20261002/typography-unit-vectors.json"
path.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps({"cases": len(cases), "path": path.relative_to(ROOT).as_posix()}))
