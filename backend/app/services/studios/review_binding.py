"""Content identity for review; transport/audit bookkeeping is not creative content."""

import hashlib
import json

from ...domain.studios.contracts import CreativeDocumentV1
from ...models import CreativeDocument, Post


def requires_natural_sound_review(document: CreativeDocumentV1) -> bool:
    narrative = document.composition.narrative
    return document.content_type in {"video", "presenter"} and (
        narrative.get("naturalSoundPolicy") == "required-before-approval"
        or narrative.get("voicePolicy") == "prohibited"
        or narrative.get("audioMode") == "natural-foley-only"
    )


def reviewable_content(document: CreativeDocumentV1) -> dict:
    payload = document.model_dump(
        mode="json",
        exclude={
            "status",
            "revision",
            "actor_id",
            "correlation_id",
            "review",
            "exports",
            "created_at",
            "updated_at",
        },
    )
    # The handoff is sealed into the immutable review snapshot. It is compared
    # independently with the linked Post, not with the editable Studio document.
    payload.get("composition", {}).get("narrative", {}).pop("publicationHandoff", None)
    return payload


def publication_content(post: Post) -> dict:
    return {
        "postId": post.id,
        "title": post.title,
        "platform": post.platform,
        "format": post.format,
        "caption": post.copy,
        "hashtags": list(post.hashtags or []),
    }


def publication_digest(payload: dict) -> str:
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def publication_handoff(post: Post) -> dict:
    content = publication_content(post)
    return {
        "schemaVersion": "studio.publication-handoff.v1",
        **content,
        "checksumSha256": publication_digest(content),
    }


def invalidate_linked_post_review(db, record: CreativeDocument) -> None:
    post = db.get(Post, record.post_id) if record.post_id else None
    if post and post.status in {"approved", "in_review", "pending_approval", "scheduled"}:
        post.status = "draft"
        post.scheduled_at = None
