"""Describe this build's native contract without implying Adobe binary parity."""

from ...providers.studios.craft import REPOSITORY_ROOT
from .craft_discovery import rank


def scripting_reference(engine, capability, query="", offset=0):
    if type(offset) is not int or offset < 0:
        raise ValueError("craft_capability_offset_invalid")
    commands = capability.get("commands", [])
    matching = rank(commands, query)
    parity = REPOSITORY_ROOT / "third_party" / "craft" / engine / "docs" / "scripting-parity.md"
    notes = []
    if parity.is_file():
        notes = rank([line for line in parity.read_text(encoding="utf-8").splitlines()
                      if line.startswith("| ")], query)
    return {
        "engine": engine, "buildId": capability.get("buildId"),
        "implementation": "Independent clean-room Craft implementation with its own native command contract.",
        "nativeCommands": [{"id": command["id"], "label": command.get("label", command["id"]),
                            "required": command.get("inputSchema", {}).get("required", []),
                            "details": "Use describe_commands with this id for the full input schema."}
                           for command in matching[offset:offset + 24]],
        "documentedCompatibility": notes[offset:offset + 24],
        "totalCommands": len(matching),
        "totalCompatibilityNotes": len(notes),
        "searchStatus": "matches" if matching or notes else "no_matches",
        "suggestedCategories": [] if matching or notes else ["camera", "light", "text", "audio", "motion", "script"],
        "evidenceStatus": "documented; execution must be verified on this build",
        "nextOffset": offset + 24 if offset + 24 < max(len(matching), len(notes)) else None,
        "verification": "The command schemas describe this build. Upstream parity notes are declarations, not a test of your script.",
        "editingGuidance": [
            "For API experiments use probe_motion_script on a disposable copy. To verify persisted configuration use "
            "verify_motion_execution with exact inspected layer IDs/property UIDs, expected values or key metadata. "
            "A successful script is not proof of applied settings or visual quality. Report exceptions instead of empty catch blocks.",
            "Discover the exact command schema and inspect native properties before using an unfamiliar operation.",
            "Text position is the anchor position, not its visible top-left. After setting the actual text/font/size, "
            "read sourceRectAtTime(time,false). For a centered word set Anchor Point to "
            "[rect.left+rect.width/2,rect.top+rect.height/2,0] and Position to the desired center. "
            "Recompute after content/font changes and inspect the full word in the render; defaults can crop its first letters.",
            "EffectCraft supports spatial layer/camera/light operations through its native contract. "
            "Do not assume motion graphics means flat 2D. Discover and test the operations required by your chosen direction. "
            "A perspective-transformed flat layer is not a volumetric model or proof of physical CGI/materials.",
            "Find imported layers by their exact inspected names or native IDs. The asset ID and the timeline layer name may differ.",
            "Pass color channels as numeric arrays in scripts. Do not assume that JavaScript globals or legacy String methods from other runtimes are available.",
            "For a keyed property use setValueAtTime or setValueAtKey. setValue rejects a property that has keyframes.",
            "Key times are quantized to the composition frame grid. Inspect keyTime/keyValue, or use a frame-sized tolerance; a decimal like 8.25 s is not necessarily representable at 30 fps.",
            "Script setValueAtTime uses composition time; stored native key times can be layer-local after the layer start offset. "
            "Inspect the persisted times and account for that offset instead of shifting the same key twice.",
            "JSX names alone do not establish behaviour. Check the render and retain any native error for correction.",
            *(["To enable a dashed stroke, call addProperty('ADBE Vector Stroke Dashes') on the stroke "
               "or on Contents when it contains a single stroke. On the returned group, set Dash and Gap in "
               "pixels and animate Offset with setValueAtTime. With multiple strokes select the intended stroke.",
               "For gradients inside vector geometry, add ADBE Vector Graphic - G-Fill (or G-Stroke). "
               "Type=2 in scripts is radial; Start Point and End Point are layer-local coordinates. "
               "If Colors.setValue reports 'value must be a number', use the documented native prop.set "
               "command with the inspected layer ID, gradient Colors property UID and "
               "value={colors:[[0,[r,g,b,1]],[1,[r,g,b,1]]],opacities:[[0,1],[1,1]]}. "
               "Native prop.set accepts gradient objects independently of the script custom-value conversion.",
               "Gradient Ramp is a Generate effect and can replace the layer image/alpha with a rectangle. "
               "Do not assume it clips to a shape; inspect the render or use a vector gradient fill."]
              if engine == "effectcraft" else []),
        ],
    }
