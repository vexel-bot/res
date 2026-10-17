"""Evidence-bound material inspection, separate from human review."""

import re
import unicodedata
from typing import Literal

from pydantic import Field

from .contracts import StudioContract


class MaterialInspectionRequestV1(StudioContract):
    asset_id: str = Field(min_length=1, max_length=120)
    checksum: str = Field(pattern=r"^[a-f0-9]{64}$")
    purpose: str = Field(min_length=1, max_length=1000)
    criteria: list[str] = Field(min_length=1, max_length=30)
    required_seconds: float = Field(default=0, ge=0, le=120)
    source_start_seconds: float = Field(default=0, ge=0, le=86400)
    max_samples: int = Field(default=6, ge=6, le=18)
    evidence_kind: Literal["static_frames", "temporal_sequence"] = "static_frames"
    allowed_post_processing: list[Literal["remove_background", "convert_to_png", "trim", "chroma_key"]] = Field(
        default_factory=list, max_length=5
    )


class MaterialCriterionV1(StudioContract):
    index: int = Field(ge=0, le=29)
    result: Literal["supported", "contradicted", "unknown"]
    evidence: str = Field(min_length=1, max_length=1000)
    sample_indices: list[int] = Field(min_length=1, max_length=18)


class MaterialInspectionResultV1(StudioContract):
    description: str = Field(min_length=1, max_length=2000)
    criteria: list[MaterialCriterionV1] = Field(min_length=1, max_length=30)
    confidence: float | None = Field(default=None, ge=0, le=1)
    confidence_kind: Literal["calibrated", "model_reported", "uncalibrated_rule"] = "model_reported"
    evidence_kind: Literal["static_frames", "temporal_sequence"] = "static_frames"
    processing_requirements: list[Literal["chroma_key"]] = Field(default_factory=list, max_length=5)
    uncertainty: str = Field(min_length=1, max_length=1000)


def material_inspection_criteria(need) -> list[str]:
    """Bind inspection to what pixels must depict, not only to layout traits."""
    visual_identity = (
        getattr(need, "visual_description", "").strip()
        or getattr(need, "entity", "").strip()
        or getattr(need, "query", "").strip()
    )
    semantic = (
        "The pixels themselves must visibly and recognizably depict this requested subject: "
        f"{visual_identity}. Metadata, filename, a future overlay, path, animation or surrounding scene "
        "cannot satisfy this criterion."
    )
    acceptance = list(getattr(need, "acceptance_criteria", None) or [])

    def comparable(value: str) -> str:
        value = "".join(
            character
            for character in unicodedata.normalize("NFKD", value.casefold())
            if not unicodedata.combining(character)
        )
        return re.sub(r"[^a-z0-9]+", " ", value).strip()

    # The resolver can deliberately decompose a broad visual description into
    # independently observable mandatory facets.  In that case, asking a small
    # VLM to prove the concatenated sentence as an additional criterion adds no
    # evidence: it merely makes one long paraphrase able to veto all of the
    # concrete checks.  Keep the semantic identity guard whenever it contains
    # information beyond those facets.
    decomposed_identity = comparable(" ".join(acceptance))
    include_semantic = not acceptance or comparable(visual_identity) != decomposed_identity
    criteria = ([semantic] if include_semantic else []) + acceptance
    result = []
    for criterion in criteria:
        normalized = criterion.strip()
        if normalized and normalized not in result:
            result.append(normalized)
    return result[:30]


def inspect_verdict(result, request, samples, duration):
    if sorted(c.index for c in result.criteria) != list(range(len(request.criteria))):
        raise ValueError("material_inspection_criteria_coverage_invalid")
    if any(index < 0 or index >= len(samples) for c in result.criteria for index in c.sample_indices):
        raise ValueError("material_inspection_sample_binding_invalid")
    # Declaring a transform eligible is not evidence that it happened.  A
    # chroma plate remains an intermediate material until a checksum-bound
    # processing job produces and inspects the derived asset.
    if result.processing_requirements:
        return "requires_processing"
    calibrated = result.confidence_kind in {"calibrated", "model_reported"} and (result.confidence or 0) >= 0.9
    bounded_rule = result.confidence_kind == "uncalibrated_rule" and result.confidence is None
    evidence_matches = result.evidence_kind == request.evidence_kind
    return (
        "accepted"
        if (calibrated or bounded_rule)
        and evidence_matches
        and all(c.result == "supported" for c in result.criteria)
        and duration >= request.source_start_seconds + request.required_seconds
        else "requires_alternative"
    )
