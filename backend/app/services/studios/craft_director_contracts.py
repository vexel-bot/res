"""Discoverable director tool formats and session-local optimistic write chaining."""
import copy
from datetime import UTC, datetime
from uuid import uuid4

from ...domain.studios.craft_direction_v2 import Comparison, DirectionPlan, Interval

READ_TOOLS = {"inspect_direction", "inspect_cycle_history", "inspect_production_capabilities"}


def payload_schema(name):
    if name == "record_direction_plan":
        plan = DirectionPlan.model_json_schema(by_alias=True)
        definitions = plan.pop("$defs", {})
        return {"type": "object", "properties": {"plan": plan}, "required": ["plan"],
                "additionalProperties": False}, definitions
    if name == "compare_direction_candidates":
        schema = Comparison.model_json_schema(by_alias=True)
        return schema, schema.pop("$defs", {})
    interval = Interval.model_json_schema(by_alias=True)
    fields = {
        "record_cycle_progress": {"stage": {"enum": ["diagnosis", "experiment", "production", "comparison", "delivered"]},
            "summary": {"type": "string", "minLength": 1}, "toolUseIds": {"type": "array", "items": {"type": "string"}, "minItems": 1}},
        "save_direction_candidate": {"reviewAssetId": {"type": "string"}, "label": {"type": "string"}},
        "manage_direction_issue": {"id": {"type": "string"}, "description": {"type": "string"}, "interval": interval,
            "scope": {"enum": ["document", "family"], "description": "Default document. Source-document defects remain historical context; family explicitly applies across branches."},
            "status": {"enum": ["open", "resolved", "refuted", "limitation"]},
            "evidenceIds": {"type": "array", "items": {"type": "string"}}, "rationale": {"type": "string"}},
        "record_revision_hypothesis": {"problem": {"type": "string"}, "change": {"type": "string"},
            "expectedGain": {"type": "string"}, "possibleLosses": {}},
        "request_direction_evaluation": {"operationId": {"type": "string"}, "providerId": {"type": "string"},
            "reviewAssetId": {"type": "string"}, "modality": {"enum": ["visual", "audio", "audiovisual"]},
            "interval": interval, "timeOrigin": {"enum": ["composition", "clip"],
                "description": "Default composition: absolute timeline seconds. Clip: seconds relative to review clip start."},
            "operationKey": {"type": "string"}, "parameters": {"type": "object", "properties": {
                "fps": {"type": "number", "exclusiveMinimum": 0, "maximum": 60},
                "maximumSide": {"type": "integer", "minimum": 256, "maximum": 2048}}},
            "sampling": {"type": "object"}, "questions": {"type": "array", "items": {"type": "string"}},
            "baselineReviewAssetId": {"type": "string"}, "baselineInterval": interval,
            "rationale": {"type": "string"}, "cost": {}},
    }.get(name)
    required = {"record_cycle_progress": ["stage", "summary", "toolUseIds"],
                "save_direction_candidate": ["reviewAssetId"],
                "record_revision_hypothesis": ["problem", "change", "expectedGain"]}.get(name, [])
    return ({"type": "object", "properties": fields, "required": required, "additionalProperties": False}
            if fields is not None else {"type": "object"}), {}


def tool_schema(name):
    payload, definitions = payload_schema(name)
    schema = {"type": "object", "properties": {"expectedVersion": {"type": "integer", "minimum": 0},
        "payload": payload}, "required": ["payload"] + ([] if name in READ_TOOLS else ["expectedVersion"]),
        "additionalProperties": False}
    if definitions:
        schema["$defs"] = definitions
    return schema


class DirectorWriteChain:
    """Forward only revisions produced by successful writes in this assistant tool batch.

    The database still compares the forwarded revision. A concurrent external write
    therefore fails normally; a larger-than-owned version jump never extends this chain.
    """
    def __init__(self):
        self.clear()

    def clear(self):
        self.known = set()
        self.latest = None

    def arguments(self, name, args):
        if name in READ_TOOLS or args.get("expectedVersion") not in self.known:
            return args
        return {**args, "expectedVersion": self.latest}

    def observe(self, name, submitted, effective, reply):
        if name in READ_TOOLS:
            return
        used = effective.get("expectedVersion")
        delta = 2 if name in {"request_direction_evaluation", "request_direction_material"} else 1
        if (effective.get("payload", {}).get("operationId") or type(used) is not int
                or reply.get("version") != used + delta):
            self.clear()
            return
        if self.latest != used:
            self.known.clear()
        self.known.update((submitted["expectedVersion"], used, reply["version"]))
        self.latest = reply["version"]


def compact_cycle(cycle):
    """Keep decisions once and retrieve the full event trail on demand."""
    value = copy.deepcopy({k: v for k, v in cycle.items() if k not in {"processHistory", "events"}})
    value["eventCount"] = len(cycle.get("events", []))
    value["recentEvents"] = [{k: e[k] for k in ("id", "stage", "binding") if k in e}
                            for e in cycle.get("events", [])[-4:]]
    value["latestDecision"] = cycle.get("events", [{}])[-1].get("summary") if cycle.get("events") else None
    value["historyAvailableVia"] = {"kind": "cycle"}
    return value


def record_finish_issues(state, binding, descriptions, identifiers=None):
    """Reference existing issues explicitly; never close or merge by fuzzy similarity."""
    known = {i["id"]: i for i in state["issues"]}
    identifiers = [] if identifiers is None else identifiers
    if (not isinstance(identifiers, list) or any(not isinstance(i, str) or i not in known for i in identifiers)):
        raise ValueError("craft_finish_issue_reference_invalid")
    changed = False
    for description in descriptions:
        if any(i["description"] == str(description) for i in state["issues"]):
            continue
        state["issues"].append({"id": str(uuid4()), "description": str(description), "status": "open",
            "binding": binding, "origin": "finish_project", "history": [],
            "createdAt": datetime.now(UTC).isoformat()})
        changed = True
    return changed


def reconcile_native_commit(review_binding, document_id, revision, native_sha256):
    return {"reviewBinding": copy.deepcopy(review_binding), "committedDocumentId": document_id,
            "committedRevision": revision, "committedNativeChecksumSha256": native_sha256,
            "sameNativeContent": bool(review_binding and review_binding.get("documentId") == document_id
                and review_binding.get("nativeChecksumSha256") == native_sha256),
            "meaning": "Commit provenance only. Does not rewrite evidence or promote any quality assessment."}
