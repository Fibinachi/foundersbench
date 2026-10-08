"""Founder registry: who is on the bench, who is coming soon.

Each entry controls the agent's identity, its corpus collections (the
retrieval filter), and whether it is playable yet. Flip `enabled` to
True once a founder's corpus is ingested — the app labels disabled
founders "coming soon".

Corpus files are loaded by path; missing files are skipped with a
warning so the app still runs on a partial corpus.
"""

from __future__ import annotations

FOUNDERS: dict[str, dict] = {
    "hamilton": {
        "name": "Alexander Hamilton",
        "role": "Framer, first Secretary of the Treasury",
        "era": "Founding",
        "death_year": 1804,
        "affiliation": "Federalist",
        "enabled": True,
        "corpus_files": ["data/ambient.jsonl", "data/founder-hamilton.jsonl"],
        "corpus_collections": [
            "Federalist Papers",
            "Blackstone's Commentaries",
            "The Works of Alexander Hamilton (J.C. Hamilton ed.)",
        ],
    },
    "madison": {
        "name": "James Madison",
        "role": "Framer, primary drafter of the Constitution",
        "era": "Founding",
        "death_year": 1836,
        "affiliation": "Federalist",
        "enabled": True,
        "corpus_files": ["data/ambient.jsonl", "data/founder-madison.jsonl"],
        "corpus_collections": [
            "Federalist Papers",
            "Blackstone's Commentaries",
            "The Writings of James Madison (Hunt ed.)",
            "Journal of the Constitutional Convention",
        ],
    },
    "jefferson": {
        "name": "Thomas Jefferson",
        "role": "Framer, third President",
        "era": "Founding",
        "death_year": 1826,
        "affiliation": "Democratic-Republican",
        "enabled": True,
        "corpus_files": ["data/ambient.jsonl", "data/founder-jefferson.jsonl"],
        "corpus_collections": [
            "Federalist Papers",
            "Blackstone's Commentaries",
            "The Writings of Thomas Jefferson (Washington ed.)",
        ],
    },
    "adams": {
        "name": "John Adams",
        "role": "Framer, second President",
        "era": "Founding",
        "death_year": 1826,
        "affiliation": "Federalist",
        "enabled": True,
        "corpus_files": ["data/ambient.jsonl", "data/founder-adams.jsonl"],
        "corpus_collections": [
            "Blackstone's Commentaries",
            "The Works of John Adams (CFA ed.)",
        ],
    },
}


def enabled_founders() -> dict[str, dict]:
    return {k: v for k, v in FOUNDERS.items() if v.get("enabled")}
