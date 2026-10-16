"""Bounded discovery compiler derived from a real Alight text project.

This is not an admitted production compiler or a driver. Its output must be
reimported and rendered in the pinned app before qualification can be granted.
"""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ...domain.studios.contextual_editing import digest

APP_VERSION = "5.0.273.1028425"
COMPILER_VERSION = "res.alight-text-discovery.v1"
REFERENCE_SHA256 = "730152f4f7188a1656b5121b675e0fe223bd5accfd6f8c94ac3d4935c833aadf"
REFERENCE = (
    Path(__file__).resolve().parents[4] / "workers/alight-motion/references" / APP_VERSION / "text-linear-motion.xml"
)


class TextReferenceParameters(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)
    schema_version: Literal["studio.alight-text-discovery.v1"] = "studio.alight-text-discovery.v1"
    scene_id: str = Field(min_length=1, max_length=120)
    element_id: str = Field(min_length=1, max_length=120)
    title: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=120)
    duration_ms: int = Field(ge=100, le=15000)
    entry_ms: int = Field(ge=100, le=14000)

    @model_validator(mode="after")
    def bounded(self):
        # Keep the observed keyframe-centre offset. Its timing interpretation
        # remains an inference until a generated variant has been re-exported.
        if self.entry_ms + 16 >= self.duration_ms:
            raise ValueError("alight_entry_outside_layer")
        for value in (self.title, self.text, self.scene_id, self.element_id):
            if any(
                ord(char) not in (9, 10, 13)
                and not (
                    0x20 <= ord(char) <= 0xD7FF or 0xE000 <= ord(char) <= 0xFFFD or 0x10000 <= ord(char) <= 0x10FFFF
                )
                for char in value
            ):
                raise ValueError("alight_xml_character_invalid")
        return self


def compile_text_reference(parameters: TextReferenceParameters, *, reference_path: Path = REFERENCE):
    """Only title, content and timing change; never accept planner-supplied XML."""
    parameters = TextReferenceParameters.model_validate(parameters.model_dump())
    source = reference_path.read_bytes()
    if hashlib.sha256(source).hexdigest() != REFERENCE_SHA256:
        raise ValueError("alight_reference_checksum_conflict")
    root = ET.fromstring(source)
    layer = root.find("text")
    location = root.find("text/transform/location")
    if layer is None or location is None or len(location) != 2:
        raise ValueError("alight_reference_shape_conflict")
    root.set("title", parameters.title)
    root.set("totalTime", str(parameters.duration_ms))
    # Avoid passing stale device timestamps off as a new native export.
    root.attrib.pop("modifiedTime", None)
    layer.set("endTime", str(parameters.duration_ms))
    layer.find("content").text = parameters.text
    location[0].set("t", f"{16 / parameters.duration_ms:.6f}")
    location[1].set("t", f"{(parameters.entry_ms + 16) / parameters.duration_ms:.6f}")
    output = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    values = parameters.model_dump(mode="json")
    receipt = {
        "kind": "alight.discovery_compilation.v1",
        "compilerVersion": COMPILER_VERSION,
        "appVersion": APP_VERSION,
        "referenceSha256": REFERENCE_SHA256,
        "parameters": values,
        "parameterDigest": digest(values),
        "outputSha256": hashlib.sha256(output).hexdigest(),
        "bindings": {
            "sceneId": parameters.scene_id,
            "elementId": parameters.element_id,
            "nativeTextId": layer.get("id"),
        },
        "outputSpec": {"width": 540, "height": 960, "fps": 30, "durationMs": parameters.duration_ms},
        "plannedGeometry": {"xStart": -270, "xEnd": 270, "y": 480},
        "observedGeometry": None,
        "timingInterpretation": "inferred from observed 16ms keyframe-centre offset; verify generated variant",
        "renderQualification": False,
        "workerJob": None,
        "pendingCapabilities": [
            "generated_variant_import",
            "generated_variant_render",
            "automatic_driver",
            "media_bindings",
            "masks",
            "fonts",
            "1080p",
        ],
    }
    return output, receipt
