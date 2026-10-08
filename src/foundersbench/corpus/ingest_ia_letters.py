"""Letter ingest for Internet Archive OCR texts (CFA Adams, Hunt Madison, etc).

IA _djvu.txt format (with OCR spacing noise)::

    TO    J  AM  IS    WARREN.

    Philadelphia,  24  July,  1775.
    Dear  Sir  :  —  I  am  determined ...

Light OCR cleanup is applied (collapse runs of spaces); character-level
OCR errors are left as-is and noted in the record.

Usage:
    python -m foundersbench.corpus.ingest_ia_letters \
        --inputs /tmp/worksjohnadams07adamrich.txt \
        --output data/founder-adams.jsonl \
        --author "Adams, John" \
        --collection "The Works of John Adams (CFA ed.)" \
        --id-prefix adams
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

_TO_HEADER = re.compile(
    r"^TO\s+(.+?)(?:\.\d+\s+MAD\. MSS\.|\.\s+MAD\. MSS\.|\.)\s*$")
# Dateline: "Philadelphia,  24  July,  1775." (day month year)
_DATELINE_DMY = re.compile(
    r"^(.+?),\s*(\d{1,2})\s+([A-Za-z]+),?\s+(\d{4})\.?\s*$"
)
# Fallback: "Aug. 21, 1777" (month day year); year may be OCR-corrupted.
_DATELINE_MDY = re.compile(
    r"([A-Za-z]+\.?)\s+(\d{1,2})(?:st|d|th)?[,]?\s+([\d\[\]()ilIogbsSaex]{3,6})\.?\s*$"
)

_MONTHS = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11,
    "dec": 12, "december": 12,
}


def clean_text(s: str) -> str:
    """Light OCR cleanup: collapse runs of spaces, normalize dashes."""
    s = re.sub(r"[ \t]{2,}", " ", s)
    s = s.replace("—", "--").replace("–", "-")
    return s


_OCR_YEAR_FIX = str.maketrans({
    "i": "1", "l": "1", "I": "1", "o": "0", "O": "0",
    "g": "9", "b": "6", "s": "5", "S": "5", "a": "4", "e": "3",
})


def _repair_year(raw: str) -> int | None:
    """Turn OCR-corrupted year like '[i7]6g' into 1769."""
    cleaned = re.sub(r"[\[\]()]", "", raw).translate(_OCR_YEAR_FIX)
    cleaned = re.sub(r"\D", "", cleaned)
    if len(cleaned) == 4:
        year = int(cleaned)
        if 1600 <= year <= 1900:
            return year
    return None


def parse_dateline(line: str) -> tuple[str | None, str | None]:
    """Tolerant dateline parse. Handles DMY and MDY order, OCR noise."""
    line = clean_text(line.strip())
    # Find month, day, year independently.
    month_m = re.search(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?", line, re.I)
    if not month_m:
        return None, None
    month = _MONTHS.get(month_m.group(0).lower().rstrip(".")[:3])
    if not month:
        return None, None
    # Day: 1-2 digits near the month (allow trailing ? from OCR).
    # Prefer before-month (DMY: "24 July, 1775"), then after (MDY).
    day = None
    for scope in (line[:month_m.start()], line[month_m.end():]):
        dm = re.search(r"\b(\d{1,2})\??(?:st|d|th)?\b", scope)
        if dm and 1 <= int(dm.group(1)) <= 31:
            # Skip if it's the start of a 4-digit year.
            if not re.match(r"\d{2}\d", scope[dm.start():dm.start()+4]):
                day = int(dm.group(1))
                break
    # Year: 3-6 chars that repair to a plausible year, after the month.
    year = None
    for ym in re.finditer(r"[\d\[\]()ilIogbsSaex?]{3,6}", line[month_m.end():]):
        year = _repair_year(ym.group(0))
        if year:
            break
    if day is None or not year:
        return None, None
    # Location: text before the month, minus any trailing day number.
    location = line[:month_m.start()].strip()
    location = re.sub(r",?\s*\d{1,2}\??\s*,?\s*$", "", location)
    location = location.rstrip(",").rstrip(".").strip() or None
    return location, f"{year:04d}-{month:02d}-{day:02d}"


def parse_letters(text: str, author: str, collection: str,
                  id_prefix: str) -> list[dict]:
    lines = text.splitlines()
    docs: list[dict] = []
    i, n = 0, len(lines)
    idx = 0
    while i < n:
        line = clean_text(lines[i].strip())
        m = _TO_HEADER.match(line)
        if not m:
            i += 1
            continue
        recipient = clean_text(m.group(1)).strip().title()
        # Dateline: first non-empty line after header, skipping source
        # citations like "D. OF S. MSS. INSTR." / "MAD. MSS."
        j = i + 1
        location, date_str = None, None
        skips = 0
        while j < n and skips < 3:
            line_j = lines[j].strip()
            if not line_j:
                j += 1
                continue
            if "MSS." in clean_text(line_j).upper() and len(line_j) < 40:
                j += 1
                skips += 1
                continue
            location, date_str = parse_dateline(lines[j])
            if date_str:
                j += 1
            break
        # Body until next TO header.
        k = j
        body_lines: list[str] = []
        while k < n:
            if _TO_HEADER.match(clean_text(lines[k].strip())):
                break
            body_lines.append(lines[k])
            k += 1
        body = clean_text("\n".join(body_lines).strip())
        body = re.sub(r"\n{3,}", "\n\n", body)
        if len(body) >= 300 and date_str:
            idx += 1
            docs.append({
                "document_id": f"{id_prefix}-{idx:05d}",
                "author": author,
                "date": date_str,
                "recipient": recipient,
                "location": location,
                "collection": collection,
                "corpus_layer": "Writings",
                "title": f"{author} to {recipient}, {date_str}",
                "full_text": body,
                "ocr_source": True,
            })
        i = k if k > i else i + 1
    return docs


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest IA OCR letters")
    parser.add_argument("--inputs", nargs="+", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--author", required=True)
    parser.add_argument("--collection", required=True)
    parser.add_argument("--id-prefix", required=True)
    args = parser.parse_args()

    all_docs: list[dict] = []
    for path_str in args.inputs:
        text = Path(path_str).read_text(encoding="utf-8", errors="replace")
        docs = parse_letters(text, args.author, args.collection,
                             args.id_prefix)
        print(f"  {path_str}: {len(docs)} letters", file=sys.stderr)
        all_docs.extend(docs)

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        for d in all_docs:
            f.write(json.dumps(d, ensure_ascii=False) + "\n")
    print(f"Wrote {len(all_docs)} documents to {out}", file=sys.stderr)


if __name__ == "__main__":
    main()
