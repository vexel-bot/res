# ruff: noqa: F811
from types import SimpleNamespace

import pytest
from test_contextual_editing import media as media
from test_contextual_editing import project as project
from test_editorial_production import brief, endpoint, headers
from test_remotion_native import native_direction

from app.config import get_settings
from app.domain.studios.editorial_production import ProductionRequestV1
from app.services.studios import engine_qualification


def test_old_production_request_serialization_and_engine_choice_are_preserved():
    request = ProductionRequestV1.model_validate(brief())
    assert "renderEngine" not in request.model_dump(by_alias=True)
    assert "render_engine" not in request.model_dump()
    candidate = native_direction()
    candidate.render_engine = "alight_motion"
    request.bind_render_engine(candidate)
    assert candidate.render_engine == "current" and candidate.engine_profile is None


@pytest.mark.parametrize("mode,profile", [("motion", "kinetic_type"), ("mixed_montage", "action_product")])
def test_user_engine_choice_overrides_planner_and_survives_snapshot(mode, profile):
    request = ProductionRequestV1.model_validate({**brief(), "mode": mode, "renderEngine": "alight_motion"})
    candidate = request.bind_render_engine(native_direction())
    assert candidate.render_engine == "alight_motion" and candidate.engine_profile == profile
    assert ProductionRequestV1.model_validate(request.model_dump(by_alias=True)).render_engine == "alight_motion"


def test_unavailable_alight_blocks_before_planning_or_budget_reservation(client, project, monkeypatch):
    monkeypatch.setattr(get_settings(), "studio_alight_motion_enabled", True)
    monkeypatch.setattr(
        engine_qualification,
        "engine_capabilities",
        lambda: {
            "engines": [
                {
                    "provider": "alight-motion.contextual-v1",
                    "available": False,
                    "blockers": ["physical_device_missing", "validated_import_missing"],
                }
            ]
        },
    )
    from app.services.studios import editorial_production

    def no_budget_call(*args):
        pytest.fail("Unusable Alight must be rejected before acquiring the budget lock")

    monkeypatch.setattr(editorial_production, "lock_editing_budget", no_budget_call)
    response = client.post(
        endpoint(project), headers=headers(project), json={**brief(), "renderEngine": "alight_motion"}
    )
    assert response.status_code == 422
    assert "alight_worker_not_ready:physical_device_missing,validated_import_missing" in response.text


def test_disabled_experiment_does_not_probe_devices(client, project, monkeypatch):
    def no_probe():
        pytest.fail("Disabled experiment must not probe a device")

    monkeypatch.setattr(engine_qualification, "engine_capabilities", no_probe)
    response = client.post(
        endpoint(project), headers=headers(project), json={**brief(), "renderEngine": "alight_motion"}
    )
    assert response.status_code == 422
    assert "alight_experiment_access_denied" in response.text


def test_non_owner_cannot_use_production_motor(monkeypatch):
    from app.services.studios.editorial_production import require_production_engine

    monkeypatch.setattr(get_settings(), "studio_alight_motion_enabled", True)
    db = SimpleNamespace(scalar=lambda query: SimpleNamespace(role="editor"))
    request = ProductionRequestV1.model_validate({**brief(), "renderEngine": "alight_motion"})
    with pytest.raises(ValueError, match="alight_experiment_access_denied"):
        require_production_engine(db, SimpleNamespace(workspace_id="w"), request, SimpleNamespace(id="u"))
