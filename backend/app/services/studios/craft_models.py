"""Inspect embedded glTF 2 assets before making them available to a renderer."""

import json
import struct


def spatial_workflow(catalog, blender_build):
    operations = {
        "renderer": "comp.renderer", "primitive": "layer.new3dPrimitive", "model": "layer.newModel",
        "camera": "layer.newCamera", "light": "layer.newLight", "material": "material.set",
    }
    return {
        "effectcraft": {role: name if name in catalog else None for role, name in operations.items()},
        "blender": {"available": bool(blender_build), "build": blender_build,
                    "tools": ["build_blender_scene", "render_blender_shot"]},
        "example": [
            {"id": "comp.renderer", "params": {"renderer": "advanced3d"}},
            {"id": "layer.new3dPrimitive", "params": {"kind": "cube", "width": 100, "height": 60, "depth": 40}},
            {"id": "layer.newLight", "params": {"kind": "Point", "position": [180, 120, -180], "intensity": 150}},
        ],
        "guidance": (
            "Discover exact command inputs with describe_commands. Camera coordinates are composition pixels. "
            "Set text/shape threeDLayer, use Advanced 3D and geometryOptions/extrusionDepth. "
            "Stage an embedded GLB and import with asset.import. "
            "Render multiple perspectives and inspect occlusion, visible faces and shading before declaring volume. "
            "For meshes with deformers or simulation use the installed Blender path. "
            "Choose native or Blender according to the scene."
        ),
    }


def inspect_glb(path):
    with path.open("rb") as source:
        header = source.read(20)
        if len(header) != 20:
            raise ValueError("craft_glb_header_invalid")
        magic, version, length, json_size, chunk_type = struct.unpack("<4sIII4s", header)
        if (magic != b"glTF" or version != 2 or length != path.stat().st_size
                or chunk_type != b"JSON" or json_size > 8 * 1024 * 1024 or json_size + 28 > length):
            raise ValueError("craft_glb_header_invalid")
        try:
            data = json.loads(source.read(json_size))
        except (ValueError, RecursionError) as error:
            raise ValueError("craft_glb_json_invalid") from error
        if not isinstance(data, dict):
            raise ValueError("craft_glb_json_invalid")
        binary = source.read(8)
        size, kind = struct.unpack("<I4s", binary)
        if kind != b"BIN\x00" or size + json_size + 28 != length:
            raise ValueError("craft_glb_binary_invalid")
    buffers = data.get("buffers") or []
    images = data.get("images") or []
    if (len(buffers) != 1 or any(not isinstance(item, dict) or "uri" in item for item in [*buffers, *images])
            or buffers[0].get("byteLength", -1) not in range(max(0, size - 3), size + 1)):
        raise ValueError("craft_glb_requires_embedded_dependencies")
    meshes = data.get("meshes") or []
    if not meshes:
        raise ValueError("craft_glb_mesh_required")
    return {
        "modelFormat": "glb", "coordinateSystem": "glTF right-handed +Y up",
        "meshCount": len(meshes), "nodeCount": len(data.get("nodes") or []), "embeddedImages": len(images),
        "materials": [item.get("name", "Material") for item in (data.get("materials") or [])][:64],
    }
