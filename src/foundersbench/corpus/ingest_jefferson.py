"""Jefferson corpus ingest: Washington edition (9 vols) from Project Gutenberg.

Letter format in the Washington edition::

    TO JOHN ADAMS.
                                        PARIS, June 23, 1785.

    DEAR SIR,--My last to you was of the 2d instant...

Each letter becomes a HistoricalDocument with author "Jefferson, Thomas",
the recipient from the TO header, and the date parsed from the dateline.

Usage:
    python -m foundersbench.corpus.ingest_jefferson \
        --inputs data/raw/jefferson-v1.txt ... \
        --output data/founder-jefferson.jsonl
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Gutenberg ebook IDs for the 9-volume Washington edition.
JEFFERSON_VOLUMES = {
    45847: 1, 50046: 2, 52878: 3, 53603: 4, 53767: 5,
    55075: 6, 56035: 7, 56313: 8, 56578: 9,
}

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}

# TO <RECIPIENT>.  — all-caps header starting a letter.
# Some editions prefix the author: "HAMILTON TO <RECIPIENT>."
_TO_HEADER = re.compile(r"^(?:(HAMILTON|JEFFERSON|MADISON|ADAMS) )?TO\s+(.+?)\.\s*$")
# Dateline: "PARIS, June 23, 1785." / "ALBERMARLE, VIRGINIA, Aug. 21, 1777."
# Month/day/year at the end of the line.
_DATELINE = re.compile(
    r"([A-Za-z]+\.?)\s+(\d{1,2})(?:st|d|th)?[,]?\s+(\d{4})\.?\s*$"
)


def parse_dateline(line: str) -> tuple[str | None, str | None]:
    """Return (location, ISO date) from a dateline, or (None, None)."""
    m = _DATELINE.search(line.strip())
    if not m:
        return None, None
    month_raw, day_raw, year_raw = m.group(1), m.group(2), m.group(3)
    month = _MONTHS.get(month_raw.lower().rstrip("."))
    if not month:
        return None, None
    try:
        day = int(day_raw)
        year = int(year_raw)
    except ValueError:
        return None, None
    location = line[: m.start()].strip().rstrip(",").rstrip(".") or None
    return location, f"{year:04d}-{month:02d}-{day:02d}"


def _strip_gutenberg(text: str) -> str:
    start = text.find("*** START OF")
    if start != -1:
        text = text[text.find("\n", start) + 1:]
    end = text.find("*** END OF")
    if end != -1:
        text = text[:end]
    return text


def _clean_recipient(raw: str) -> str:
    # "HIS EXCELLENCY GENERAL WASHINGTON" -> "George Washington"
    # Keep the original form; normalize the most common ones.
    r = raw.strip().title()
    fixes = {
        "His Excellency General Washington": "George Washington",
        "John Adams": "John Adams",
        "James Madison": "James Madison",
        "John Jay": "John Jay",
    }
    return fixes.get(raw.strip(), r)


def parse_letters(text: str, volume: int, author: str, collection: str,
                  id_prefix: str) -> list[dict]:
    text = _strip_gutenberg(text)
    lines = text.splitlines()
    docs: list[dict] = []
    i = 0
    n = len(lines)
    letter_idx = 0
    while i < n:
        m = _TO_HEADER.match(lines[i].strip())
        if not m:
            i += 1
            continue
        recipient = _clean_recipient(m.group(2))
        # Dateline: first non-empty line after the header.
        j = i + 1
        location, date_str = None, None
        while j < n and not lines[j].strip():
            j += 1
        if j < n:
            location, date_str = parse_dateline(lines[j])
            if date_str:
                j += 1
        # Body: until the next TO header or a major section break.
        k = j
        body_lines: list[str] = []
        while k < n:
            if _TO_HEADER.match(lines[k].strip()):
                break
            # Stop at all-caps section headers (new book/part), but not
            # at short salutations.
            s = lines[k].strip()
            if (len(s) > 8 and s.isupper() and not s.startswith("TO ")
                    and s.endswith(".") and len(s.split()) > 4):
                break
            body_lines.append(lines[k])
            k += 1
        body = "\n".join(body_lines).strip()
        body = re.sub(r"\n{3,}", "\n\n", body)
        if len(body) >= 300 and date_str:
            letter_idx += 1
            docs.append({
                "document_id": f"{id_prefix}-v{volume}-{letter_idx:04d}",
                "author": author,
                "date": date_str,
                "recipient": recipient,
                "location": location,
                "collection": collection,
                "corpus_layer": "Writings",
                "title": f"{author} to {recipient}, {date_str}",
                "full_text": body,
            })
        i = k if k > i else i + 1
    return docs


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest founder letters")
    parser.add_argument("--inputs", nargs="+", required=True,
                        help="Gutenberg text files (one per volume)")
    parser.add_argument("--output", required=True, help="Output JSONL path")
    parser.add_argument("--author", default="Jefferson, Thomas",
                        help="Author string for records")
    parser.add_argument("--collection",
                        default="The Writings of Thomas Jefferson (Washington ed.)",
                        help="Collection name for records")
    parser.add_argument("--id-prefix", default="jefferson",
                        help="Document ID prefix")
    parser.add_argument("--volume-map", default="",
                        help="JSON mapping of ebook ID -> volume number")
    args = parser.parse_args()

    volume_map: dict[int, int] = {}
    if args.volume_map:
        volume_map = {int(k): v for k, v in json.loads(args.volume_map).items()}

    all_docs: list[dict] = []
    for path_str in args.inputs:
        path = Path(path_str)
        vol = 0
        m = re.search(r"(\d{5})", path.name)
        if m:
            vol = volume_map.get(int(m.group(1)), JEFFERSON_VOLUMES.get(int(m.group(1)), 0))
        text = path.read_text(encoding="utf-8", errors="replace")
        docs = parse_letters(text, vol, args.author, args.collection,
                             args.id_prefix)
        print(f"  {path.name}: {len(docs)} letters", file=sys.stderr)
        all_docs.extend(docs)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for d in all_docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"Wrote {len(all_docs)} documents to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
