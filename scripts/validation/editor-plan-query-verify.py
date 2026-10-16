"""Seal latest-plan query evidence and recheck the original directed studies."""
import hashlib
import json
import runpy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/studios/research/editor-oss-20261002/inspection-latency"
ORIGINAL = ROOT / "output/visual-directed-native14-20261004"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = OUT / "verification.json"
    if target.exists():
        raise ValueError("preserve_existing_verification")
    before = read(OUT / "query-before.json")
    assert sha(OUT / "contextual_editing.py.before") == before["sha256"]
    source = ROOT / before["source"]
    # Exact untouched prefix/suffix comparison against this turn's dirty backup.
    old = (OUT / "contextual_editing.py.before").read_bytes()
    new = source.read_bytes()
    start, end = old.index(b"def latest_plan("), old.index(b"\r\n\r\ndef _save(")
    new_start, new_end = new.index(b"def latest_plan("), new.index(b"\r\n\r\ndef _save(")
    assert old[:start] == new[:new_start] and old[end:] == new[new_end:]
    prior = read(OUT.parent / "materials-and-panel-loading/sources.json")["sources"]
    for path, expected in prior.items():
        assert sha(ROOT / path) == expected, path
    observation = read(OUT / "latest-plan-observation.json")
    assert observation["workspacePlanEvents"] == 95
    assert observation["eventMetadataUnchanged"]
    assert observation["eventMetadataDigestBefore"] == observation["eventMetadataDigestAfter"]
    assert len(observation["samples"]) == 3
    for sample in observation["samples"]:
        assert sample["httpStatus"] == 200 and sample["matchesPersistedOrderReference"]
        assert sample["hydratedEventIds"] == [sample["selectedEventId"]]
    initial = read(OUT / "query-ui-settled.json")["data"]["result"]
    opened = read(OUT / "query-ui-open.json")["data"]["result"]
    for ui in [initial, opened]:
        assert ui["ready"] and ui["overlays"] == 0 and len(ui["cards"]) == 5
        assert ui["reviewGateMounted"] and ui["video"]["readyState"] >= 2
        assert (ui["video"]["width"], ui["video"]["height"], ui["video"]["duration"]) == (1080, 1920, 15)
        assert not any(r["path"].endswith("/scene-generation-capability") for r in ui["resources"])
    assert not initial["directionMounted"] and opened["directionVisible"]
    assert opened["inspectorFrame"] == "0"
    browser_latest = [r for r in opened["resources"] if r["path"].endswith("/editing-plans/latest")]
    assert any(r["status"] == 200 for r in browser_latest)
    assert any(r["path"].endswith("/editor/inspection") and r["status"] == 200 for r in opened["resources"])
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
    tracked = {**prior, **{path: sha(ROOT / path) for path in [before["source"],
        "backend/tests/test_editing_plan_projection.py", "scripts/validation/editor-inspection-profile.py",
        "scripts/validation/editor-plan-query-observe.py", "scripts/validation/editor-plan-query-verify.py"]}}
    (OUT / "sources.json").write_text(json.dumps({"observedAt": datetime.now(timezone.utc).isoformat(),
        "priorSourcesUnchanged": len(prior), "sources": tracked}, indent=2) + "\n", encoding="utf-8")
    files = {p.name: {"sha256": sha(p), "bytes": p.stat().st_size} for p in OUT.iterdir() if p.is_file() and p != target}
    target.write_text(json.dumps({"observedAt": datetime.now(timezone.utc).isoformat(), "sourceHashesMatch": len(tracked),
        "scope": "Latest-document query only, three real API selections, one real UI open, nine studies preserved",
        "tests": {"passed": 10, "failed": 0, "scope": "Six query semantics/hydration tests and four existing command/API regressions"},
        "ruff": "passed", "latestQueryHydratesOneEvent": True, "inspectorLatencyResolved": False,
        "noNewGenerationOrPaidCalls": True, "humanApproval": "not_assessed", "autonomy": "not_demonstrated",
        "files": files}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sourceHashesMatch": len(tracked), "preservedStudies": len(variants),
                      "latestQueryHydratesOneEvent": True, "humanApproval": "not_assessed"}))


if __name__ == "__main__":
    main()
