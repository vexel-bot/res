"""Declare native system-font requirements without claiming they are embedded."""
import json


def font_requirements(path, engine, build_id):
    faces = set()

    def visit(value):
        if isinstance(value, dict):
            for key, child in value.items():
                if key == "font" and isinstance(child, str) and child:
                    faces.add(child)
                else:
                    visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)

    if engine == "effectcraft":
        try:
            visit(json.loads(path.read_text(encoding="utf-8")))
        except (UnicodeError, json.JSONDecodeError, RecursionError):
            return {"schemaVersion": "craft.font-requirements.v1", "buildId": build_id,
                    "requestedFaces": [], "status": "unavailable_legacy_native_format",
                    "instruction": "Font requirements could not be inspected. Inspect fonts in the native editor."}
    return {"schemaVersion": "craft.font-requirements.v1", "buildId": build_id,
            "requestedFaces": sorted(faces), "status": "declared_not_portability_verified",
            "instruction": "Resolve these faces using inspect_motion_fonts on the destination build. "
                           "An empty fontManifest means no font files were embedded, not that fonts are unnecessary."}
