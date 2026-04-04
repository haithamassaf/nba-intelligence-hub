"""
Retriever — combines semantic vector search with optional structured lookups.

Two retrieval paths:
  Path A (Structured): Use extracted entities to filter by type/team/player.
  Path B (Semantic):   Embed the question and search the full vector store.

Both paths merge into a single context string for the LLM.
"""

from rag.vector_store import query as vector_query


def retrieve(question: str, classification: dict | None = None, top_k: int = 12) -> str:
    """
    Retrieve relevant context for a user question.

    Args:
        question:       The raw user question.
        classification: Output of the query classifier (intent, entities, time_range).
                        If None, falls back to pure semantic search.
        top_k:          Maximum number of chunks to return.

    Returns:
        A single string of newline-separated context documents.
    """
    chunks: list[str] = []
    seen_ids: set[str] = set()

    # ── Path A: Targeted retrieval based on classification ───────────
    if classification:
        intent = classification.get("intent", "general")
        entities = classification.get("entities", [])

        # For player queries, search with player name for precision
        if intent in ("player_stats", "player_comparison", "award_race") and entities:
            for entity in entities[:4]:  # cap to avoid too many queries
                hits = vector_query(entity, n_results=3)
                for h in hits:
                    doc_id = h["document"][:60]
                    if doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        chunks.append(h["document"])

        # For team queries, add team-filtered results
        if intent == "team_stats" and entities:
            for entity in entities[:4]:
                hits = vector_query(entity, n_results=3)
                for h in hits:
                    doc_id = h["document"][:60]
                    if doc_id not in seen_ids:
                        seen_ids.add(doc_id)
                        chunks.append(h["document"])

        # For rankings / award races, pull league leaders
        if intent in ("rankings", "award_race"):
            hits = vector_query(
                question, n_results=3, where={"type": "league_leaders"}
            )
            for h in hits:
                doc_id = h["document"][:60]
                if doc_id not in seen_ids:
                    seen_ids.add(doc_id)
                    chunks.append(h["document"])

    # ── Path B: Broad semantic search ────────────────────────────────
    remaining = top_k - len(chunks)
    if remaining > 0:
        hits = vector_query(question, n_results=remaining)
        for h in hits:
            doc_id = h["document"][:60]
            if doc_id not in seen_ids:
                seen_ids.add(doc_id)
                chunks.append(h["document"])

    return "\n\n".join(chunks[:top_k])
