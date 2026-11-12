"""Public image discovery, with provenance, through the free Commons Action API."""

import json
import re
import time
from html import unescape
from urllib.parse import urlsplit

import httpx

from ...domain.studios.editing_resources import RegisteredEditingSourceV1
from .editing_resources import register_source

ENDPOINT = "https://commons.wikimedia.org/w/api.php"


def _text(value):
    return unescape(re.sub(r"<[^>]*>", " ", str(value))).strip()


def _request(endpoint, params, deadline):
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise ValueError("craft_agent_deadline")
    try:
        with httpx.Client(timeout=min(20, remaining), follow_redirects=False) as client:
            with client.stream("GET", endpoint, params=params,
                               headers={"User-Agent": "ClickoEditorialResearch/1.0 (local media editor)"}) as response:
                response.raise_for_status()
                payload = bytearray()
                for chunk in response.iter_bytes():
                    payload.extend(chunk)
                    if len(payload) > 2_000_000:
                        raise ValueError("craft_material_search_response_too_large")
                data = json.loads(payload)
    except (httpx.HTTPError, ValueError) as exc:
        raise ValueError("craft_material_public_search_unavailable") from exc
    if not isinstance(data, dict) or data.get("error"):
        raise ValueError("craft_material_public_search_unavailable")
    return data


def _nasa_images(db, workspace_id, user_id, query, deadline):
    data = _request("https://images-api.nasa.gov/search", {"q": query, "media_type": "image", "page_size": 12}, deadline)
    result = []
    for item in data.get("collection", {}).get("items", []):
        detail = next(iter(item.get("data", [])), {})
        url = next((link.get("href", "") for link in item.get("links", []) if link.get("render") == "image"), "")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != "images-assets.nasa.gov" or parsed.username or parsed.password or parsed.port not in (None, 443):
            continue
        identifier = detail.get("nasa_id")
        if not isinstance(identifier, str) or not re.fullmatch(r"[a-zA-Z0-9_ .()-]+", identifier):
            continue
        from urllib.parse import quote
        page_url = "https://images.nasa.gov/details/" + quote(identifier, safe="")
        author = _text(detail.get("photographer") or detail.get("secondary_creator") or detail.get("center", ""))
        evidence = f"Discovered in NASA image library. Credit: {author}. Source: {page_url}. Item-specific rights have not been verified; NASA holdings can include third-party works. https://www.nasa.gov/nasa-brand-center/images-and-media/"
        source = register_source(db, workspace_id, RegisteredEditingSourceV1(
            title=_text(detail.get("title", identifier))[:240], kind="image", url=url, source_url=page_url,
            usage_evidence=evidence[:4000], description=_text(detail.get("description", ""))[:4000],
            tags=["nasa", "rights_unverified"], auto_acquire=False,
        ), user_id)
        result.append({"id": source["id"], "title": source["title"], "kind": "image", "sourceUrl": page_url,
                       "description": source["description"], "autoAcquire": False, "author": author,
                       "usageEvidence": source["usageEvidence"], "discoveryProvider": "nasa_images",
                       "fallbackAfter": "wikimedia_commons_unavailable", "coverage": "Search metadata only; no visual or item-specific rights inspection."})
    return result


def public_images(db, workspace_id, user_id, query, deadline):
    if not isinstance(query, str) or not query.strip() or len(query) > 250:
        raise ValueError("craft_material_query_invalid")
    params = {"action": "query", "format": "json", "formatversion": 2, "generator": "search",
              "gsrsearch": query, "gsrnamespace": 6, "gsrlimit": 12, "prop": "imageinfo",
              "iiprop": "url|mime|size|extmetadata", "iiurlwidth": 1600}
    try:
        data = _request(ENDPOINT, params, deadline)
    except ValueError as exc:
        if str(exc) != "craft_material_public_search_unavailable":
            raise
        return _nasa_images(db, workspace_id, user_id, query, deadline)
    result = []
    for page in sorted(data.get("query", {}).get("pages", []), key=lambda item: item.get("index", 0)):
        info = next(iter(page.get("imageinfo", [])), {})
        # Only formats verified by the current native media importer are eligible.
        if info.get("mime") not in {"image/png", "image/jpeg", "image/webp"}:
            continue
        url = info.get("thumburl") or info.get("url", "")
        parsed = urlsplit(url)
        if parsed.scheme != "https" or parsed.hostname != "upload.wikimedia.org" or parsed.username or parsed.password or parsed.port not in (None, 443):
            continue
        metadata = info.get("extmetadata", {})
        def field(key):
            return _text(metadata.get(key, {}).get("value", ""))
        license_name, license_url = field("LicenseShortName"), field("LicenseUrl")
        author = field("Artist")
        public_domain = license_name.casefold() in {"cc0", "public domain", "pdm"}
        attribution = license_name.upper().startswith(("CC BY ", "CC BY-SA ")) and bool(author and license_url)
        eligible = public_domain or attribution
        page_url = f"https://commons.wikimedia.org/?curid={page['pageid']}"
        evidence = f"Commons declares: {license_name or 'license not supplied'}. {license_url}. Author: {author}. Source: {page_url}."
        source = register_source(db, workspace_id, RegisteredEditingSourceV1(
            title=_text(page.get("title", "Public image"))[:240], kind="image", url=url, source_url=page_url,
            usage_evidence=evidence[:4000], description=field("ImageDescription")[:4000],
            tags=["commons", license_name[:100]], auto_acquire=eligible,
        ), user_id)
        result.append({"id": source["id"], "title": source["title"], "kind": "image", "sourceUrl": page_url,
                       "autoAcquire": eligible, "license": license_name, "licenseUrl": license_url, "author": author,
                       "description": source["description"], "discoveryProvider": "wikimedia_commons",
                       "usageEvidence": source["usageEvidence"],
                       "instruction": "Preserve attribution and license terms. Search relevance does not establish product identity or official endorsement."})
    return result
