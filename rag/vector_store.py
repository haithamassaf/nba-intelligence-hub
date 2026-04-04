"""
ChromaDB vector store — init, add documents, and semantic search.

Uses ChromaDB's built-in ONNX MiniLM embeddings (no external API needed).
"""

import chromadb
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from config.settings import CHROMA_PERSIST_DIR

COLLECTION_NAME = "nba_summaries"

_client: chromadb.ClientAPI | None = None
_embedding_fn = DefaultEmbeddingFunction()


def get_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return _client


def get_collection() -> chromadb.Collection:
    """Get (or create) the NBA summaries collection."""
    client = get_client()
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=_embedding_fn,
        metadata={"hnsw:space": "cosine"},
    )


def add_documents(summaries: list[dict], batch_size: int = 200) -> int:
    """
    Upsert summary dicts into ChromaDB.

    Each dict must have at minimum a 'summary' key (used as the document text).
    Other keys become metadata. Returns the total number of documents stored.
    """
    collection = get_collection()

    ids = []
    documents = []
    metadatas = []

    for i, s in enumerate(summaries):
        doc_type = s.get("type", "unknown")
        # Build a stable ID from type + name/team/index
        if doc_type == "player_season":
            doc_id = f"player_{s.get('player_id', i)}"
        elif doc_type == "team_season":
            doc_id = f"team_{s.get('team_id', i)}"
        elif doc_type == "league_leaders":
            doc_id = f"leaders_{s.get('category', i)}"
        else:
            doc_id = f"doc_{i}"

        ids.append(doc_id)
        documents.append(s["summary"])
        metadatas.append({k: v for k, v in s.items() if k != "summary"})

    # Upsert in batches
    for start in range(0, len(ids), batch_size):
        end = start + batch_size
        collection.upsert(
            ids=ids[start:end],
            documents=documents[start:end],
            metadatas=metadatas[start:end],
        )

    return collection.count()


def query(text: str, n_results: int = 10, where: dict | None = None) -> list[dict]:
    """
    Semantic search over the vector store.

    Returns a list of dicts with 'document', 'metadata', and 'distance' keys,
    ordered by relevance (lowest distance first).
    """
    collection = get_collection()

    kwargs = {
        "query_texts": [text],
        "n_results": n_results,
        "include": ["documents", "metadatas", "distances"],
    }
    if where:
        kwargs["where"] = where

    results = collection.query(**kwargs)

    hits = []
    for doc, meta, dist in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
    ):
        hits.append({"document": doc, "metadata": meta, "distance": dist})
    return hits


def reset_collection():
    """Delete and recreate the collection (used during data refresh)."""
    client = get_client()
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # Collection didn't exist yet
    return get_collection()


def count() -> int:
    return get_collection().count()
