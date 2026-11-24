"""Discover Clicko controls and their corresponding EffectCraft agent operations."""

import json
from pathlib import Path

from .craft import editable_commands
from .craft_discovery import rank


CATALOG = Path(__file__).with_name("craft_effectcraft_controls.v1.json")
PAGE_SIZE = 16


def controls(capability, tools, query="", offset=0):
    if type(offset) is not int or offset < 0:
        raise ValueError("craft_capability_offset_invalid")
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    commands = [item for item in editable_commands(capability) if not item["id"].startswith("host.")]
    active_commands = {item["id"] for item in commands}
    items = []
    for control in data["controls"]:
        entry = dict(control)
        binding = entry.get("binding", {})
        if "command" in binding:
            exposed = binding["command"] in active_commands and "edit_project" in tools
        else:
            exposed = binding.get("tool") in tools
            if binding.get("tool") == "run_motion_script":
                exposed = exposed and "script.run" in active_commands
        if exposed:
            entry["status"] = "available"
        elif binding or entry.get("missingAgentOperation"):
            entry["status"] = "blocked"
        else:
            entry["status"] = "interface_only"
        items.append(entry)

    matches = rank(items, query)
    native = rank(commands, query)
    return {
        "buildId": capability.get("buildId"),
        "controls": matches[offset:offset + PAGE_SIZE],
        "nativeCommands": [{"id": item["id"], "label": item.get("label", item["id"]),
                            "required": item.get("inputSchema", {}).get("required", [])}
                           for item in native[offset:offset + PAGE_SIZE]],
        "coverage": {"mapped": len(items), "available": sum(item["status"] == "available" for item in items),
                     "blocked": sum(item["status"] == "blocked" for item in items),
                     "interfaceOnly": sum(item["status"] == "interface_only" for item in items),
                     "nativeCommandCount": len(commands), "executionEvidence": "separate"},
        "totalMatches": len(matches), "totalCommandMatches": len(native),
        "nextOffset": offset + PAGE_SIZE if offset + PAGE_SIZE < max(len(matches), len(native)) else None,
        "guidance": "For command schemas use describe_commands. For scripted properties use "
                    "inspect_editor_capabilities, then probe_motion_script and verify_motion_execution. "
                    "Availability describes the current session. Qualify behavior by executing, reopening and reviewing.",
    }


def command_guidance(command_id):
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    return data["commandGuidance"].get(command_id)
