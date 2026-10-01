from copy import deepcopy

from app.services.studios.historical_semantic_reevaluation import reevaluate_production_snapshot


def test_historical_motion_does_not_become_semantic_proof_and_source_is_unchanged():
    snapshot = {
        "pilot": "v31",
        "run": {
            "id": "production",
            "productionGates": {"observedResult": {"status": "passed", "evidence": [{"status": "observed"}]}},
            "visualAudit": {
                "renderChecksum": "a" * 64,
                "actionVerification": {"evidence": [{"status": "observed"}]},
            },
            "artifacts": {
                "plan": {
                    "direction": {
                        "scenes": [{
                            "id": "scene",
                            "elements": [{"id": "empty", "kind": "card"}],
                            "compositions": [{
                                "id": "format", "family": "format_transformation", "targetIds": ["empty"]
                            }],
                        }]
                    }
                },
                "animatic": {"qualityEvaluation": {"metrics": {
                    "silenceRatio": 1.0, "integratedLoudnessLufs": -120.0, "truePeakDbfs": -120.0
                }}},
            },
        },
    }
    original = deepcopy(snapshot)

    receipt = reevaluate_production_snapshot(snapshot, "b" * 64)

    assert snapshot == original
    assert receipt["execution"]["status"] == "observed"
    assert receipt["semantic"]["status"] == "failed"
    assert receipt["human"]["status"] == "pending"
    assert receipt["historicalObservedResult"]["status"] == "passed"
    assert {finding["code"] for finding in receipt["semantic"]["evidence"]} >= {
        "historical_semantic_assertions_missing",
        "historical_format_transformation_has_no_canonical_content",
        "historical_mix_is_silent",
    }
