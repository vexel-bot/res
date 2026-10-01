"""Allowlisted local generation profiles; never accepts model identifiers from an LLM."""

from __future__ import annotations

import copy
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROFILES = ROOT / "profiles"
LEGACY_PROFILE = "wan21-t2v-local-experimental-v1"


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _merge(parent: dict, child: dict) -> dict:
    result = copy.deepcopy(parent)
    result.update({key: value for key, value in child.items() if key != "inherits"})
    return result


def _raw_profiles() -> dict[str, dict]:
    profiles = {LEGACY_PROFILE: _load_json(ROOT / "model-manifest.json")}
    for path in sorted(PROFILES.glob("*.json")):
        data = _load_json(path)
        profiles[data["profileId"]] = data
    return profiles


def profiles() -> dict[str, dict]:
    raw = _raw_profiles()
    resolved: dict[str, dict] = {}

    def resolve(profile_id: str, stack: tuple[str, ...] = ()) -> dict:
        if profile_id in resolved:
            return resolved[profile_id]
        if profile_id in stack:
            raise ValueError("local_diffusion_profile_cycle")
        data = raw.get(profile_id)
        if data is None:
            raise ValueError("local_diffusion_profile_unavailable")
        parent_id = data.get("inherits")
        value = _merge(resolve(parent_id, (*stack, profile_id)), data) if parent_id else copy.deepcopy(data)
        if value.get("operation") != "text_to_video":
            raise ValueError("local_diffusion_operation_unavailable")
        resolved[profile_id] = value
        return value

    for key in raw:
        resolve(key)
    return resolved


def get_profile(profile_id: str | None = None) -> dict:
    return profiles().get(profile_id or LEGACY_PROFILE) or (_ for _ in ()).throw(
        ValueError("local_diffusion_profile_unavailable")
    )


def list_profiles() -> list[dict]:
    return [profiles()[key] for key in sorted(profiles())]
