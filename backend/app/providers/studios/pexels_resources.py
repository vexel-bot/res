"""Candidate discovery only. Import still uses the validated resource pipeline."""

import httpx


def discover(key, query, kind, *, orientation="any", duration_seconds=None, client=None):
    if kind not in {"image", "video"}:
        raise ValueError("pexels_resource_kind_unsupported")
    if not key:
        return {"status": "unconfigured", "candidates": [], "alternatives": ["project", "catalog", "upload"]}

    def request(http):
        endpoint = "https://api.pexels.com/v1/videos/search" if kind == "video" else "https://api.pexels.com/v1/search"
        params = {"query": query, "per_page": 12}
        if orientation in {"portrait", "landscape", "square"}:
            params["orientation"] = orientation
        with http.stream("GET", endpoint, params=params, headers={"Authorization": key}) as response:
            if response.status_code != 200:
                raise ValueError(f"pexels_http_{response.status_code}")
            payload = bytearray()
            for chunk in response.iter_bytes():
                payload.extend(chunk)
                if len(payload) > 2 * 1024 * 1024:
                    raise ValueError("pexels_response_too_large")
        import json

        data = json.loads(payload)
        candidates = []
        items = data.get("videos" if kind == "video" else "photos", [])
        if kind == "video" and duration_seconds:
            items = [item for item in items if item.get("duration", 0) >= duration_seconds]
        for item in items[:12]:
            author = (
                item.get("user", {})
                if kind == "video"
                else {"name": item.get("photographer"), "url": item.get("photographer_url")}
            )
            if kind == "video":
                files = item.get("video_files", [])
            else:
                sources = item.get("src", {})
                # Do not default to the original: provider originals can exceed
                # the catalog's decoded-pixel ceiling even when a documented HD
                # derivative is available. Preserve the original as a fallback
                # and let acquisition select the smallest suitable variant.
                files = [
                    {"link": sources.get("large2x"), "width": 1880, "height": 1300},
                    {"link": sources.get("large"), "width": 940, "height": 650},
                    {
                        "link": sources.get("original"),
                        "width": item.get("width"),
                        "height": item.get("height"),
                    },
                ]
                files = [entry for entry in files if entry["link"]]
            candidates.append(
                {
                    "provider": "pexels",
                    "providerId": str(item["id"]),
                    "kind": kind,
                    "sourceUrl": item.get("url"),
                    "previewUrl": item.get("image") if kind == "video" else item.get("src", {}).get("medium"),
                    "files": files,
                    "width": item.get("width"),
                    "height": item.get("height"),
                    "durationSeconds": item.get("duration"),
                    "description": item.get("alt", ""),
                    "author": author,
                    "attribution": {"provider": "Pexels", "url": "https://www.pexels.com"},
                    "licenseUrl": "https://www.pexels.com/license/",
                    "observation": "not_inspected",
                    "renderReady": False,
                    "requiresInspection": True,
                    "acquisitionAllowed": True,
                }
            )
        return {"status": "candidates", "query": query, "candidates": candidates}

    if client:
        try:
            return request(client)
        except httpx.HTTPError as error:
            raise ValueError("pexels_transport_unavailable") from error
    with httpx.Client(timeout=20, follow_redirects=False, trust_env=False) as http:
        try:
            return request(http)
        except httpx.HTTPError as error:
            raise ValueError("pexels_transport_unavailable") from error
