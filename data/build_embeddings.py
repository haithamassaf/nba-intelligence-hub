"""
Fetch all NBA data, generate summaries, and load them into ChromaDB.

Run this script to seed or refresh the vector store:
    python -m data.build_embeddings
"""

from data.fetch_stats import fetch_all
from data.transform import build_all_summaries
from rag.vector_store import add_documents, reset_collection, count


def build(fresh: bool = True):
    """
    Full pipeline: fetch → transform → embed.

    If fresh=True, wipes the existing collection first.
    """
    # 1. Fetch live data from NBA API
    datasets = fetch_all()

    # 2. Generate natural-language summaries
    summaries = build_all_summaries(datasets)

    # 3. Load into ChromaDB
    if fresh:
        print("Resetting vector store...")
        reset_collection()

    print("Embedding summaries into ChromaDB...")
    total = add_documents(summaries)
    print(f"Vector store now contains {total} documents.")
    return total


if __name__ == "__main__":
    build()
