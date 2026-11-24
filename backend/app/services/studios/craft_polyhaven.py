"""Search the Poly Haven catalog and normalize selected glTF assets to self-contained GLB."""

import hashlib
import json
import re
import struct
import time
from urllib.parse import unquote, urlsplit

from ...domain.studios.editing_resources import RegisteredEditingSourceV1
from ...providers.studios.resource_download import download_resource
from .craft_material_search import _request
from .editing_resources import register_source

API = "https://api.polyhaven.com"
HOST = "dl.polyhaven.org"
CATEGORIES = {"model": "models", "image": "textures", "environment": "hdris"}


def release_file(files, kind):
    if kind == "model":
        return files.get("gltf", {}).get("1k", {}).get("gltf", {})
    if kind == "environment":
        return files.get("hdri", {}).get("1k", {}).get("hdr", {})
    diffuse = files.get("Diffuse") or files.get("diff") or {}
    return diffuse.get("1k", {}).get("jpg", {})


def valid_download(url):
    address = urlsplit(url)
    return (address.scheme == "https" and address.hostname == HOST and not address.username
            and not address.password and address.port in (None, 443))


def search(db, workspace, user, query, deadline, kind):
    if kind not in CATEGORIES:
        raise ValueError("craft_polyhaven_kind_unavailable")
    index = _request(API + "/assets", {"t": CATEGORIES[kind]}, deadline)
    words = set(re.findall(r"[a-z0-9]+", query.casefold()))
    ranked = []
    for slug, item in index.items():
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", slug) or not isinstance(item, dict):
            continue
        primary = set(re.findall(r"[a-z0-9]+", (slug + " " + item.get("name", "")).casefold()))
        tags = set(re.findall(r"[a-z0-9]+", " ".join(item.get("tags", [])).casefold()))
        score = len(words & primary) * 3 + len(words & tags)
        if score:
            ranked.append((score, slug, item))
    result = []
    for _, slug, item in sorted(ranked, key=lambda row: (-row[0], row[1]))[:6]:
        files = _request(API + "/files/" + slug, {}, deadline)
        url = release_file(files, kind).get("url", "")
        if not valid_download(url):
            continue
        page = "https://polyhaven.com/a/" + slug
        author = ", ".join(item.get("authors", {}))
        evidence = f"Poly Haven CC0. Author: {author}. Source: {page}. https://polyhaven.com/license"
        resource = register_source(db, workspace, RegisteredEditingSourceV1(
            title=item.get("name", slug)[:240], kind=kind, url=url, source_url=page,
            description=item.get("description", "")[:3900], usage_evidence=evidence,
            tags=["polyhaven", "cc0"], auto_acquire=True,
        ), user)
        result.append({"id": resource["id"], "title": resource["title"], "sourceUrl": page, "kind": kind,
                       "author": author, "license": "CC0", "usageEvidence": evidence,
                       "autoAcquire": True, "discoveryProvider": "polyhaven"})
    return result


def padded(data, byte=b"\0"):
    return data + byte * (-len(data) % 4)


def prepare_model(path, source):
    slug = urlsplit(source.source_url or "").path.rsplit("/", 1)[-1]
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", slug):
        raise ValueError("craft_polyhaven_model_invalid")
    entry = release_file(_request(API + "/files/" + slug, {}, time.monotonic() + 20), "model")
    if source.url != entry.get("url") or not valid_download(source.url) or path.stat().st_size > 2_000_000:
        raise ValueError("craft_polyhaven_model_source_changed")
    raw = path.read_bytes()
    if hashlib.md5(raw, usedforsecurity=False).hexdigest() != entry.get("md5"):
        raise ValueError("craft_polyhaven_model_checksum_mismatch")
    data = json.loads(raw)
    includes = entry.get("include", {})
    downloaded = {}

    def read_dependency(uri):
        item = includes.get(unquote(uri), {})
        url = item.get("url", "")
        if not valid_download(url) or not 0 < item.get("size", 0) <= 16_000_000:
            raise ValueError("craft_polyhaven_dependency_invalid")
        if uri not in downloaded:
            target = path.with_suffix(f".part{len(downloaded)}")
            download_resource(url, target, [HOST], max_bytes=16_000_000)
            content = target.read_bytes()
            if hashlib.md5(content, usedforsecurity=False).hexdigest() != item.get("md5"):
                raise ValueError("craft_polyhaven_dependency_checksum_mismatch")
            downloaded[uri] = content
        return downloaded[uri]

    if len(data.get("buffers", [])) != 1 or len(data.get("images", [])) > 12:
        raise ValueError("craft_polyhaven_model_invalid")
    buf = data["buffers"][0]
    binary = bytearray(padded(read_dependency(buf.pop("uri"))))
    for image in data.get("images", []):
        uri = image.pop("uri")
        extension = uri.lower().rsplit(".", 1)[-1]
        mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png"}.get(extension)
        if not mime:
            raise ValueError("craft_polyhaven_texture_format_invalid")
        content = read_dependency(uri)
        views = data.setdefault("bufferViews", [])
        image.update(mimeType=mime, bufferView=len(views))
        views.append({"buffer": 0, "byteOffset": len(binary), "byteLength": len(content)})
        binary.extend(padded(content))
    if len(binary) > 90_000_000:
        raise ValueError("craft_polyhaven_model_too_large")
    buf["byteLength"] = len(binary)
    header = padded(json.dumps(data, separators=(",", ":")).encode(), b" ")
    output = path.with_suffix(".glb")
    with output.open("wb") as file:
        file.write(struct.pack("<4sIII4s", b"glTF", 2, 28 + len(header) + len(binary), len(header), b"JSON"))
        file.write(header)
        file.write(struct.pack("<I4s", len(binary), b"BIN\0"))
        file.write(binary)
    return output
