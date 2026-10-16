"""Export inspection evidence; never submit or synthesize a human review."""

import argparse
import hashlib
import json
import os
import runpy
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
study = runpy.run_path(str(ROOT / "scripts/validation/visual-distance-study.py"))
OUT = study["OUT"]


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["verify", "receipts", "revise-interface"])
    parser.add_argument("--study", choices=["organization", "comparison", "interface"])
    args = parser.parse_args()
    state = json.loads(study["STATE"].read_text(encoding="utf-8"))
    if args.mode == "revise-interface":
        archive = OUT / "interface-fast-input-cycle"
        archive.mkdir(exist_ok=True)
        for variant in state["variants"]:
            if variant["study"] != "interface":
                continue
            if variant["status"] != "succeeded":
                raise ValueError("previous_job_must_finish_before_revision")
            variant.setdefault("supersededRenders", []).append({
                "result": variant["result"], "metadata": variant["metadata"],
                "reason": "Sampled capture filled the field too fast; replaced by progressive real keyboard input.",
            })
            for suffix in (".mp4", "-plan.json"):
                source = OUT / (variant["key"] + suffix)
                source.replace(archive / source.name)
            variant["status"] = "needs_source_correction"
            variant.setdefault("interventions", []).append(
                "Capture revised: longer initial reading interval and progressive typing, then a real persisted apply."
            )
        if "interface" in state.get("comparisons", {}):
            state.setdefault("supersededComparisons", []).append(state["comparisons"].pop("interface"))
        study["save"](state)
        return
    if args.mode == "verify":
        token, workspace = study["identity"]()
        origin = os.environ.get("VISUAL_STUDY_UI_ORIGIN", "http://127.0.0.1:3000")
        targets = [{"name": v["study"], "url": v["url"].replace("http://127.0.0.1:3000", origin)}
                   for v in state["variants"] if v["variant"] == "a" and (not args.study or v["study"] == args.study)]
        if len(state.get("comparisons", {})) != 3:
            raise ValueError("three_frozen_sessions_required")
        process = subprocess.Popen(["node", str(ROOT / "scripts/validation/verify-visual-distance.mjs")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        process.stdin.write(json.dumps({"token": token, "workspaceId": workspace, "out": str(OUT), "studies": targets}))
        process.stdin.close()
        lines = []
        with (OUT / "studio-verification.log").open("w", encoding="utf-8") as log:
            for line in process.stdout:
                lines.append(line)
                log.write(line)
                log.flush()
                print(line, end="", flush=True)
        if process.wait():
            raise ValueError("studio_verification_failed:" + "".join(lines)[-3000:])
        return
    renders = []
    for variant in state["variants"]:
        if variant["status"] != "succeeded":
            raise ValueError("unfinished_variant:" + variant["key"])
        artifact = variant["result"]["artifact"]
        path = OUT / (variant["key"] + ".mp4")
        if hashlib.sha256(path.read_bytes()).hexdigest() != artifact["checksumSha256"]:
            raise ValueError("local_artifact_checksum_mismatch")
        qc = variant["result"]["qualityEvaluation"]
        renders.append({"key": variant["key"], "documentId": variant["documentId"],
            "revision": variant["revision"], "planId": variant["planId"], "jobId": variant["jobId"],
            "provider": variant["result"]["provider"], "providerVersion": variant["result"]["providerVersion"],
            "artifact": artifact, "localPath": str(path), "renderDurationMs": variant["result"]["renderDurationMs"],
            "qcStatus": qc["status"], "qcWarnings": [c for c in qc["checks"] if c["status"] != "passed"],
            "visualStatus": "not_assessed", "autonomy": "not_demonstrated", "interventions": variant["interventions"]})
    write("render-index.json", {"schemaVersion": "res.visual-distance-render-index.v1", "renders": renders,
        "comparisons": state.get("comparisons", {}), "paidApiSpendUsd": 0,
        "humanReview": "pending", "autonomy": "not_demonstrated"})
    write("cost-receipt.json", {"schemaVersion": "res.local-study-cost.v1",
        "budgetGroupId": state["budgetGroupId"], "sharedCapUsd": 10, "phaseApiSpendUsd": 0,
        "paidCalls": [], "rejectedPaidAttempts": [],
        "scope": "Only this local round; does not assert unused balance of other rounds",
        "localExecution": "Remotion and FFmpeg; device/electricity costs not priced", "renderJobIds": [r["jobId"] for r in renders]})
    write("human-review-template.json", {"schemaVersion": "res.pending-human-study-review.v1",
        "status": "not_assessed", "instruction": "Watch all options in the Studio blind panel before entering scores. This file is not a receipt.",
        "studies": [{"study": name, "comparisonId": session["id"], "preferredLabel": None,
            "clarity": None, "rhythm": None, "continuity": None, "finish": None, "suitability": None,
            "fullVideoInspected": False, "mobileInspected": False, "audioInspected": False,
            "notes": "", "findings": []} for name, session in state.get("comparisons", {}).items()]})
    write("inspection-findings.json", {"schemaVersion": "res.agent-triage-findings.v1",
        "isHumanReview": False, "fullVideoAestheticApproval": "pending", "findings": [
            {"study": "interface", "sceneId": "study", "startSeconds": 0, "endSeconds": 6,
             "cause": "material", "status": "corrected_awaiting_human_review",
             "observation": "Earlier sampled capture filled the field too fast to follow the action.",
             "correction": "Replace capture with progressive real typing and initial reading pause; new assets and three new jobs.",
             "evidence": "interface-task-contact.png / interface-capture-evidence.json / supersededRenders"},
            {"study": "comparison", "sceneId": "study", "startSeconds": 0, "endSeconds": 15,
             "cause": "direction", "status": "pending_human_review",
             "observation": "Both graphic studies use the same three labels and closely related organization/connection transforms.",
             "correction": "If concept remains unclear in review, revise canonical initial/final state and relationships to explain a concrete difference, then rerender.",
             "evidence": "comparison-a-plan.json / organization-a-plan.json"},
            {"study": "all", "sceneId": "study", "startSeconds": 0, "endSeconds": 15,
             "cause": "sound", "status": "pending_human_listening",
             "observation": "Original sparse PCM accents; QC reports a high silence ratio. Automated playback is muted.",
             "correction": "Listen to full output; adjust event onset, envelope or authored mix if rhythm/synchronism is weak. Never infer audio quality from stream presence.",
             "evidence": "render-index.json qcWarnings / graphic-events.wav"}]})
    lines = ["# Estudos dirigidos — 02/10/2026", "", "QC técnico e avaliação humana são separados. Aprovação visual e autonomia pendentes. APIs nesta rodada: US$ 0.", "",
        "| Estudo/variante | Vídeo local | QC | Render (s) |", "|---|---|---|---|"]
    lines += [f"| {r['key']} | [MP4]({r['key']}.mp4) | {r['qcStatus']} | {r['renderDurationMs']/1000:.1f} |" for r in renders]
    lines += ["", "[Índice com checksums e recibos](render-index.json) · [Custos](cost-receipt.json) · [Avaliação em branco](human-review-template.json)", "",
        "A/B/controle acima identificam artefatos para auditoria; para preferência cega use as opções randomizadas no Studio. Intervenções editoriais constam nos recibos."]
    (OUT / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps({"renders": len(renders), "technicalPassed": sum(r["qcStatus"] == "passed" for r in renders),
        "humanReview": "pending", "paidApiSpendUsd": 0}), flush=True)


if __name__ == "__main__":
    main()
