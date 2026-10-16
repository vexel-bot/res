"""Retain failed real-job QC evidence before the test fixture tears down its DB.

Only records existing results. It never suppresses failures or changes a test.
"""
import hashlib
import json
import os
import shutil
from pathlib import Path

import pytest


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if call.when != "call" or not report.failed or not call.excinfo:
        return
    folder = os.environ.get("TEMPORAL_MATTE_EVIDENCE_DIR")
    if not folder:
        return
    for entry in call.excinfo.traceback:
        values = entry.frame.f_locals
        result = values.get("result")
        name = values.get("name")
        if not isinstance(result, dict) or not name or "artifact" not in result:
            continue
        output = Path(folder) / name
        output.mkdir(parents=True, exist_ok=True)
        files = {}
        for source_key, target_name in [("intermediate", "graphics-intermediate.mp4"),
                                        ("image", "original-matte.png")]:
            source = values.get(source_key)
            if isinstance(source, Path) and source.is_file():
                shutil.copy2(source, output / target_name)
                files[target_name] = hashlib.sha256(source.read_bytes()).hexdigest()
        evidence = {"scope": "failed_actual_API_job_diagnostic", "test": item.nodeid,
                    "technicalQcStatus": result.get("qualityEvaluation", {}).get("status"),
                    "failure": str(call.excinfo.value), "humanReview": "pending",
                    "renderResult": result, "inspection": values.get("inspection"),
                    "retainedFiles": files}
        (output / "failed-qc-evidence.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        break
