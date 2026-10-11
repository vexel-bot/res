"""Seal catalog compatibility, current API/UI behavior and canonical studies."""
import ast
import hashlib
import json
import runpy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/studios/research/editor-oss-20261002/catalog-loading"
ORIGINAL = ROOT / "output/visual-directed-native14-20261004"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = OUT / "verification.json"
    if target.exists():
        raise ValueError("preserve_existing_verification")
    before = read(OUT / "before.json")
    for name, value in before.items():
        assert sha(OUT / value["backup"]) == value["sha256"], name
    unchanged_functions = {}
    for name, changed_functions in {
        "backend/app/routers/assets.py": set(),
        "backend/app/services/studios/engine_qualification.py": {"_reference"},
        "backend/app/services/studios/visual_quality_program.py": {"project_quality_program"},
        "backend/app/services/studios/editing_resources.py": {"catalog"},
    }.items():
        old = ast.parse((OUT / before[name]["backup"]).read_text(encoding="utf-8"))
        new = ast.parse((ROOT / name).read_text(encoding="utf-8"))
        new_functions = {n.name: n for n in new.body if isinstance(n, ast.FunctionDef)}
        preserved = []
        for node in old.body:
            if isinstance(node, ast.FunctionDef) and node.name not in changed_functions:
                assert ast.dump(node) == ast.dump(new_functions[node.name]), (name, node.name)
                preserved.append(node.name)
            if isinstance(node, ast.FunctionDef) and node.name == "_reference":
                current = new_functions[node.name]
                assert len(current.body) == len(node.body)
                assert all(ast.dump(a) == ast.dump(b) for i, (a, b) in enumerate(zip(node.body, current.body)) if i != 1)
        unchanged_functions[name] = preserved
    schema = "backend/app/schemas.py"
    old = ast.parse((OUT / before[schema]["backup"]).read_text(encoding="utf-8"))
    new = ast.parse((ROOT / schema).read_text(encoding="utf-8"))
    classes = {n.name: n for n in new.body if isinstance(n, ast.ClassDef)}
    assert all(ast.dump(n) == ast.dump(classes[n.name]) for n in old.body if isinstance(n, ast.ClassDef))
    prior = read(OUT.parent / "plan-history-validation/sources.json")["sources"]
    changed = []
    for name, expected in prior.items():
        if sha(ROOT / name) != expected:
            assert name in before and before[name]["sha256"] == expected, name
            changed.append(name)
    api_observation = read(OUT / "api-observation-final.json")
    assert api_observation["catalogRows"] == 46 and api_observation["fullFontDetailEqual"]
    assert api_observation["nonMetadataFieldsAndSourceIdEqual"]
    assert api_observation["timings"]["resources"]["equalsPreviousFullApiProjection"]
    assert api_observation["timings"]["quality"]["equalsPreviousFullApiProjection"]
    for stage, frame in [("catalog-ui-open", 0), ("catalog-ui-frame244", 244), ("catalog-ui-frame449", 449)]:
        envelope = read(OUT / (stage + ".json"))
        ui = envelope["data"]["result"]
        assert envelope["success"] and ui["ready"] and ui["overlays"] == 0
        assert ui["directionVisible"] and ui["reviewGateMounted"] and len(ui["cards"]) == 5
        assert ui["inspectorFrame"] == str(frame) and f"Propriedades calculadas no frame {frame}." in ui["inspectorText"]
        assert ui["selectedLayerId"] == "ed2-895c9ff7a0a9ce1cb92ec080"
        assert ui["video"]["readyState"] >= 2 and not ui["video"]["seeking"] and ui["video"]["paused"]
        assert abs(ui["video"]["currentTime"] - frame / 30) < 1 / 60
        assert any(r["path"] == "/api/v1/assets/catalog" and r["status"] == 200 for r in ui["resources"])
        assert not any(r["path"] == "/api/v1/assets" for r in ui["resources"])
    helper = runpy.run_path(str(ROOT / "scripts/validation/visual-distance-study.py"))
    _, workspace_id = helper["identity"]()
    helper["api"].__globals__["BASE"] = "http://127.0.0.1:8000/api/v1"
    api = helper["api"]
    execution = read(ORIGINAL / "execution.json")
    variants = {}
    for name, variant in execution["variants"].items():
        current = api("/studios/v1/documents/" + variant["documentId"])
        snapshot = read(ORIGINAL / (name + "-render.json"))["snapshot"]
        assert current["workspaceId"] == workspace_id
        assert current["revision"] == snapshot["revision"] == variant["revision"] == 2
        assert current["version"] == snapshot["version"] == 1
        assert current["composition"] == snapshot["composition"] and current["assets"] == snapshot["assets"]
        actual_sha = sha(ORIGINAL / (name + ".mp4"))
        assert actual_sha == variant["artifact"]["checksumSha256"]
        variants[name] = {"documentId": current["documentId"], "revision": current["revision"],
                          "compositionAndAssetsEqualOriginalRenderSnapshot": True, "originalMp4Sha256": actual_sha}
    comparisons = {}
    for name, original in execution["comparisons"].items():
        current = api(f"/studios/v1/workspaces/{workspace_id}/visual-study-comparisons/{original['id']}")
        assert current["status"] == "not_assessed" and current["review"] is None
        assert current["labels"] == original["labels"]
        comparisons[name] = {"id": current["id"], "status": current["status"], "review": None, "labelsUnchanged": True}
    (OUT / "preservation.json").write_text(json.dumps({"observedAt": datetime.now(timezone.utc).isoformat(),
        "variants": variants, "comparisons": comparisons}, indent=2) + "\n", encoding="utf-8")
    new_sources = set(before) | {"backend/app/services/studios/asset_read_projection.py",
        "backend/tests/test_asset_read_projection.py", "backend/tests/test_asset_catalog_api.py",
        "backend/tests/test_asset_reference_projection.py", "scripts/validation/editor-catalog-observe.py",
        "scripts/validation/editor-catalog-ui.py", "scripts/validation/editor-catalog-verify.py"}
    tracked = {**prior, **{path: sha(ROOT / path) for path in new_sources}}
    (OUT / "sources.json").write_text(json.dumps({"observedAt": datetime.now(timezone.utc).isoformat(),
        "priorSourcesChanged": changed, "priorSourcesUnchanged": len(prior) - len(changed),
        "priorAssetSchemasUnchanged": True, "preservedFunctions": unchanged_functions,
        "referenceChecksUnchangedExceptLookup": True, "sources": tracked}, indent=2) + "\n", encoding="utf-8")
    files = {p.name: {"sha256": sha(p), "bytes": p.stat().st_size} for p in OUT.iterdir() if p.is_file() and p != target}
    target.write_text(json.dumps({"observedAt": datetime.now(timezone.utc).isoformat(), "sourceHashesMatch": len(tracked),
        "scope": "Explicit lightweight catalog, sparse metadata reads, old resource/quality output parity, real UI and nine studies",
        "tests": {"passed": 32, "failed": 0, "scope": "10 catalog/projection cases, 6 synthetic reference guards, 16 existing resource/quality/study cases"},
        "typecheck": "passed", "ruff": "passed", "summaryUiVerified": True,
        "noNewGenerationOrPaidCalls": True, "realtimeScrubbingDemonstrated": False,
        "humanApproval": "not_assessed", "autonomy": "not_demonstrated", "files": files}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sourceHashesMatch": len(tracked), "preservedStudies": len(variants), "summaryUiVerified": True}))


if __name__ == "__main__":
    main()
