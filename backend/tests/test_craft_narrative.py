import json
import os
import shutil
import time
import wave
from pathlib import Path
from types import SimpleNamespace

import pytest

from app.providers.studios.craft import require_capability
from app.services.studios import craft_direction, craft_narrative
from app.services.studios.craft_agent import Draft, NARRATIVE
from app.services.studios.craft_review import review_draft


@pytest.mark.parametrize(("profile", "engine", "instruction", "expected"), [
    ("auto", "effectcraft", "Crie um motion com uma história sobre startups.", True),
    ("auto", "effectcraft", "Ajuste apenas o volume.", False),
    ("general", "effectcraft", "Motion com história", False),
    ("narrative_motion", "effectcraft", "Crie a peça", True),
    ("narrative_motion", "filmcraft", "Crie a peça", False),
])
def test_editorial_profile(profile, engine, instruction, expected):
    assert craft_narrative.enabled(profile, engine, instruction) is expected


def test_repertoire_returns_specific_editorial_passages(monkeypatch):
    from app.services.studios import editing_repertoire

    monkeypatch.setattr(editing_repertoire, "search_repertoire", lambda *_: [])
    monkeypatch.setattr(editing_repertoire, "available_repertoire", lambda *_: [])
    result = craft_direction.search_repertoire(None, None, "revelação cedo demais", limit=4)
    assert {card["id"] for card in result["matches"]} >= {"story.sol-turn", "story.velotile-word"}
    sol = craft_direction.references(["story.sol-turn"])["story.sol-turn"]
    assert sol["source"]["startSeconds"] == 39
    assert sol["source"]["temporalAvailable"] is False


def test_optional_story_tool_schema_and_versioning():
    assert "$ref" not in json.dumps(NARRATIVE[0])
    db = SimpleNamespace(commit=lambda: None)
    job = SimpleNamespace(result_payload={})
    args = {"openings": [{"premise": "Three lights", "viewerQuestion": "Where is the fourth?"},
                         {"premise": "An offer", "viewerQuestion": "Will anyone buy?"}],
            "selectedOpening": 1, "choice": "Begin with evidence.",
            "beats": [{"atSeconds": 2, "initialState": "Three lights", "event": "Grid appears",
                       "inference": "Only three bought"}], "payoff": "Recover the grid at the end."}
    assert craft_narrative.record_story(db, job, args)["version"] == 1
    assert craft_narrative.record_story(db, job, args)["version"] == 1
    assert craft_narrative.record_story(db, job, {**args, "selectedOpening": 2})["version"] == 2


def test_sound_library_requires_verified_workspace_audio():
    audio = SimpleNamespace(workspace_id="workspace-a", lifecycle_status="active", media_type="audio/wav",
                            storage_key="file.wav", checksum_sha256="hash", object_metadata={})
    assert not craft_narrative.audio_source(audio, "workspace-a")
    audio.object_metadata = {"editingResource": {"usageEvidence": "Original FX"}}
    assert craft_narrative.audio_source(audio, "workspace-a")
    assert not craft_narrative.audio_source(audio, "workspace-b")
    audio.object_metadata["rightsStatus"] = "restricted"
    assert not craft_narrative.audio_source(audio, "workspace-a")


def test_audio_layer_selection_uses_exact_ids():
    assert "keep=[12, 40]" in craft_narrative.audio_isolation_script([12, 40])
    with pytest.raises(ValueError, match="craft_audio_layer_ids_invalid"):
        craft_narrative.audio_isolation_script([12, 12])


