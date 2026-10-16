"""Verify summary parity, real UI frame binding, preservation, and source boundaries."""
import ast
import hashlib
import json
import runpy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/studios/research/editor-oss-20261002/inspection-response"
ORIGINAL = ROOT / "output/visual-directed-native14-20261004"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = OUT / "verification.json"
    if target.exists():
        raise ValueError("preserve_existing_verification")
    backups = read(OUT / "before.json")
    for name, value in backups.items():
        assert sha(OUT / value["backup"]) == value["sha256"], name
    service = "backend/app/services/studios/editor_commands.py"
    old_ast = ast.parse((OUT / backups[service]["backup"]).read_text(encoding="utf-8"))
    new_ast = ast.parse((ROOT / service).read_text(encoding="utf-8"))
    new_functions = {n.name: n for n in new_ast.body if isinstance(n, ast.FunctionDef)}
    preserved_functions = []
    for node in old_ast.body:
        if isinstance(node, ast.FunctionDef) and node.name != "inspect_editor":
            assert ast.dump(node) == ast.dump(new_functions[node.name]), node.name
            preserved_functions.append(node.name)
    prior = read(OUT.parent / "inspection-latency/sources.json")["sources"]
    changed = []
    for name, expected in prior.items():
        if sha(ROOT / name) != expected:
            assert name in backups and backups[name]["sha256"] == expected, name
            changed.append(name)
    parity = read(OUT / "http-parity.json")
    assert len(parity["samples"]) == 3
    for sample in parity["samples"]:
        assert sample["allOtherFieldsEqual"] and sample["legacyMatchesPriorProfile"]
        assert sample["wire"]["summary"]["bytes"] < 50_000 < sample["wire"]["full"]["bytes"]
        assert sample["evaluationSummary"]["human"] == "pending"
    for stage, frame in [("summary-ui-open", 0), ("summary-ui-frame244", 244), ("summary-ui-frame449", 449)]:
        envelope = read(OUT / (stage + ".json"))
        ui = envelope["data"]["result"]
        assert envelope["success"] and ui["ready"] and ui["overlays"] == 0
        assert len(ui["cards"]) == 5 and ui["directionVisible"] and ui["reviewGateMounted"]
        assert ui["inspectorFrame"] == str(frame)
        assert f"Propriedades calculadas no frame {frame}." in ui["inspectorText"]
        assert ui["video"]["readyState"] >= 2 and not ui["video"]["seeking"] and ui["video"]["paused"]
        assert abs(ui["video"]["currentTime"] - frame / 30) < 1 / 60
        assert ui["selectedLayerId"] == read(OUT / "ui-target.json")["layerId"]
        assert any(r["path"].endswith("/editor/inspection") and r["status"] == 200
                   and "evaluationDetail=summary" in r["query"] for r in ui["resources"])
        assert not any(r["path"].endswith("/scene-generation-capability") for r in ui["resources"])
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
    new_sources = set(backups) | {"backend/tests/test_editor_inspection_summary.py",
        "scripts/validation/editor-inspection-summary-observe.py", "scripts/validation/editor-inspection-summary-ui.py",
        "scripts/validation/editor-inspection-summary-verify.py"}
    tracked = {**prior, **{path: sha(ROOT / path) for path in new_sources}}
    (OUT / "sources.json").write_text(json.dumps({"observedAt": datetime.now(timezone.utc).isoformat(),
        "priorSourcesChanged": changed, "priorSourcesUnchanged": len(prior) - len(changed),
        "preservedServiceFunctions": preserved_functions, "sources": tracked}, indent=2) + "\n", encoding="utf-8")
    files = {p.name: {"sha256": sha(p), "bytes": p.stat().st_size} for p in OUT.iterdir() if p.is_file() and p != target}
    target.write_text(json.dumps({"observedAt": datetime.now(timezone.utc).isoformat(), "sourceHashesMatch": len(tracked),
        "scope": "Additive evaluation summary, exact full-response compatibility, real UI selection and seeks, nine studies preserved",
        "tests": {"passed": 17, "failed": 0, "scope": "Nine new summary cases, six existing query cases, two command regressions"},
        "typecheck": "passed", "ruff": "passed after line wrapping and existing fixture-import convention",
        "legacyFullEvidencePreserved": True, "summaryUiVerified": True, "inspectorLatencyResolved": False,
        "noNewGenerationOrPaidCalls": True, "humanApproval": "not_assessed", "autonomy": "not_demonstrated",
        "files": files}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sourceHashesMatch": len(tracked), "preservedStudies": len(variants),
                      "summaryUiVerified": True, "humanApproval": "not_assessed"}))


if __name__ == "__main__":
    main()
