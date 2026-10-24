"""Versioned official retirement notices. No automatic model substitution."""

from datetime import UTC, date, datetime

NOTICES = {
    "sora-2": ("2026-09-24", None, "https://developers.openai.com/api/docs/deprecations"),
    "sora-2-pro": ("2026-09-24", None, "https://developers.openai.com/api/docs/deprecations"),
    "veo-3.1-lite-generate-preview": (
        "2026-10-22", "gemini-omni-1.1-flash", "https://ai.google.dev/gemini-api/docs/deprecations"
    ),
    "veo-3.1-generate-preview": (
        "2026-10-22", "gemini-omni-1.1-flash", "https://ai.google.dev/gemini-api/docs/deprecations"
    ),
    "veo-3.1-fast-generate-preview": (
        "2026-10-22", "gemini-omni-1.1-flash", "https://ai.google.dev/gemini-api/docs/deprecations"
    ),
    "gemini-omni-flash-preview": (
        "2026-10-22", "gemini-omni-1.1-flash", "https://ai.google.dev/gemini-api/docs/deprecations"
    ),
}


def lifecycle(model, today=None):
    normalized = model.removeprefix("models/")
    if normalized.startswith("sora-2-") or normalized.startswith("sora-2-pro-"):
        normalized = "sora-2"
    entry = NOTICES.get(normalized)
    if not entry:
        return {"status": "no_local_retirement_notice", "verifiedAt": "2026-10-21"}
    shutdown, replacement, source = entry
    return {"status": "retired" if (today or datetime.now(UTC).date()) >= date.fromisoformat(shutdown)
            else "retiring", "shutdownDate": shutdown, "suggestedReplacement": replacement,
            "documentationUrl": source, "verifiedAt": "2026-10-21"}


def assert_supported(model):
    if lifecycle(model)["status"] == "retired":
        raise ValueError("external_model_retired")
