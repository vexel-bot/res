"""Preserve raw pytest results and classify failures without hiding or skipping them."""

import json
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


def identity(case):
    classname = case.get("classname", "").replace("\\", "/")
    # pytest rootdir changes can prefix the same backend test with "backend.".
    # Normalize only that known package, never arbitrary third-party namespaces.
    if classname.startswith("backend.tests."):
        classname = classname.removeprefix("backend.")
    return classname + "::" + case.get("name", "")


def read(path):
    root = ET.parse(path).getroot()
    records = []
    for case in root.iter("testcase"):
        failure = case.find("failure")
        error = case.find("error")
        skipped = case.find("skipped")
        kind = "failure" if failure is not None else "error" if error is not None else "skipped" if skipped is not None else "passed"
        nodes = case.findall("failure") + case.findall("error")
        if nodes:
            for index, node in enumerate(nodes):
                records.append({"id": identity(case) + (f"::subcase-{index}" if len(nodes) > 1 else ""),
                    "status": kind, "diagnostic": node.text or node.get("message", "")})
        else:
            records.append({"id": identity(case), "status": kind,
                "diagnostic": "" if skipped is None else skipped.text or skipped.get("message", "")})
    suites = [root] if root.tag == "testsuite" else list(root.findall("testsuite"))
    counts = {name: sum(int(suite.get(name, "0")) for suite in suites) for name in ("tests", "failures", "errors", "skipped")}
    counts["passed"] = counts["tests"] - counts["failures"] - counts["errors"] - counts["skipped"]
    return records, counts


def classify(row):
    text = row["diagnostic"]
    if "third_party.craft.filmcraft.packaging.linux" in row["id"]:
        return "linux_packaging_on_windows"
    if "external_monthly_budget_required" in text or "external_model_budget_required" in text:
        return "test_fixture_requires_explicit_financial_envelope"
    if "FileNotFoundError" in text:
        return "missing_artifact_manifest_or_runtime"
    if "can't open file" in text or "Native review wheels missing" in text or (
        "test_longcat_avatar_integration::test_preflight_is_read_only" in row["id"]
    ):
        return "missing_worker_source_or_verified_wheels"
    if "test_video_creative_preproduction_api::" in row["id"]:
        return "qualification_read_model_evidence_missing"
    if "ImportError" in text and ("creatives" in text or "Alight" in text):
        return "retired_helper_or_provider_contract"
    if any(value in text for value in (
        "editor_replaced_by_effectcraft", "ContextualFFmpegProvider", "studio_review_native_migration_required",
        "craft_project_content_requires_native_commands_or_migration", "assert 'craft.effectcraft' == 'remotion",
    )) or ("410" in text and "assert" in text):
        return "retired_endpoint_or_engine_contract"
    if any(value in text for value in ("craft_engine_unavailable", "CRAFT_BROWSER_RUNTIME_NOT_BUILT", "craft_runtime_error")):
        return "native_craft_runtime_missing"
    if "test_speech_cpu_requirements_digest_is_frozen" in row["id"]:
        return "integrity_lock_mismatch_not_bypassed"
    return "requires_individual_diagnosis"


def main():
    current, counts = read(Path(sys.argv[1]))
    baseline, baseline_counts = read(Path(sys.argv[2]))
    old_failures = {row["id"] for row in baseline if row["status"] in {"failure", "error"}}
    current_ids = {row["id"] for row in current}
    failures = [row for row in current if row["status"] in {"failure", "error"}]
    for row in failures:
        row["category"] = classify(row)
        row["presentInBaseline"] = row["id"] in old_failures
    result = {"schemaVersion": "clicko.stage1-test-triage.v1", "rawCounts": counts,
        "baselineCounts": baseline_counts,
        "failureCategories": dict(Counter(row["category"] for row in failures)),
        "newFailureIds": [row["id"] for row in failures if not row["presentInBaseline"]],
        "resolvedBaselineFailureIds": sorted((old_failures & current_ids) - {row["id"] for row in failures}),
        "baselineFailureIdsNotCollected": sorted(old_failures - current_ids),
        "failures": failures,
        "note": "JUnit includes unittest subcases. Known backend package prefixes are normalized. "
            "Not-collected baseline failures are not resolutions. Categories are diagnostic triage, not qualification."}
    Path(sys.argv[3]).write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({key: value for key, value in result.items() if key not in {"failures"}}, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
