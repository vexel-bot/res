"""Verify readonly catalog observations and preservation of the nine studies."""
import difflib
import hashlib
import json
import runpy
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/studios/research/editor-oss-20261002/resource-search"
ORIGINAL = ROOT / "output/visual-directed-native14-20261004"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    target = OUT / "verification.json"
    if target.exists():
        raise ValueError("preserve_existing_verification")
    prior = read(OUT.parent / "catalog-loading/sources.json")["sources"]
    assert all(sha(ROOT / path) == expected for path, expected in prior.items())
    before = read(OUT / "before.json")
    assert sha(OUT / "EditingResourcesPanel.tsx.before") == before["sha256"]
    old = (OUT / "EditingResourcesPanel.tsx.before").read_text(encoding="utf-8")
    new = (ROOT / before["source"]).read_text(encoding="utf-8")
    diff = "".join(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                     fromfile=before["source"] + ".before", tofile=before["source"]))
    (OUT / "EditingResourcesPanel.tsx.diff").write_text(diff, encoding="utf-8")
    ui = {}
    for stage, query, status in [("visible-initial", "", "ready"),
                                 ("latest-query", "interface", "ready"),
                                 ("failed-query", "bloqueiocodex20261005", "failed"),
                                 ("recovered-scrolled-query", "bloqueiocodex20261005", "ready")]:
        envelope = read(OUT / (stage + ".json"))
        v = envelope["data"]["result"]
        assert envelope["success"] and v["ready"] and v["overlays"] == 0
        catalog = v["catalog"]
        assert catalog["open"] and catalog["query"] == query and catalog["status"] == status
        assert catalog["busy"] == "false" and v["video"]["readyState"] >= 2
        ui[stage] = v
    assert len(ui["visible-initial"]["catalog"]["rows"]) == 46
    assert len(ui["latest-query"]["catalog"]["rows"]) == 22
    assert ui["failed-query"]["catalog"]["rows"] == []
    assert len(ui["failed-query"]["catalog"]["alerts"]) == 1
    recovered = ui["recovered-scrolled-query"]
    assert recovered["catalog"]["rows"] == [] and recovered["catalog"]["alerts"] == []
    assert any(r["status"] == 200 and r["query"].endswith("query=bloqueiocodex20261005")
               for r in recovered["resources"] if r["path"].endswith("/editing/resources"))
    helper = runpy.run_path(str(ROOT / "scripts/validation/visual-distance-study.py"))
    _, workspace_id = helper["identity"]()
    helper["api"].__globals__["BASE"] = "http://127.0.0.1:8000/api/v1"
    api = helper["api"]
    catalog = api("/studios/v1/editing/resources?workspace_id=" + workspace_id + "&query=interface")
    assert [row["id"] for row in catalog] == [row["id"] for row in ui["latest-query"]["catalog"]["rows"]]
    execution = read(ORIGINAL / "execution.json")
    preserved = {}
    for name, variant in execution["variants"].items():
        document = api("/studios/v1/documents/" + variant["documentId"])
        snapshot = read(ORIGINAL / (name + "-render.json"))["snapshot"]
        assert document["workspaceId"] == workspace_id
        assert document["revision"] == snapshot["revision"] == variant["revision"] == 2
        assert document["version"] == snapshot["version"] == 1
        assert document["composition"] == snapshot["composition"] and document["assets"] == snapshot["assets"]
        assert sha(ORIGINAL / (name + ".mp4")) == variant["artifact"]["checksumSha256"]
        preserved[name] = {"documentId": document["documentId"], "revision": 2,
                           "compositionAndAssetsUnchanged": True, "mp4Sha256": variant["artifact"]["checksumSha256"]}
    comparisons = {}
    for name, original in execution["comparisons"].items():
        current = api(f"/studios/v1/workspaces/{workspace_id}/visual-study-comparisons/{original['id']}")
        assert current["status"] == "not_assessed" and current["review"] is None
        assert current["labels"] == original["labels"]
        comparisons[name] = {"id": current["id"], "status": current["status"], "review": None}
    additional = {before["source"], "src/studios/latestResourceRead.ts", "tests/unit/latestResourceRead.test.ts",
                  "scripts/validation/editor-resource-search-ui.py", "scripts/validation/editor-resource-search-verify.py"}
    sources = {**prior, **{path: sha(ROOT / path) for path in additional}}
    (OUT / "sources.json").write_text(json.dumps({"priorSourcesUnchanged": len(prior), "sources": sources}, indent=2) + "\n", encoding="utf-8")
    target.write_text(json.dumps({"observedAt": datetime.now(timezone.utc).isoformat(),
        "sourcesVerified": len(sources), "catalogIdsEqualActualApi": True, "readonlyFailureRecovery": True,
        "diagnosticObservationsRetained": ["initial", "initial-open", "recovered-query", "recovered-visible-query"],
        "scopeLimit": "Offscreen CLI clicks were ineffective; successful observations required explicit scrolling. No p95 or aesthetic claim.",
        "variants": preserved, "comparisons": comparisons,
        "humanFeedback": "User overall rating 1; no structured approval written",
        "paidGenerationCalls": 0, "newRenders": 0}, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"sources": len(sources), "variants": len(preserved), "comparisons": len(comparisons), "verified": True}))


if __name__ == "__main__":
    main()
