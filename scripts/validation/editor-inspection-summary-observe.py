"""Compare complete and summary HTTP inspections on the unchanged owned real study."""
import hashlib
import json
import runpy
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "docs/studios/research/editor-oss-20261002/inspection-response"


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def main():
    target = OUT / "http-parity.json"
    if target.exists():
        raise ValueError("preserve_existing_observation")
    helper = runpy.run_path(str(ROOT / "scripts/validation/visual-distance-study.py"))
    token, workspace_id = helper["identity"]()
    original = json.loads((ROOT / "output/visual-directed-native14-20261004/execution.json").read_text(encoding="utf-8"))
    study = original["variants"]["interface-a"]
    baseline = json.loads((OUT.parent / "inspection-latency/interface-a-profile.json").read_text(encoding="utf-8"))
    samples = []
    for frame in [0, 244, 449]:
        values, wire = {}, {}
        for detail in ["full", "summary"]:
            path = f"/api/v1/studios/v1/documents/{study['documentId']}/editor/inspection?frame={frame}"
            if detail == "summary":
                path += "&evaluationDetail=summary"
            started = time.perf_counter()
            with urlopen(Request("http://127.0.0.1:8000" + path,
                                 headers={"Authorization": "Bearer " + token}), timeout=60) as response:
                header_ms = (time.perf_counter() - started) * 1000
                raw = response.read()
                status = response.status
            body_ms = (time.perf_counter() - started) * 1000
            started = time.perf_counter()
            values[detail] = json.loads(raw)
            parse_ms = (time.perf_counter() - started) * 1000
            wire[detail] = {"httpStatus": status, "bytes": len(raw), "headersMs": header_ms,
                            "completeBodyMs": body_ms, "jsonParseMs": parse_ms,
                            "canonicalJsonDigest": digest(values[detail])}
            assert status == 200
            print(json.dumps({"frame": frame, "detail": detail, "bytes": len(raw), "httpMs": round(body_ms, 2)}), flush=True)
        full, summary = values["full"], values["summary"]
        assert full["schemaVersion"] == "studio.editor-inspection.v1"
        assert summary["schemaVersion"] == "studio.editor-inspection.v2"
        assert summary["document"]["workspaceId"] == workspace_id
        assert summary["document"]["revision"] == study["revision"] == 2
        assert summary["document"]["version"] == study["version"] == 1
        assert summary["frame"] == frame and summary["durationFrames"] == 450
        core_full = {k: v for k, v in full.items() if k not in {"schemaVersion", "evaluation"}}
        core_summary = {k: v for k, v in summary.items() if k not in {"schemaVersion", "evaluation"}}
        assert core_full == core_summary
        for axis in ["technical", "audiovisual", "human"]:
            state = full["evaluation"].get(axis)
            if isinstance(state, dict):
                state = state.get("status")
            assert summary["evaluation"][axis] == (state if isinstance(state, str) else None)
        assert summary["evaluation"]["human"] == "pending"
        assert summary["evaluation"]["fullInspectionPath"].endswith(f"?frame={frame}")
        baseline_round = next(r for r in baseline["rounds"] if r["frame"] == frame)
        assert wire["full"]["canonicalJsonDigest"] == baseline_round["http"][0]["canonicalJsonDigest"]
        samples.append({"frame": frame, "wire": wire, "allOtherFieldsEqual": True,
                        "coreDigest": digest(core_full), "legacyMatchesPriorProfile": True,
                        "evaluationSummary": summary["evaluation"], "fullEvaluationDigest": digest(full["evaluation"])})
    target.write_text(json.dumps({"observedAt": datetime.now(timezone.utc).isoformat(),
        "scope": "Six sequential real direct API requests, three frames of the unchanged interface study",
        "documentId": study["documentId"], "samples": samples,
        "limits": ["Three pairs, always full then summary; not randomized, not p95 or a controlled speedup benchmark",
                   "Wire-size and field-parity comparison is exact for the observed responses",
                   "get_plan still hydrates and validates history; no CPU or scrubbing latency guarantee",
                   "Full QC evidence was not discarded, regenerated or reclassified"]}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
