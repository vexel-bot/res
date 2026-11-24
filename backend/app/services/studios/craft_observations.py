"""Durable revision-aware discovery results, independent of context windows."""
import copy
import hashlib
import json

READ_COMMANDS = {"effect.list", "comp.info", "project.summary", "layer.tree"}
GLOBAL_TOOLS = {"describe_commands", "find_commands", "inspect_editor_capabilities"}


def global_scope(name, args):
    commands = args.get("commands", [])
    return name in GLOBAL_TOOLS or (name == "edit_project" and bool(commands)
        and all(c.get("id") == "effect.list" for c in commands))


def eligible(name, args):
    return name in GLOBAL_TOOLS or (name == "edit_project" and bool(args.get("commands"))
        and all(c.get("id") in READ_COMMANDS for c in args["commands"]))


def key(name, args, build, checksum):
    scope = None if global_scope(name, args) else checksum
    return hashlib.sha256(json.dumps([name, args, build, scope], sort_keys=True).encode()).hexdigest()


def remember(archive, name, args, result, build, checksum, tool_id):
    identifier = key(name, args, build, checksum)
    archive[identifier] = {"id": identifier, "name": name, "input": copy.deepcopy(args),
        "buildId": build, "checksum": None if global_scope(name, args) else checksum,
        "toolUseId": tool_id, "result": copy.deepcopy(result)}
    return identifier


def recall(archive, identifier, build, checksum):
    item = archive.get(identifier)
    # Legacy effect.list receipts were unnecessarily tied to a project revision.
    # The registry is build-scoped; this exception never revives project data.
    if (not item or item["buildId"] != build
            or (item["checksum"] not in {None, checksum}
                and not global_scope(item["name"], item["input"]))):
        raise ValueError("craft_observation_stale_or_missing")
    return copy.deepcopy(item["result"])


def index(archive):
    return [{**{k: v for k, v in item.items() if k != "result"},
             "scope": "engine_build" if global_scope(item["name"], item["input"]) else "project_revision"}
            for item in archive.values()]


def present(value, pointer="", offset=0, limit=20):
    """Page large discovery schemas; preserve full originals in the archive."""
    selected = value
    if pointer:
        if not pointer.startswith("/"):
            raise ValueError("craft_observation_pointer_invalid")
        for part in pointer[1:].split("/"):
            part = part.replace("~1", "/").replace("~0", "~")
            selected = selected[int(part)] if isinstance(selected, list) else selected[part]
    if offset < 0 or not 1 <= limit <= 50:
        raise ValueError("craft_observation_page_invalid")
    if len(json.dumps(selected)) < 12000:
        return selected
    if isinstance(selected, list):
        return {"path": pointer, "total": len(selected), "items": [
            {"path": pointer + "/" + str(i), "summary": {k: item[k] for k in ("id", "name", "category") if k in item}
             if isinstance(item, dict) else {"type": type(item).__name__, "count": len(item) if isinstance(item, list) else None}}
            for i, item in enumerate(selected[offset:offset+limit], start=offset)],
            "nextOffset": offset+limit if offset+limit < len(selected) else None}
    if isinstance(selected, dict):
        return {"path": pointer, "fields": [{"key": k, "path": pointer + "/" + k.replace("~", "~0").replace("/", "~1"),
            "type": type(v).__name__} for k, v in selected.items()],
            "instruction": "Use recall_native_observation with this observation id and a path to inspect the needed field."}
    return selected
