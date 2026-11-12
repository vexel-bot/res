"""Describe this build's native contract without implying Adobe binary parity."""

from ...providers.studios.craft import REPOSITORY_ROOT


def scripting_reference(engine, capability, query="", offset=0):
    if type(offset) is not int or offset < 0:
        raise ValueError("craft_capability_offset_invalid")
    commands = capability.get("commands", [])
    terms = query.casefold().split()
    matching = [command for command in commands if all(term in str(command).casefold() for term in terms)]
    parity = REPOSITORY_ROOT / "third_party" / "craft" / engine / "docs" / "scripting-parity.md"
    notes = []
    if parity.is_file():
        notes = [line for line in parity.read_text(encoding="utf-8").splitlines()
                 if line.startswith("| ") and (not terms or all(term in line.casefold() for term in terms))]
    return {
        "engine": engine, "buildId": capability.get("buildId"),
        "implementation": "Independent clean-room Craft implementation with its own native command contract.",
        "nativeCommands": matching[offset:offset + 24],
        "documentedCompatibility": notes[offset:offset + 24],
        "totalCommands": len(matching),
        "totalCompatibilityNotes": len(notes),
        "nextOffset": offset + 24 if offset + 24 < max(len(matching), len(notes)) else None,
        "verification": "The command schemas describe this build. Upstream parity notes are declarations, not a test of your script.",
        "editingGuidance": [
            "Discover the exact command schema and inspect native properties before using an unfamiliar operation.",
            "For a keyed property use setValueAtTime or setValueAtKey. setValue rejects a property that has keyframes.",
            "JSX names alone do not establish behaviour. Check the render and retain any native error for correction.",
        ],
    }
