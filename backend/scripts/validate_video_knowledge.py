from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

R1_IDS = (
    "instagram-DTRBJoOAUl1",
    "instagram-DcuHK9ChRrP",
    "instagram-DcRjR01BFVM",
    "instagram-DciIBRYBHBK",
    "instagram-DcsuFSGhnlw",
    "instagram-Dcq32xNgO1d",
    "instagram-DaJVyavI65T",
    "instagram-DZiYEzBvZOc",
    "instagram-DbBddW3JNKD",
    "instagram-Dbhmn9eOiXN",
    "blender-charge-factory-invasion",
    "blender-sprite-fright-forest-reveal",
)


def validate_shots(path: Path) -> list[str]:
    errors: list[str] = []
    data = json.loads(path.read_text(encoding="utf-8"))
    shots = data.get("shots", [])
    if not shots:
        return [f"empty_shot_map:{path}"]
    if shots[0]["start_ms"] != 0:
        errors.append(f"shot_map_not_zero:{path}")
    if shots[-1]["end_ms"] != data["duration_ms"]:
        errors.append(f"shot_map_not_complete:{path}")
    cursor = 0
    for shot in shots:
        if shot["start_ms"] != cursor:
            errors.append(f"shot_map_gap_or_overlap:{path}:{cursor}:{shot['start_ms']}")
        if shot["end_ms"] <= shot["start_ms"]:
            errors.append(f"nonpositive_shot:{path}:{shot['shot_id']}")
        if not shot.get("human_review_required"):
            errors.append(f"machine_map_missing_review_flag:{path}:{shot['shot_id']}")
        cursor = shot["end_ms"]
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--knowledge-root", type=Path, required=True)
    parser.add_argument("--temporary-sources-deleted", action="store_true")
    args = parser.parse_args()
    decisions_path = args.knowledge_root / "ledgers" / "r1-review-decisions.json"
    decisions = (
        json.loads(decisions_path.read_text(encoding="utf-8"))
        if decisions_path.exists()
        else {"units": {}, "taxonomy_decision": "pending"}
    )
    errors: list[str] = []
    analyses: list[dict[str, object]] = []
    downloads: list[dict[str, object]] = []
    for unit_id in R1_IDS:
        unit = args.knowledge_root / "corpus" / unit_id
        analysis = unit / "analysis.md"
        shots = unit / "shots.json"
        if not analysis.exists():
            errors.append(f"missing_analysis:{unit_id}")
            continue
        if not shots.exists():
            errors.append(f"missing_shots:{unit_id}")
            continue
        errors.extend(validate_shots(shots))
        data = json.loads(shots.read_text(encoding="utf-8"))
        analyses.append(
            {
                "unit_id": unit_id,
                "analysis_path": str(analysis.relative_to(args.knowledge_root)),
                "shots_path": str(shots.relative_to(args.knowledge_root)),
                "temporal_map_complete": not any(unit_id in error for error in errors),
                "provenance_complete": bool(data.get("source_url") and data.get("source_checksum_sha256")),
                "human_reviewed": decisions["units"].get(unit_id) == "approved",
                "human_review_decision": decisions["units"].get(unit_id, "pending"),
            }
        )
        downloads.append(
            {
                "unit_id": unit_id,
                "source_url": data["source_url"],
                "checksum_sha256": data["source_checksum_sha256"],
                "accessed_at": "2026-09-01",
                "purpose": "R1 audiovisual research",
                "persisted_in_repository": False,
                "temporary_source_deleted": args.temporary_sources_deleted,
                "deletion_recorded_at": datetime.now(UTC).isoformat() if args.temporary_sources_deleted else None,
            }
        )
    minds = [path for path in (args.knowledge_root / "minds").iterdir() if path.is_dir()]
    for mind in minds:
        for required in (
            "profile.md",
            "sources.json",
            "heuristics.yaml",
            "critique-rubric.yaml",
            "collaborators.json",
            "cases/README.md",
        ):
            if not (mind / required).exists():
                errors.append(f"mind_missing:{mind.name}:{required}")
    repositories = json.loads((args.knowledge_root / "repositories" / "registry.json").read_text(encoding="utf-8"))
    coverage = json.loads((args.knowledge_root / "ledgers" / "coverage.json").read_text(encoding="utf-8"))
    if repositories["actual_count"] != 42:
        errors.append("repository_count_not_42")
    if len(minds) != 30:
        errors.append("mind_count_not_30")
    if coverage["planned"] != 900:
        errors.append("corpus_manifest_not_900")
    ledger_root = args.knowledge_root / "ledgers"
    ledger_root.mkdir(parents=True, exist_ok=True)
    (ledger_root / "downloads.json").write_text(
        json.dumps(
            {"schema_version": "studio.temporary-download-ledger.v1", "entries": downloads},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    blockers = [f"human_review_required:{item['unit_id']}" for item in analyses if not item["human_reviewed"]]
    taxonomy_approved = decisions.get("taxonomy_decision") == "approved"
    if not taxonomy_approved:
        blockers.append("taxonomy_human_approval_required")
    if errors:
        blockers.extend(errors)
    (ledger_root / "r1-gate.json").write_text(
        json.dumps(
            {
                "schema_version": "studio.creative-research-gate.v1",
                "pilot_id": "r1-2026-09-01",
                "analyses": analyses,
                "taxonomy_report_path": "R1_TAXONOMY_CORRECTION_REPORT.md",
                "taxonomy_human_approved": taxonomy_approved,
                "corpus_expansion_eligible": not blockers,
                "expensive_generation_eligible": False,
                "blockers": sorted(set(blockers)),
                "evaluated_at": datetime.now(UTC).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (ledger_root / "validation.json").write_text(
        json.dumps(
            {
                "schema_version": "studio.video-knowledge-validation.v1",
                "valid": not errors,
                "errors": errors,
                "r1_analysis_count": len(analyses),
                "r1_human_approved_count": sum(
                    bool(item["human_reviewed"]) for item in analyses
                ),
                "mind_scaffold_count": len(minds),
                "repository_audit_count": repositories["actual_count"],
                "corpus_planned_count": coverage["planned"],
                "corpus_annotated_count": coverage["annotated_in_main_corpus"],
                "validated_at": datetime.now(UTC).isoformat(),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    if errors:
        for error in errors:
            print(error)
        return 1
    if blockers:
        print("R1 artifacts valid; human review gate remains closed.")
    else:
        print("R1 artifacts valid; human review gate is open for corpus expansion.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
