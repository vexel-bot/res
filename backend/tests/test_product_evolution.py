import hashlib

import pytest
from conftest import register

from app.routers import product_evolution


def test_evolution_is_authenticated_and_serves_exact_versioned_markdown(client):
    base = "/api/v1/product-evolution"
    assert client.get(base).status_code == 401
    token, _ = register(client, "evolution@example.com")
    headers = {"Authorization": f"Bearer {token}"}
    result = client.get(base, headers=headers)
    assert result.status_code == 200
    entries = result.json()["entries"]
    assert len({entry["id"] for entry in entries}) == len(entries)
    for entry in entries:
        response = client.get(f"{base}/{entry['id']}", headers=headers)
        assert response.status_code == 200
        value = response.json()
        markdown = (product_evolution.DOCUMENTS / entry["document"]).read_text(encoding="utf-8")
        assert value["markdown"] == markdown
        assert value["checksumSha256"] == hashlib.sha256(markdown.encode()).hexdigest()
        download = client.get(f"{base}/{entry['id']}/document", headers=headers)
        assert download.text == markdown
        assert "text/markdown" in download.headers["content-type"]
        assert "private" in download.headers["cache-control"]
        for reference in entry["evidence"]:
            if not reference.startswith("https://"):
                assert (product_evolution.ROOT / reference).is_file(), reference
    research = next(entry for entry in entries if entry["id"] == "identity-research")
    assert research["status"] == "in_progress"
    assert client.get(f"{base}/missing", headers=headers).status_code == 404
    assert client.get(f"{base}/missing/document", headers=headers).status_code == 404


def test_catalog_cannot_read_documents_outside_the_evolution_directory(tmp_path, monkeypatch):
    import json

    monkeypatch.setattr(product_evolution, "DOCUMENTS", tmp_path)
    (tmp_path / "catalog.json").write_text(
        json.dumps(
            {
                "schemaVersion": "clicko.product-evolution.v1",
                "entries": [
                    {
                        "id": "bad",
                        "date": "2026-10-21",
                        "category": "analysis",
                        "status": "planned",
                        "document": "../private.md",
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="document_invalid"):
        product_evolution.read_catalog()
