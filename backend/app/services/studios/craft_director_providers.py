"""Explicit, qualified extension points for native production and perceptual review.

No provider is enabled by model assertions, a URL, or a documentation entry.
Deployments install adapters with a qualification receipt for their exact version.
An adapter owns credentials, billing and asset registration; the director chooses it.
"""
from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class DirectorProvider:
    id: str
    version: str
    kind: str  # evaluator or production
    modalities: tuple[str, ...]
    qualification: str
    available: Callable
    execute: Callable
    poll: Callable
    metered: bool = True
    validated_execution: dict | None = None
    description: str | None = None
    validate: Callable | None = None


PROVIDERS: dict[str, DirectorProvider] = {}


def register(provider):
    if (provider.kind not in {"evaluator", "production"} or not provider.qualification
            or not provider.version or not provider.modalities):
        raise ValueError("craft_provider_qualification_required")
    if provider.id in PROVIDERS:
        raise ValueError("craft_provider_already_registered")
    PROVIDERS[provider.id] = provider


def capabilities(db, record, job=None):
    result = []
    for provider in configured_providers(db, record, job).values():
        availability = provider.available(db, record)
        result.append({"id": provider.id, "version": provider.version, "kind": provider.kind,
                       "modalities": list(provider.modalities), "qualification": provider.qualification,
                       "metered": provider.metered,
                       "availability": availability, "validatedExecution": provider.validated_execution,
                       "description": provider.description})
    return result


def configured_providers(db, record, job=None):
    from .craft_claude_review import adapters

    return {**adapters(db, record, job), **PROVIDERS}


def qualified(identifier, kind, db, record, modality=None, job=None):
    provider = configured_providers(db, record, job).get(identifier)
    if not provider or provider.kind != kind:
        raise ValueError("craft_provider_unavailable")
    if modality and modality not in provider.modalities:
        raise ValueError("craft_provider_modality_unavailable")
    if provider.available(db, record).get("status") != "available":
        raise ValueError("craft_provider_unavailable")
    return provider
