"""Deterministic, local UI sounds for causal editorial events."""

from __future__ import annotations

import math
import re
import struct
import unicodedata
import wave
from pathlib import Path

SOUND_RULES = (
    (("publicar", "publicacao", "publish", "confirmar", "confirmacao"), "publish_confirm"),
    (("scroll", "rolar", "passagem", "feed"), "feed_scroll"),
    (("transicao", "transition", "entrada", "revelar"), "soft_transition"),
)


def _tokens(value: str) -> set[str]:
    normalized = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return set(re.findall(r"[a-z0-9]+", normalized))


def discover(query: str, purpose: str, kind: str):
    if kind != "sound_effect":
        return {"status": "unsupported", "candidates": []}
    words = _tokens(query + " " + purpose)
    match = next(
        ((profile, sorted(words.intersection(keys))) for keys, profile in SOUND_RULES if words & set(keys)),
        None,
    )
    if not match:
        return {"status": "no_semantic_match", "candidates": []}
    profile, matched = match
    return {
        "status": "candidates",
        "candidates": [{
            "id": f"procedural-sound:{profile}",
            "provider": "procedural-sound",
            "providerId": profile,
            "kind": "sound_effect",
            "description": f"Sinal de interface sintético {profile}",
            "query": query,
            "purpose": purpose,
            "semanticMatch": {"terms": matched, "confidence": "rule_exact"},
            "rightsStatus": "original_procedural",
            "renderReady": False,
        }],
    }


def render(profile: str, destination: Path, sample_rate: int = 48_000) -> dict:
    profiles = {
        "publish_confirm": (0.22, 620.0, 960.0, 0.55),
        "feed_scroll": (0.16, 900.0, 420.0, 0.42),
        "soft_transition": (0.28, 280.0, 680.0, 0.45),
    }
    if profile not in profiles:
        raise ValueError("procedural_sound_profile_unknown")
    duration, start_hz, end_hz, amplitude = profiles[profile]
    sample_count = round(duration * sample_rate)
    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destination), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(sample_rate)
        frames = []
        for index in range(sample_count):
            t = index / sample_rate
            normalized = t / duration
            envelope = math.sin(math.pi * min(1.0, normalized)) ** 1.6
            chirp_phase = 2 * math.pi * (
                start_hz * t + ((end_hz - start_hz) / (2 * duration)) * t * t
            )
            sample = int(max(-1, min(1, amplitude * math.sin(chirp_phase) * envelope)) * 32767)
            frames.append(struct.pack("<h", sample))
        output.writeframes(b"".join(frames))
    return {"profile": profile, "durationSeconds": duration, "sampleRate": sample_rate, "channels": 1}
