from __future__ import annotations

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from ..config import settings
from .circuit_breakers import qdrant_breaker

EMBEDDING_DIM = 3072  # gemini-embedding-001

_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    global _client
    if _client is None:
        _client = QdrantClient(url=settings.qdrant_url, check_compatibility=False)
    return _client


@qdrant_breaker
def ensure_collection(name: str) -> None:
    client = get_client()
    collections = [c.name for c in client.get_collections().collections]
    if name not in collections:
        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=EMBEDDING_DIM, distance=Distance.COSINE),
        )


@qdrant_breaker
def upsert_embedding(
    collection: str, point_id: str, vector: list[float], payload: dict | None = None
) -> None:
    ensure_collection(collection)
    client = get_client()
    client.upsert(
        collection_name=collection,
        points=[
            PointStruct(
                id=point_id,
                vector=vector,
                payload=payload or {},
            )
        ],
    )


@qdrant_breaker
def search_similar(collection: str, vector: list[float], limit: int = 20) -> list[dict]:
    ensure_collection(collection)
    client = get_client()
    results = client.query_points(
        collection_name=collection,
        query=vector,
        limit=limit,
    )
    return [{"id": str(r.id), "score": r.score, "payload": r.payload} for r in results.points]
