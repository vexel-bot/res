from conftest import register
from fastapi.testclient import TestClient

from app.models import EMBEDDING_DIMENSIONS
from app.services.knowledge import CHUNK_CHARS, chunk_content


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_chunking_is_bounded_and_preserves_offsets():
    content = " ".join(f"palavra-{index}" for index in range(500))
    chunks = chunk_content(content)
    assert len(chunks) > 1
    assert all(len(chunk.content) <= CHUNK_CHARS for chunk in chunks)
    assert all(content[chunk.char_start : chunk.char_end] == chunk.content for chunk in chunks)


def test_lexical_knowledge_search_is_traceable_deduplicated_and_isolated(client: TestClient):
    token, workspace = register(client, "knowledge@example.com")
    other_token, _ = register(client, "knowledge-other@example.com")
    payload = {
        "workspaceId": workspace,
        "title": "Guia comercial",
        "content": "A marca atende restaurantes com cardápio digital e pedidos por delivery.",
        "sourceType": "brain",
        "sourceUrl": "https://example.com/guia",
        "metadata": {"revision": 2},
    }
    created = client.post("/api/v1/knowledge/documents", headers=auth(token), json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["embeddingStatus"] == "unconfigured"
    assert created.json()["chunkCount"] == 1

    duplicate = client.post("/api/v1/knowledge/documents", headers=auth(token), json=payload)
    assert duplicate.status_code == 409

    search = client.get(
        f"/api/v1/knowledge/search?workspace_id={workspace}&q=cardápio delivery",
        headers=auth(token),
    )
    assert search.status_code == 200, search.text
    body = search.json()
    assert body["retrievalMode"] == "lexical"
    assert body["results"][0]["citation"]["sourceUrl"] == "https://example.com/guia"
    assert body["results"][0]["lexicalScore"] > 0

    assert (
        client.get(f"/api/v1/knowledge/documents?workspace_id={workspace}", headers=auth(other_token)).status_code
        == 404
    )
    document_id = created.json()["id"]
    assert client.delete(f"/api/v1/knowledge/documents/{document_id}", headers=auth(other_token)).status_code == 404
    assert client.delete(f"/api/v1/knowledge/documents/{document_id}", headers=auth(token)).status_code == 204


def test_hybrid_search_uses_configured_embeddings(client: TestClient, monkeypatch):
    class FakeEmbeddingProvider:
        configured = True

        def embed(self, texts: list[str]):
            vectors = []
            for value in texts:
                vector = [0.0] * EMBEDDING_DIMENSIONS
                vector[0 if "inovação" in value.casefold() or "tendência" in value.casefold() else 1] = 1.0
                vectors.append(vector)
            return vectors, {"model": "deterministic-test-provider"}

    monkeypatch.setattr("app.routers.knowledge.OpenAICompatibleEmbeddingProvider", FakeEmbeddingProvider)
    token, workspace = register(client, "knowledge-hybrid@example.com")
    created = client.post(
        "/api/v1/knowledge/documents",
        headers=auth(token),
        json={
            "workspaceId": workspace,
            "title": "Posicionamento",
            "content": "Inovação responsável orienta todas as decisões da empresa.",
            "sourceType": "manual",
        },
    )
    assert created.status_code == 201, created.text
    assert created.json()["embeddingStatus"] == "ready"

    search = client.get(
        f"/api/v1/knowledge/search?workspace_id={workspace}&q=tendência",
        headers=auth(token),
    )
    assert search.status_code == 200, search.text
    body = search.json()
    assert body["retrievalMode"] == "hybrid"
    assert body["embeddingModel"] == "deterministic-test-provider"
    assert body["results"][0]["semanticScore"] > 0.99
