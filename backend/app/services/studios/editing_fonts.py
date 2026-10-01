"""Official font discovery; acquisition always pins an actual variant file."""

import json

import httpx

from ...config import get_settings
from ...domain.studios.editing_resources import ImportResourceV1


def lookup_fonts(family):
    key = get_settings().google_fonts_api_key
    if not key:
        raise ValueError("google_fonts_key_required")
    try:
        with httpx.Client(timeout=30, trust_env=False, follow_redirects=False) as client:
            with client.stream(
                "GET",
                "https://www.googleapis.com/webfonts/v1/webfonts",
                params={"key": key.get_secret_value(), "family": family},
            ) as response:
                if response.status_code != 200:
                    raise ValueError("google_fonts_lookup_failed")
                data = bytearray()
                for chunk in response.iter_bytes():
                    data.extend(chunk)
                    if len(data) > 8 * 1024 * 1024:
                        raise ValueError("google_fonts_response_too_large")
        return [
            {k: item.get(k) for k in ("family", "variants", "files", "version", "lastModified")}
            for item in json.loads(data).get("items", [])
            if item.get("family", "").casefold() == family.casefold()
        ]
    except httpx.HTTPError as error:
        raise ValueError("google_fonts_lookup_failed") from error


def acquire_font(db, workspace_id, family, variant, user_id):
    from .editing_resources import import_resource

    choices = lookup_fonts(family)
    if len(choices) != 1 or variant not in choices[0].get("files", {}):
        raise ValueError("google_fonts_family_or_variant_unavailable")
    selected = choices[0]
    url = selected["files"][variant].replace("http://", "https://", 1)
    return import_resource(
        db,
        workspace_id,
        ImportResourceV1(
            kind="font",
            title=f"{family} {variant}",
            family=family,
            variant=variant,
            version=selected["version"],
            url=url,
            official=True,
            usage_evidence="Família distribuída pelo Google Fonts; preservar a licença da família na utilização.",
            source_url="https://fonts.google.com/",
            tags=[family, variant],
        ),
        user_id,
    )
