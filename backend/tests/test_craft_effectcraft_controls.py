from app.services.studios.craft_effectcraft_controls import controls


def test_effectcraft_inventory_binds_active_session_and_matches_editing_intent():
    capability = {"buildId": "test", "commands": [
        {"id": "asset.import"}, {"id": "script.run"}, {"id": "host.undo"},
    ]}
    first = controls(capability, {"run_motion_script", "edit_project"}, "frear")
    assert first["controls"][0]["id"] == "interpolation"
    assert first["controls"][0]["status"] == "available"
    assert first["coverage"]["nativeCommandCount"] == 2
    result = controls(capability, {"edit_project"}, "biblioteca")
    assert result["controls"][0]["binding"]["command"] == "asset.import"
    assert result["controls"][0]["status"] == "available"
    assert controls(capability, set(), "frear")["controls"][0]["status"] == "blocked"

    full = controls(capability, {"run_motion_script", "edit_project"})
    second = controls(capability, {"run_motion_script", "edit_project"}, offset=full["nextOffset"])
    ids = [item["id"] for page in (full, second) for item in page["controls"]]
    assert len(set(ids)) == len(ids) == full["coverage"]["mapped"]
    assert second["nextOffset"] is None
