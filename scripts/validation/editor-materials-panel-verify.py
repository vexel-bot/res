"""Verify saved real UI evidence and the exact current source checkpoint."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/studios/research/editor-oss-20261002/materials-and-panel-loading"


def read(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def observed(stage):
    envelope = read(stage + ".json")
    assert envelope["success"]
    v = envelope["data"]["result"]
    assert v["ready"] and v["overlays"] == 0
    assert v["reviewGateMounted"]
    assert v["video"]["readyState"] >= 2 and not v["video"]["seeking"]
    assert (v["video"]["width"], v["video"]["height"], v["video"]["duration"]) == (1080, 1920, 15)
    assert len(v["cards"]) == 5
    assets = read("interface-a-document-after.json")["assets"]
    assert [(c["assetId"], c["mediaType"]) for c in v["cards"]] == [(a["id"], a["mediaType"]) for a in assets]
    for index, card in enumerate(v["cards"], 1):
        label = "Fonte tipográfica" if card["mediaType"].startswith("font/") else "Áudio" if card["mediaType"].startswith("audio/") else "Vídeo"
        assert card["title"] == f"{label} {index}"
        assert card["rights"] == f"{label} · direitos verificados"
        assert card["videoElements"] == (1 if label == "Vídeo" else 0)
        assert "Take" not in card["title"] and "Prévia pendente" not in card["thumbnailText"]
    return v


def capability_requests(v):
    return [r for r in v["resources"] if r["path"].endswith("/scene-generation-capability")]


def main():
    current = read("sources.json")["sources"]
    for path, expected in current.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected, path
    initial = observed("probe-final-initial-settled")
    assert not initial["directionMounted"] and not capability_requests(initial)
    assert not any(r["path"].endswith(("/editing/repertoire", "/editing-plans/latest")) for r in initial["resources"])
    opened = observed("probe-final-open")
    assert opened["directionVisible"] and not capability_requests(opened)
    assert opened["localProbe"]["selected"] is False and opened["localProbe"]["optionDisabled"]
    failed = observed("probe-failed")
    assert len(capability_requests(failed)) == 1 and capability_requests(failed)[0]["status"] == 0
    assert failed["localProbe"]["alerts"] == ["Não foi possível verificar o gerador local. Tente novamente."]
    assert failed["localProbe"]["selected"] is False and not failed["localProbe"]["disabled"]
    retrying = observed("probe-retrying")
    assert retrying["localProbe"]["disabled"] and retrying["localProbe"]["selected"] is False
    recovered = observed("probe-recovered")
    assert [r["status"] for r in capability_requests(recovered)] == [0, 200]
    assert recovered["localProbe"]["alerts"] == [] and recovered["localProbe"]["capability"]
    assert recovered["localProbe"]["selected"] is False
    for stage, visible in [("final-draft-open", True), ("final-draft-hidden", False), ("final-draft-reopened", True)]:
        v = observed(stage)
        assert v["directionMounted"] and v["directionVisible"] == visible
        assert v["directionDraft"] == "rascunho-final-20261005"
    clean = observed("final-clean-settled")
    assert clean["directionDraft"] == "" and not capability_requests(clean)
    preservation = read("api-preservation.json")
    assert len(preservation["variants"]) == 9
    assert all(v["compositionAndAssetsEqualOriginalRenderSnapshot"] for v in preservation["variants"].values())
    assert len(preservation["comparisons"]) == 3
    assert all(v["status"] == "not_assessed" and v["review"] is None and v["labelsUnchanged"] for v in preservation["comparisons"].values())
    print(json.dumps({"sourceHashesMatch": len(current), "materialCards": 5,
                      "deferredDirectionPanel": True, "localProbeRequiresClick": True,
                      "localProbeFailureAndRealRecovery": True, "draftSurvivesTabSwitch": True,
                      "preservedStudies": 9, "humanReviews": "not_assessed"}))


if __name__ == "__main__":
    main()