@pytest.mark.skipif(not os.environ.get("CLICKO_NARRATIVE_NATIVE_PROOF"), reason="Requires local EffectCraft")
def test_effectcraft_compares_and_applies_the_exact_variant_and_isolates_audio(tmp_path):
    source = Path(os.environ["CLICKO_NARRATIVE_NATIVE_PROOF"])
    native = tmp_path / "source.ecproj"
    shutil.copyfile(source, native)
    for name in ("voice", "bed"):
        with wave.open(str(tmp_path / (name + ".wav")), "wb") as wav:
            wav.setparams((1, 2, 48000, 0, "NONE", "not compressed"))
            wav.writeframes(b"\x00\x10" * 48000)
    draft = Draft(SimpleNamespace(engine="effectcraft", migration_warnings=[]), tmp_path,
                  {"nativePath": str(native), "mediaRoot": str(tmp_path), "media": []},
                  require_capability("effectcraft"), SimpleNamespace(expected_revision=1), time.monotonic() + 240)
    draft.run("run_motion_script", {"code": """
var c=app.project.activeItem;while(c.numLayers)c.layer(1).remove();
c.duration=1;c.frameRate=30;c.width=64;c.height=64;
function add(name){
  var l=c.layers.add(app.project.importFile(new ImportOptions(new File('/job/'+name+'.wav'))));
  l.name=name;
}
add('bed');add('voice');
"""})
    review = {"startSeconds": 0, "durationSeconds": 1, "sampling": "overview", "pageSize": 2}
    working_native = draft.params["nativePath"]
    voice = next(layer for layer in draft.project["layers"] if layer["name"] == "voice")
    voice_id = int(voice["id"])
    mix = review_draft(draft, review)
    script = craft_narrative.audio_isolation_script([voice_id])
    isolated = draft.preview_candidate({**review, "code": script}, isolate=True)
    assert json.loads(isolated[0]["text"])["scope"] == "isolated_audio_review"
    solo_peak = json.loads(isolated[1]["text"])["audio"]["peakDbfs"]
    assert mix["report"]["audio"]["peakDbfs"] > solo_peak + 4
    base = draft.batches
    candidates = [
        json.loads(draft.run("preview_motion_variant", {**review, "code": "app.project.activeItem.layer(1).name='" + label + "'"})[0]["text"])
        for label in ("Hold then reveal", "Reveal early")
    ]
    assert all(candidate["baseBatch"] == base for candidate in candidates)
    assert draft.params["nativePath"] == working_native
    applied = draft.run("apply_motion_variant", {"variantId": candidates[0]["variantId"]})
    assert applied["draftBatch"] == base + 1
    assert any(layer["name"] == "Hold then reveal" for layer in draft.call("project.open")["inspection"]["layers"])
    with pytest.raises(ValueError, match="craft_variant_missing_or_base_changed"):
        draft.run("apply_motion_variant", {"variantId": candidates[1]["variantId"]})

def test_first_view_direction_reaches_both_editors(monkeypatch):
    from app.services.studios.motion_brief import motion_brief

    monkeypatch.setattr(craft_narrative.craft_references, "reference_index", lambda _: [])
    monkeypatch.setattr(craft_direction, "reference_index", lambda: [])
    direction = craft_narrative.context("workspace")["firstViewDirection"]
    assert "construir, medir, aprender" in direction
    assert motion_brief("Briefing original").startswith("Briefing original\n\n")
    assert motion_brief("Briefing original").endswith(direction)
    assert craft_narrative.enabled("auto", "effectcraft", "Motion sobre startups")


def test_first_view_review_requires_ordered_evidence():
    data = dict(subjectInPlainWords="Descobrir qual oferta repetir",
                evidenceOnScreen="Duas ofertas com o mesmo prazo e preços diferentes",
                evidenceReadableAt=12, comparisonEndsAt=14,
                likelyMisreading="Achar que o desconto explicou todo o aumento",
                editorialDecision="Segurar o par de ofertas até a decisão", source="editorial_review")
    assert craft_narrative.FirstViewReview.model_validate(data).comparison_ends_at == 14
    with pytest.raises(ValueError, match="before"):
        craft_narrative.FirstViewReview.model_validate({**data, "comparisonEndsAt": 11})
