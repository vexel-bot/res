from __future__ import annotations

from pathlib import Path

import pytest

from scripts.inspect_supervision_native_bundles import inspect


@pytest.fixture(autouse=True)
def clean_database() -> None:
    """Keep the offline wheel inspection independent from the database."""


def test_native_wheel_bundle_evidence_is_complete_but_not_auto_approved() -> None:
    root = Path(__file__).resolve().parents[2]
    evidence = inspect(root / ".candidate-build/supervision-wheelhouse-linux")
    assert evidence["packageCount"] == 10
    assert evidence["allWheelsContainLicenseEvidence"] is True
    assert evidence["packagesMissingLicenseEvidence"] == []
    assert evidence["status"] == "human_review_required"
    assert all(item["reviewStatus"] == "human_review_required" for item in evidence["packages"])
