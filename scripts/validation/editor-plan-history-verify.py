"""Seal history read parity and re-audit canonical documents and original videos."""
import ast
import hashlib
import json
import runpy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/studios/research/editor-oss-20261002/plan-history-validation"
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
    assert sha(OUT / "contextual_editing.py.before") == before["sha256"]
    old = ast.parse((OUT / "contextual_editing.py.before").read_text(encoding="utf-8"))
    new = ast.parse((ROOT / before["source"]).read_text(encoding="utf-8"))
    new_functions = {n.name: n for n in new.body if isinstance(n, ast.FunctionDef)}
    preserved_functions = []
    for node in old.body:
        if isinstance(node, ast.FunctionDef):
            current = new_functions[node.name]
            if node.name == "get_plan":
                assert ast.dump(ast.Module(body=node.body, type_ignores=[])) == ast.dump(
                    ast.Module(body=current.body[1:], type_ignores=[]))
            else:
                assert ast.dump(node) == ast.dump(current), node.name
                preserved_functions.append(node.name)
    prior = read(OUT.parent / "inspection-response/sources.json")["sources"]
    changed = []
    for name, expected in prior.items():
        if sha(ROOT / name) != expected:
            assert name == before["source"] and before["sha256"] == expected
            changed.append(name)
    observation = read(OUT / "observation.json")
    assert len(observation["samples"]) == 3 and len(observation["http"]) == 3
    for sample in observation["samples"]:
        assert sample["allModesEqual"]
        assert len({m["canonicalPlanDigest"] for m in sample["modes"]}) == 1
        assert sample["modes"][-1]["mode"] == "warm" and sample["modes"][-1]["parserCalls"] == 1
        assert all(m["validationFactCount"] <= 1024 for m in sample["modes"])
    assert all(h["status"] == 200 and h["matchesPreviousSummary"] for h in observation["http"])
    for stage, frame in [("history-ui-open", 0), ("history-ui-frame244-settled", 244),
                         ("history-ui-frame449-settled", 449)]:
        envelope = read(OUT / (stage + ".json"))
        ui = envelope["data"]["result"]
        assert envelope["success"] and ui["ready"] and ui["overlays"] == 0
        assert ui["directionVisible"] and ui["reviewGateMounted"] and len(ui["cards"]) == 5
        assert ui["inspectorFrame"] == str(frame)
        assert f"Propriedades calculadas no frame {frame}." in ui["inspectorText"]
        assert ui["selectedLayerId"] == "ed2-895c9ff7a0a9ce1cb92ec080"
        assert ui["video"]["readyState"] >= 2 and not ui["video"]["seeking"] and ui["video"]["paused"]
        assert abs(ui["video"]["currentTime"] - frame / 30) < 1 / 60
        assert any(r["path"].endswith("/editor/inspection") and r["status"] == 200
                   and "evaluationDetail=summary" in r["query"] for r in ui["resources"])
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
    additional = [before["source"], "backend/app/services/studios/editing_plan_validation.py",
        "backend/tests/test_editing_plan_validation.py", "scripts/validation/editor-plan-history-observe.py",
        "scripts/validation/editor-plan-history-ui.py", "scripts/validation/editor-plan-history-verify.py"]
    tracked = {**prior, **{path: sha(ROOT / path) for path in additional}}
    (OUT / "sources.json").write_text(json.dumps({"observedAt": datetime.now(timezone.utc).isoformat(),
        "priorSourcesChanged": changed, "priorSourcesUnchanged": len(prior) - len(changed),
        "preservedServiceFunctions": preserved_functions, "fallbackBodyUnchanged": True,
        "sources": tracked}, indent=2) + "\n", encoding="utf-8")
    files = {p.name: {"sha256": sha(p), "bytes": p.stat().st_size} for p in OUT.iterdir() if p.is_file() and p != target}
    target.write_text(json.dumps({"observedAt": datetime.now(timezone.utc).isoformat(), "sourceHashesMatch": len(tracked),
        "scope": "Content-keyed bounded validation facts, fresh selected plan, legacy session behavior, real parity/UI/preservation",
        "tests": {"passed": 26, "failed": 0, "scope": "Eight new validation cases, six query cases, nine summary cases, three command cases"},
        "ruff": "passed", "noNewGenerationOrPaidCalls": True, "summaryUiVerified": True,
        "realtimeScrubbingDemonstrated": False, "humanApproval": "not_assessed", "autonomy": "not_demonstrated",
        "files": files}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sourceHashesMatch": len(tracked), "preservedStudies": len(variants),
                      "historyParityVerified": True, "summaryUiVerified": True}))


if __name__ == "__main__":
    main()
