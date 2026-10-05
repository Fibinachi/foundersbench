"""Founders Bench CLI — on-site interactive mode.

Usage:
    python -m foundersbench.cli --founder hamilton --corpus data/ambient.jsonl

    ANTHROPIC_API_KEY=... python -m foundersbench.cli --founder hamilton

Starts an interactive chat loop. Type 'quit' to exit.
BYOK: keys from environment (ANTHROPIC_API_KEY, OPENAI_API_KEY).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Founder registry (placeholder until the Friday poll picks the winner).
# Each entry: name, role, era, death year (anachronism cutoff), collections.
# ---------------------------------------------------------------------------

FOUNDERS: dict[str, dict] = {
    "hamilton": {
        "name": "Alexander Hamilton",
        "role": "Framer, first Secretary of the Treasury",
        "era": "Founding",
        "death_year": 1804,
        "affiliation": "Federalist",
        "corpus_collections": ["Federalist Papers", "Blackstone's Commentaries"],
    },
    "madison": {
        "name": "James Madison",
        "role": "Framer, primary drafter of the Constitution",
        "era": "Founding",
        "death_year": 1836,
        "affiliation": "Federalist",
        "corpus_collections": ["Federalist Papers", "Blackstone's Commentaries"],
    },
    "jefferson": {
        "name": "Thomas Jefferson",
        "role": "Framer, third President",
        "era": "Founding",
        "death_year": 1826,
        "affiliation": "Democratic-Republican",
        "corpus_collections": ["Blackstone's Commentaries"],
    },
    "adams": {
        "name": "John Adams",
        "role": "Framer, second President",
        "era": "Founding",
        "death_year": 1826,
        "affiliation": "Federalist",
        "corpus_collections": ["Blackstone's Commentaries"],
    },
}


def load_corpus(path: Path) -> list[dict]:
    docs = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    return docs


def to_historical_documents(raw: list[dict]):
    from foundersbench.models import HistoricalDocument

    out = []
    for r in raw:
        date = None
        if r.get("date"):
            try:
                date = datetime.fromisoformat(r["date"])
            except ValueError:
                pass
        out.append(HistoricalDocument(
            document_id=r["document_id"],
            author=r.get("author", ""),
            date=date,
            recipient=r.get("recipient"),
            collection=r.get("collection", ""),
            corpus_layer=r.get("corpus_layer", ""),
            title=r.get("title", ""),
            full_text=r.get("full_text", ""),
        ))
    return out


async def chat_loop(founder_key: str, corpus_path: Path) -> None:
    from foundersbench.agent_service import FounderAgentService
    from foundersbench.models import BenchSession, FounderAgent
    from foundersbench.providers import default_provider
    from foundersbench.retrieval import CorpusIndex

    if founder_key not in FOUNDERS:
        print(f"Unknown founder '{founder_key}'. Choices: {', '.join(FOUNDERS)}",
              file=sys.stderr)
        sys.exit(1)

    cfg = FOUNDERS[founder_key]
    print(f"Loading corpus from {corpus_path}...", file=sys.stderr)
    raw_docs = load_corpus(corpus_path)
    documents = to_historical_documents(raw_docs)
    print(f"  {len(documents)} documents", file=sys.stderr)

    index = CorpusIndex(documents)
    provider = default_provider()
    if not provider.is_configured():
        print("WARNING: no API key found (ANTHROPIC_API_KEY / OPENAI_API_KEY).",
              file=sys.stderr)
        print("Responses will use labeled fallback text.", file=sys.stderr)
    else:
        print(f"  provider: {provider.name}", file=sys.stderr)

    agent = FounderAgent(
        name=cfg["name"],
        era=cfg["era"],
        role=cfg["role"],
        affiliation=cfg["affiliation"],
        corpus_collections=cfg["corpus_collections"],
        death_year=cfg["death_year"],
    )

    service = FounderAgentService(index, provider)
    session_kwargs: dict = {"mode": "one_on_one", "era": cfg["era"],
                            "user_question": ""}
    from foundersbench.models import BenchMode
    session = BenchSession(mode=BenchMode.ONE_ON_ONE, era=cfg["era"],
                           user_question="")

    print(f"\nYou are speaking with {cfg['name']} ({cfg['role']}).")
    print("Type 'quit' to exit.\n")

    while True:
        try:
            user_in = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if user_in.lower() in ("quit", "exit", "q"):
            break
        if not user_in:
            continue
        session.user_question = user_in
        turn = await service.respond(agent, session, user_in)
        print(f"\n{turn.speaker_name}: {turn.text}")
        if turn.citations:
            print("\n  Sources:")
            for c in turn.citations:
                print(f"    [{c.label}]")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Founders Bench CLI")
    parser.add_argument("--founder", default="hamilton",
                        help=f"founder key ({', '.join(FOUNDERS)})")
    parser.add_argument("--corpus", default="data/ambient.jsonl",
                        help="Path to ambient corpus JSONL")
    args = parser.parse_args()
    asyncio.run(chat_loop(args.founder, Path(args.corpus)))


if __name__ == "__main__":
    main()
