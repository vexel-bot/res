"""Authenticated, read-only evolution records from a fixed, versioned catalog."""

import hashlib
import json
from datetime import date
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from ..models import User
from ..security import get_current_user

router = APIRouter(prefix="/product-evolution", tags=["product-evolution"])
ROOT = Path(__file__).resolve().parents[3]
DOCUMENTS = ROOT / "docs" / "evolution"
CATEGORIES = {"feature", "update", "fix", "removal", "analysis", "pending"}
STATUSES = {"integrated", "implemented", "in_progress", "planned"}


def read_catalog():
    catalog = json.loads((DOCUMENTS / "catalog.json").read_text(encoding="utf-8"))
    if catalog["schemaVersion"] != "clicko.product-evolution.v1":
        raise ValueError("evolution_schema_invalid")
    seen = set()
    for entry in catalog["entries"]:
        if entry["id"] in seen or entry["category"] not in CATEGORIES or entry["status"] not in STATUSES:
            raise ValueError("evolution_entry_invalid")
        seen.add(entry["id"])
        date.fromisoformat(entry["date"])
        document = (DOCUMENTS / entry["document"]).resolve()
        if document.parent != DOCUMENTS.resolve() or document.suffix != ".md" or not document.is_file():
            raise ValueError("evolution_document_invalid")
    return catalog


def selected_record(entry_id: str):
    entry = next((item for item in read_catalog()["entries"] if item["id"] == entry_id), None)
    if not entry:
        raise HTTPException(404, "Registro de evolução não encontrado.")
    content = (DOCUMENTS / entry["document"]).read_text(encoding="utf-8")
    return entry, content


@router.get("")
def list_evolution(_user: User = Depends(get_current_user)):
    return read_catalog()


@router.get("/{entry_id}")
def get_evolution(entry_id: str, _user: User = Depends(get_current_user)):
    entry, content = selected_record(entry_id)
    return {**entry, "markdown": content, "checksumSha256": hashlib.sha256(content.encode()).hexdigest()}


@router.get("/{entry_id}/document")
def download_evolution(entry_id: str, _user: User = Depends(get_current_user)):
    entry, content = selected_record(entry_id)
    return Response(
        content,
        media_type="text/markdown",
        headers={
            "Content-Disposition": f'attachment; filename="{entry["document"]}"',
            "Cache-Control": "private, no-store",
        },
    )
