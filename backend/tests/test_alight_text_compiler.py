import xml.etree.ElementTree as ET

import pytest
from pydantic import ValidationError

from app.providers.studios.alight_text_compiler import REFERENCE, TextReferenceParameters, compile_text_reference


def params(**changes):
    return TextReferenceParameters(
        scene_id="scene-1",
        element_id="title-1",
        title="res — variante",
        text="Criar • mover & <testar>",
        duration_ms=15000,
        entry_ms=2000,
        **changes,
    )


def test_reference_mutation_blocks_compilation(tmp_path):
    changed = tmp_path / "changed.xml"
    changed.write_bytes(REFERENCE.read_bytes() + b" ")
    with pytest.raises(ValueError, match="checksum_conflict"):
        compile_text_reference(params(), reference_path=changed)


def test_parameters_are_data_and_preserve_observed_layer_structure():
    output, receipt = compile_text_reference(params())
    root = ET.fromstring(output)
    assert root.find("text/content").text == "Criar • mover & <testar>"
    assert len(root.findall("text")) == 1
    assert root.get("totalTime") == root.find("text").get("endTime") == "15000"
    assert root.get("width") == "540" and root.get("height") == "960"
    assert root.find("text").get("font") == "googlefonts?name=Roboto&weight=400"
    times = [float(k.get("t")) for k in root.findall("text/transform/location/kf")]
    assert 0 < times[0] < times[1] < 1
    assert receipt["renderQualification"] is False
    assert receipt["workerJob"] is None
    assert receipt["observedGeometry"] is None


def test_changed_parameters_change_output_and_receipt_digest():
    original = params()
    first, a = compile_text_reference(original)
    second, b = compile_text_reference(original.model_copy(update={"text": "Outra mensagem"}))
    assert first != second
    assert a["parameterDigest"] != b["parameterDigest"]
    assert a["outputSha256"] != b["outputSha256"]


@pytest.mark.parametrize("extra", [{"xml": "<scene/>"}, {"command": "adb shell"}, {"curve": [0.2, 0, 0.2, 1]}])
def test_unimplemented_features_are_rejected(extra):
    with pytest.raises(ValidationError):
        params(**extra)


def test_entry_cannot_exceed_layer_or_contain_invalid_xml_characters():
    with pytest.raises(ValidationError, match="outside_layer"):
        TextReferenceParameters(scene_id="s", element_id="e", title="t", text="t", duration_ms=1000, entry_ms=1000)
    with pytest.raises(ValidationError, match="character_invalid"):
        TextReferenceParameters(
            scene_id="s", element_id="e", title="t", text="bad\x00", duration_ms=15000, entry_ms=2000
        )
