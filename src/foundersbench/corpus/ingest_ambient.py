"""Ambient corpus ingest: Federalist Papers + Blackstone's Commentaries.

Fetches public-domain texts, normalizes to HistoricalDocument records,
outputs JSONL ready for BM25 indexing.

Sources:
- Federalist Papers: Project Gutenberg #18 (85 essays, 1787-1788)
- Blackstone's Commentaries: Project Gutenberg (excerpts on criminal
  procedure topics: search/seizure, due process, jury trial)

Usage:
    python -m foundersbench.corpus.ingest_ambient --output data/ambient.jsonl

All documents get full metadata: author, date, collection, document_id.
Corpus layer: "LegalAuthority" for Blackstone, "PrintCulture" for Federalist.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Federalist Papers metadata: essay number -> author, date
# Authorship per the standard Cooke edition. Dates are publication dates.
# ---------------------------------------------------------------------------

FEDERALIST_AUTHORS = {
    # Hamilton wrote 51, Madison 29, Jay 5
    **{n: "Alexander Hamilton" for n in [
        1, 6, 7, 8, 9, 11, 12, 13, 15, 16, 17, 21, 22, 23, 24, 25, 26, 27,
        28, 29, 30, 31, 32, 33, 34, 35, 36, 59, 60, 61, 65, 66, 67, 68, 69,
        70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81, 82, 83, 84, 85,
    ]},
    **{n: "James Madison" for n in [
        10, 14, 18, 19, 20, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48,
        49, 50, 51, 52, 53, 54, 55, 56, 57, 58, 62, 63,
    ]},
    **{n: "John Jay" for n in [2, 3, 4, 5, 64]},
}

# Approximate publication dates (month/year sufficient for citation)
FEDERALIST_DATES = {
    1: "1787-10-27", 2: "1787-10-31", 3: "1787-11-03", 4: "1787-11-07",
    5: "1787-11-10", 6: "1787-11-14", 7: "1787-11-17", 8: "1787-11-20",
    9: "1787-11-21", 10: "1787-11-22", 11: "1787-11-24", 12: "1787-11-27",
    13: "1787-11-28", 14: "1787-11-30", 15: "1787-12-01", 16: "1787-12-04",
    17: "1787-12-05", 18: "1787-12-07", 19: "1787-12-08", 20: "1787-12-11",
    21: "1787-12-12", 22: "1787-12-14", 23: "1787-12-18", 24: "1787-12-19",
    25: "1787-12-21", 26: "1787-12-22", 27: "1787-12-25", 28: "1787-12-26",
    29: "1788-01-09", 30: "1787-12-28", 31: "1788-01-01", 32: "1788-01-02",
    33: "1788-01-02", 34: "1788-01-04", 35: "1788-01-05", 36: "1788-01-08",
    37: "1788-01-11", 38: "1788-01-12", 39: "1788-01-16", 40: "1788-01-18",
    41: "1788-01-19", 42: "1788-01-22", 43: "1788-01-23", 44: "1788-01-25",
    45: "1788-01-26", 46: "1788-01-29", 47: "1788-01-30", 48: "1788-02-01",
    49: "1788-02-02", 50: "1788-02-05", 51: "1788-02-06", 52: "1788-02-08",
    53: "1788-02-09", 54: "1788-02-12", 55: "1788-02-13", 56: "1788-02-16",
    57: "1788-02-19", 58: "1788-02-20", 59: "1788-02-22", 60: "1788-02-23",
    61: "1788-02-26", 62: "1788-02-27", 63: "1788-03-01", 64: "1788-03-05",
    65: "1788-03-07", 66: "1788-03-08", 67: "1788-03-11", 68: "1788-03-12",
    69: "1788-03-14", 70: "1788-03-15", 71: "1788-03-18", 72: "1788-03-19",
    73: "1788-03-21", 74: "1788-03-22", 75: "1788-03-26", 76: "1788-04-01",
    77: "1788-04-02", 78: "1788-05-28", 79: "1788-05-28", 80: "1788-05-28",
    81: "1788-05-28", 82: "1788-05-28", 83: "1788-05-28", 84: "1788-05-28",
    85: "1788-05-28",
}

GUTENBERG_FEDERALIST = "https://www.gutenberg.org/cache/epub/18/pg18.txt"

# Blackstone: Book 4 (public wrongs / criminal procedure) is most relevant.
# Gutenberg ebook #55948 is Commentaries Book 4. We extract key chapters.
GUTENBERG_BLACKSTONE_4 = "https://www.gutenberg.org/cache/epub/55948/pg55948.txt"


def fetch_text(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "FoundersBench/0.1 (research)"})
    with urllib.request.urlopen(req, timeout=60) as resp:
        raw = resp.read().decode("utf-8", errors="replace")
    # Strip Gutenberg header/footer
    start = raw.find("*** START OF")
    end = raw.find("*** END OF")
    if start != -1:
        raw = raw[raw.find("\n", start) + 1:]
    if end != -1:
        raw = raw[:end]
    return raw


def parse_federalist(text: str) -> list[dict]:
    """Split Gutenberg Federalist text into 85 essay documents."""
    # Headers look like: "FEDERALIST No. 1" possibly with "FEDERALIST. No. 1"
    pattern = re.compile(
        r"FEDERALIST[\.\s]+No\.\s*(\d+)", re.IGNORECASE
    )
    matches = list(pattern.finditer(text))
    docs = []
    for i, m in enumerate(matches):
        num = int(m.group(1))
        if num < 1 or num > 85:
            continue
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        # Clean up: remove excessive whitespace, page markers
        body = re.sub(r"\n{3,}", "\n\n", body)
        body = re.sub(r"_+", "", body)
        if len(body) < 500:
            continue  # skip fragments
        author = FEDERALIST_AUTHORS.get(num, "Publius")
        date_str = FEDERALIST_DATES.get(num)
        docs.append({
            "document_id": f"federalist-{num:02d}",
            "author": author,
            "date": date_str,
            "recipient": None,
            "collection": "Federalist Papers",
            "corpus_layer": "PrintCulture",
            "title": f"Federalist No. {num}",
            "full_text": body,
        })
    return docs


# Blackstone Book 4 chapters relevant to criminal procedure.
# We match on chapter headings and extract those sections.
BLACKSTONE_CHAPTERS = [
    (r"CHAPTER\s+IV\.?\s*\n\s*OF\s+OFFENCES\s+AGAINST\s+THE\s+LAW\s+OF\s+NATIONS",
     "blackstone-4-04", "Of Offences Against the Law of Nations"),
    (r"CHAPTER\s+XIX\.?\s*\n\s*OF\s+PROCEEDINGS.*SUMMARY",
     "blackstone-4-19", "Of Summary Proceedings"),
    (r"CHAPTER\s+XX\.?\s*\n\s*OF\s+ARRESTS",
     "blackstone-4-20", "Of Arrests"),
    (r"CHAPTER\s+XXI\.?\s*\n\s*OF\s+BAIL.*COMMITMENT",
     "blackstone-4-21", "Of Bail and Commitment"),
    (r"CHAPTER\s+XXII\.?\s*\n\s*OF\s+THE\s+SEVERAL\s+MODES\s+OF\s+PROSECUTION",
     "blackstone-4-22", "Of the Several Modes of Prosecution"),
    (r"CHAPTER\s+XXVII\.?\s*\n\s*OF\s+TRIAL.*CONVICTION",
     "blackstone-4-27", "Of Trial and Conviction"),
]


def parse_blackstone(text: str) -> list[dict]:
    """Extract criminal-procedure chapters from Blackstone Book 4."""
    docs = []
    for pattern, doc_id, title in BLACKSTONE_CHAPTERS:
        m = re.search(pattern, text, re.IGNORECASE)
        if not m:
            continue
        start = m.start()
        # End at next CHAPTER heading
        next_m = re.search(r"\nCHAPTER\s+[IVXLCDM]+\.?", text[start + 100:], re.IGNORECASE)
        end = start + 100 + next_m.start() if next_m else min(start + 60000, len(text))
        body = text[start:end].strip()
        body = re.sub(r"\n{3,}", "\n\n", body)
        if len(body) < 1000:
            continue
        docs.append({
            "document_id": doc_id,
            "author": "William Blackstone",
            "date": "1769-01-01",  # Book 4 published 1769
            "recipient": None,
            "collection": "Blackstone's Commentaries",
            "corpus_layer": "LegalAuthority",
            "title": f"Commentaries, Book 4: {title}",
            "full_text": body,
        })
    # Fallback: if chapter parsing fails, include a general search/seizure excerpt
    # by keyword search for relevant passages
    if not docs:
        for keyword, doc_id, title in [
            ("warrant", "blackstone-warrant", "On Warrants (extracts)"),
            ("jury", "blackstone-jury", "On Jury Trial (extracts)"),
        ]:
            passages = []
            for pm in re.finditer(keyword, text, re.IGNORECASE):
                s = max(0, pm.start() - 1500)
                e = min(len(text), pm.end() + 1500)
                passages.append(text[s:e].strip())
                if len(passages) >= 5:
                    break
            if passages:
                docs.append({
                    "document_id": doc_id,
                    "author": "William Blackstone",
                    "date": "1769-01-01",
                    "recipient": None,
                    "collection": "Blackstone's Commentaries",
                    "corpus_layer": "LegalAuthority",
                    "title": f"Commentaries: {title}",
                    "full_text": "\n\n---\n\n".join(passages),
                })
    return docs


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest ambient corpus")
    parser.add_argument("--output", required=True, help="Output JSONL path")
    parser.add_argument("--skip-blackstone", action="store_true",
                        help="Skip Blackstone (Federalist only)")
    args = parser.parse_args()

    all_docs: list[dict] = []

    print("Fetching Federalist Papers...", file=sys.stderr)
    fed_text = fetch_text(GUTENBERG_FEDERALIST)
    fed_docs = parse_federalist(fed_text)
    print(f"  parsed {len(fed_docs)} essays", file=sys.stderr)
    all_docs.extend(fed_docs)

    if not args.skip_blackstone:
        print("Fetching Blackstone Book 4...", file=sys.stderr)
        try:
            bl_text = fetch_text(GUTENBERG_BLACKSTONE_4)
            bl_docs = parse_blackstone(bl_text)
            print(f"  parsed {len(bl_docs)} chapters", file=sys.stderr)
            all_docs.extend(bl_docs)
        except Exception as e:
            print(f"  WARNING: Blackstone fetch failed: {e}", file=sys.stderr)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for doc in all_docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
    print(f"Wrote {len(all_docs)} documents to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
