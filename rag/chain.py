"""
Main RAG chain: question in -> grounded answer out (NBA or NFL).

Pipeline:
  1. Classify the user's question (intent, entities, time_range)
  2. Retrieve relevant stat context (structured + semantic)
  3. Generate a grounded response via Claude
"""

import json
import anthropic

from config.settings import ANTHROPIC_API_KEY, CLAUDE_MODEL, DEFAULT_SPORT
from rag.prompts import system_prompt, classify_prompt, CONTEXT_TEMPLATE
from rag.retriever import retrieve

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    return _client


# ── Step 1: Query Classification ─────────────────────────────────────

def classify_query(question: str, sport: str = DEFAULT_SPORT) -> dict:
    """
    Use Claude to extract intent, entities, and time_range from the question.

    Returns a dict like:
      {"intent": "player_comparison", "entities": ["Mahomes", "Allen"], "time_range": "season"}
    """
    client = _get_client()
    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=256,
        messages=[{
            "role": "user",
            "content": classify_prompt(sport).format(question=question),
        }],
    )
    text = response.content[0].text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Fallback: treat as general query
        return {"intent": "general", "entities": [], "time_range": "not_specified"}


# ── Step 3: Response Generation ──────────────────────────────────────

def generate_answer(question: str, context: str, sport: str = DEFAULT_SPORT) -> str:
    """Send the question + retrieved context to Claude and return the answer."""
    client = _get_client()
    user_message = CONTEXT_TEMPLATE.format(context=context, question=question)

    response = client.messages.create(
        model=CLAUDE_MODEL,
        max_tokens=1024,
        system=system_prompt(sport),
        messages=[{"role": "user", "content": user_message}],
    )
    return response.content[0].text


# ── Full Chain ───────────────────────────────────────────────────────

def ask(question: str, sport: str = DEFAULT_SPORT, verbose: bool = False) -> str:
    """
    End-to-end: question -> classify -> retrieve -> generate.

    Set verbose=True to print intermediate steps.
    """
    # 1. Classify
    classification = classify_query(question, sport)
    if verbose:
        print(f"[classify] {json.dumps(classification)}")

    # 2. Retrieve
    context = retrieve(question, sport=sport, classification=classification)
    if verbose:
        n_chunks = context.count("\n\n") + 1 if context else 0
        print(f"[retrieve] {n_chunks} context chunks")

    # 3. Generate
    answer = generate_answer(question, context, sport)
    return answer


# ── Interactive Terminal Mode ────────────────────────────────────────

def chat(sport: str = DEFAULT_SPORT):
    """Interactive REPL for testing the RAG chain."""
    label = sport.upper()
    print("=" * 60)
    print(f"  {label} Intelligence Hub")
    print("  Type your question or 'quit' to exit.")
    print("=" * 60)

    while True:
        try:
            question = input("\nYou: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not question:
            continue
        if question.lower() in ("quit", "exit", "q"):
            print("Goodbye!")
            break

        print("\nThinking...\n")
        answer = ask(question, sport=sport, verbose=True)
        print(f"\nAnalyst: {answer}")


if __name__ == "__main__":
    import sys
    sport = sys.argv[1].lower() if len(sys.argv) > 1 else DEFAULT_SPORT
    chat(sport)
