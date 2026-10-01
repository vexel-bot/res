"""A complete critique must also be bound to actual decoded animatic evidence."""

import hashlib
import json


def _visual_direction_fingerprint(direction):
    """Compare executable visual choices, ignoring prose and arbitrary IDs.

    Z-order is represented by the actual relative stack, so changing a
    background from z=0 to z=1 below every other layer is not a visual edit.
    This is a pre-render economy check; the exported pixels remain decisive.
    """
    projected = {
        "artDirection": direction.get("artDirection"),
        "frameRate": direction.get("frameRate"),
        "scenes": [],
    }
    for scene in direction.get("scenes", []):
        elements = scene.get("elements", [])
        stack = {
            element.get("id"): position
            for position, (_, element) in enumerate(
                sorted(enumerate(elements), key=lambda item: (item[1].get("zIndex", 0), item[0]))
            )
        }
        visual_elements = []
        for element in elements:
            visual_elements.append({
                key: value
                for key, value in element.items()
                if key not in {
                    "purpose", "contentIdentity", "contentReferenceId", "contentPartId",
                    "zIndex", "schemaVersion",
                }
            } | {"stackPosition": stack.get(element.get("id"))})
        projected["scenes"].append({
            key: value
            for key, value in scene.items()
            if key in {
                "id", "durationFrames", "background", "entrance", "transitionFrames",
                "cameraCues", "keywordCues", "audio", "compositions",
            }
        } | {"elements": visual_elements})

    def normalized(value):
        if isinstance(value, dict):
            return {key: normalized(item) for key, item in sorted(value.items())}
        if isinstance(value, list):
            return [normalized(item) for item in value]
        if isinstance(value, float):
            return round(value, 3)
        return value

    return hashlib.sha256(
        json.dumps(normalized(projected), sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()


def visual_correction_effect(previous, candidate, action):
    """Reject a paid correction that weakens its proof or changes no pixels."""
    if action:
        previous_assertions = {
            assertion["id"]: assertion
            for scene in previous.get("scenes", [])
            for assertion in scene.get("semanticAssertions", [])
            if assertion.get("essential", True)
        }
        current_assertions = {
            assertion["id"]: assertion
            for scene in candidate.get("scenes", [])
            for assertion in scene.get("semanticAssertions", [])
        }
        for assertion_id, original in previous_assertions.items():
            current = current_assertions.get(assertion_id)
            if (
                not current
                or not current.get("essential", True)
                or current.get("kind") != original.get("kind")
                or current.get("objectId") != original.get("objectId")
                or set(current.get("targetIds", [])) != set(original.get("targetIds", []))
                or not set(original.get("requiredPartIds", [])) <= set(current.get("requiredPartIds", []))
                or current.get("evidenceRequired") != original.get("evidenceRequired")
            ):
                return {"status": "rejected", "reason": "production_visual_correction_weakened_verification", "assertionId": assertion_id}
    if _visual_direction_fingerprint(previous) == _visual_direction_fingerprint(candidate):
        return {"status": "rejected", "reason": "production_visual_correction_no_render_delta"}
    return {"status": "accepted", "reason": "executable_visual_change_present"}


def blocking_visual_findings(audit):
    if not isinstance(audit, dict):
        return []
    findings = [
        finding
        for finding in audit.get("findings", [])
        if finding.get("severity") in {"correction", "blocker"}
    ]
    semantic = audit.get("semanticVerification", {})
    if semantic.get("required") is True and semantic.get("status") != "passed":
        failed = next(
            (item for item in semantic.get("evidence", []) if item.get("status") == "failed"),
            None,
        )
        findings.append(
            {
                "sceneId": (failed or {}).get("sceneId"),
                "code": (
                    "audible_event_missing"
                    if (failed or {}).get("kind") == "audible_event"
                    else "canonical_content_incomplete"
                    if (failed or {}).get("kind")
                    in {"content_present", "content_continuity", "format_adaptation"}
                    else "semantic_action_failed"
                    if failed
                    else "inspection_coverage_incomplete"
                ),
                "severity": "correction",
                "evidence": failed or semantic,
                "correction": (failed or {}).get("reason")
                or "Inspect the complete assertion interval before progressing.",
            }
        )
    return findings


CORRECTION_ACTIONS = {
    "text_overflow": "recompile_composition",
    "concurrent_text_collision": "recompile_composition",
    "duplicate_concurrent_text": "recompile_composition",
    "format_viewport_ratio_mismatch": "recompile_composition",
    "format_content_identity_lost": "select_route",
    "declared_contrast_below_reference": "recompile_composition",
    "material_irrelevant": "resolve_material",
    "material_insufficient": "resolve_material",
    "action_not_observed": "select_route",
    "representation_generic": "select_route",
    "visual_idea_inadequate": "replan_scene",
    "inspection_coverage_incomplete": "inspect_interval",
    "semantic_action_failed": "select_route",
    "canonical_content_incomplete": "recompile_composition",
    "audible_event_missing": "resolve_material",
}


def correction_action(finding):
    code = str(finding.get("code") or "")
    if code in CORRECTION_ACTIONS:
        return CORRECTION_ACTIONS[code]
    if any(token in code for token in ("material", "asset", "footage")):
        return "resolve_material"
    if any(token in code for token in ("coverage", "unobserved", "evidence_missing")):
        return "inspect_interval"
    if any(token in code for token in ("technique", "action", "demonstration")):
        return "select_route"
    return "recompile_composition"


def observed_result_gate(audit, render_checksum=None):
    """Translate immutable render evidence into the fourth production gate."""
    if not isinstance(audit, dict) or audit.get("status") == "unavailable":
        return {
            "status": "inconclusive",
            "evidence": [],
            "reason": "Rendered visual evidence is unavailable.",
            "nextAction": "inspect_interval",
        }
    binding_ok = bool(render_checksum and audit.get("renderChecksum") == render_checksum)
    coverage = audit.get("coverage", {})
    action = audit.get("actionVerification", {})
    semantic = audit.get("semanticVerification", {})
    findings = [
        finding
        for finding in audit.get("findings", [])
        if finding.get("severity") in {"correction", "blocker"}
    ]
    if findings:
        return {
            "status": "failed",
            "evidence": findings,
            "reason": "The rendered candidate contains a blocking visual finding.",
            "nextAction": correction_action(findings[0]),
        }
    if semantic.get("required") is True and semantic.get("status") == "failed":
        evidence = semantic.get("evidence") or []
        first = next((item for item in evidence if item.get("status") == "failed"), {})
        next_action = (
            "resolve_material"
            if first.get("kind") == "audible_event"
            else "recompile_composition"
            if first.get("kind") in {"content_present", "content_continuity", "format_adaptation"}
            else "select_route"
        )
        return {
            "status": "failed",
            "evidence": evidence,
            "reason": first.get("reason") or "An essential semantic assertion is contradicted by the render.",
            "nextAction": next_action,
        }
    if semantic.get("required") is True and semantic.get("status") != "passed":
        return {
            "status": "inconclusive",
            "evidence": semantic.get("evidence") or [],
            "reason": "The semantic action lacks complete checksum-bound evidence.",
            "nextAction": "inspect_interval",
        }
    semantic_ok = semantic.get("required") is not True or semantic.get("status") == "passed"
    complete_observation = (
        binding_ok
        and audit.get("renderedEvidence")
        and coverage.get("frameSampleComplete") is True
        and action.get("status") == "observed"
        and action.get("evidence")
        and semantic_ok
        and (semantic.get("evidence") or not semantic.get("required"))
    )
    if complete_observation:
        return {
            "status": "passed",
            "evidence": [*action.get("evidence", []), *semantic.get("evidence", [])],
            "reason": "The bound render executes the operations and proves every essential semantic assertion.",
            "nextAction": None,
        }
    return {
        "status": "inconclusive",
        "evidence": audit.get("renderedEvidence") or [],
        "reason": "Execution evidence alone does not prove the requested visual meaning.",
        "nextAction": "inspect_interval",
    }


def prepare_visual_correction(state, audit):
    """Schedule a bounded, scene-local re-plan from executable visual evidence."""
    findings = blocking_visual_findings(audit)
    if not findings:
        return False
    rounds = state.get("correctionRounds", 0)
    if rounds >= 2:
        state.update(
            status="awaiting_review",
            blockers=["production_visual_correction_limit_reached"],
            visualAudit=audit,
        )
        return True
    plan = state.get("artifacts", {}).get("plan", {})
    direction = plan.get("direction")
    if not direction:
        state.update(status="blocked", blockers=["production_visual_plan_missing"], visualAudit=audit)
        return True
    actions = [correction_action(finding) for finding in findings]
    if "inspect_interval" in actions:
        state.update(
            status="awaiting_review",
            blockers=["production_complementary_inspection_required"],
            visualAudit=audit,
            correctionAction="inspect_interval",
        )
        return True
    instructions = []
    scene_ids = []
    for finding in findings:
        scene_id = finding.get("sceneId")
        if scene_id:
            scene_ids.append(scene_id)
        action = correction_action(finding)
        instructions.append(
            f"{scene_id or 'composition'} [{action}]: {finding.get('correction') or finding.get('code')}"
        )
    state["history"] = [
        *state.get("history", []),
        {
            "jobs": state.get("jobs", {}),
            "artifacts": state.get("artifacts", {}),
            "revision": state.get("revision"),
            "visualAudit": audit,
            "correctionActions": actions,
        },
    ]
    state["revisionRequest"] = {
        "original": direction,
        "sceneIds": list(dict.fromkeys(scene_ids)),
        "instruction": "\n".join(instructions)[:4000],
    }
    state["jobs"] = {
        key: value
        for key, value in state.get("jobs", {}).items()
        if key not in {"composition", "animatic", "render", "critique"}
    }
    state.update(
        stage="composition",
        status="pending",
        blockers=[],
        visualAudit=audit,
        correctionRounds=rounds + 1,
        correctionAction=(actions[0] if len(set(actions)) == 1 else "multiple"),
    )
    return True


def animatic_ready(state, critique):
    audit = state.get("visualAudit") or {}
    artifact = (state.get("artifacts", {}).get("animatic") or {}).get("artifact", {})
    return bool(
        artifact.get("checksumSha256")
        and audit.get("renderChecksum") == artifact["checksumSha256"]
        and audit.get("renderedEvidence")
        and audit.get("coverage", {}).get("frameSampleComplete") is True
        and audit.get("actionVerification", {}).get("status") == "observed"
        and audit.get("actionVerification", {}).get("evidence")
        and (
            audit.get("semanticVerification", {}).get("required") is not True
            or (
                audit.get("semanticVerification", {}).get("status") == "passed"
                and audit.get("semanticVerification", {}).get("evidence")
            )
        )
        and not blocking_visual_findings(audit)
        and critique.get("coverage") == "full"
        and not any(f["severity"] in {"correction", "blocker"} for f in critique.get("findings", []))
    )
