"""
Fetch data for a sport, generate summaries, and load them into ChromaDB.

Seed or refresh a single sport:
    python -m data.build_embeddings nba
    python -m data.build_embeddings nfl

Seed both:
    python -m data.build_embeddings all
"""

from config.settings import SPORTS, DEFAULT_SPORT
from rag.vector_store import add_documents, reset_collection


def _pipeline(sport: str):
    """Return (fetch_all, build_all_summaries) for the given sport (lazy import)."""
    if sport == "nba":
        from data.fetch_stats import fetch_all
        from data.transform import build_all_summaries
        return fetch_all, build_all_summaries
    if sport == "nfl":
        from data.nfl_fetch import fetch_all
        from data.nfl_transform import build_all_summaries
        return fetch_all, build_all_summaries
    raise ValueError(f"Unknown sport '{sport}'. Expected one of {SPORTS}.")


def build(sport: str = DEFAULT_SPORT, fresh: bool = True) -> int:
    """
    Full pipeline for one sport: fetch -> transform -> embed.

    If fresh=True, wipes the sport's collection first.
    """
    fetch_all, build_all_summaries = _pipeline(sport)

    # 1. Fetch live data
    datasets = fetch_all()

    # 2. Generate natural-language summaries
    summaries = build_all_summaries(datasets)

    if not summaries:
        print(f"No {sport.upper()} summaries generated; leaving existing data untouched.")
        return 0

    # 3. Load into ChromaDB
    if fresh:
        print(f"Resetting {sport.upper()} vector store...")
        reset_collection(sport)

    print(f"Embedding {sport.upper()} summaries into ChromaDB...")
    total = add_documents(summaries, sport=sport)
    print(f"{sport.upper()} vector store now contains {total} documents.")
    return total


def build_all(fresh: bool = True) -> dict[str, int]:
    """Build every supported sport."""
    return {sport: build(sport, fresh=fresh) for sport in SPORTS}


if __name__ == "__main__":
    import sys
    arg = sys.argv[1].lower() if len(sys.argv) > 1 else DEFAULT_SPORT
    if arg == "all":
        build_all()
    else:
        build(arg)
