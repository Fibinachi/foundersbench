"""Per-founder corpus ingest from the Founders Online API.

Uses the official National Archives / UVA Press API:
    https://founders.archives.gov/API/docdata/<project>/<doc-id>

Document IDs come from the bulk metadata file:
    https://founders.archives.gov/Metadata/founders-online-metadata.json
(behind an AWS WAF JS challenge — download in a real browser; the
`aws-waf-token` cookie it sets is also needed for API calls, passed
via --cookie-file as a Netscape-format cookie jar or raw Cookie header).

Each founder's documents are normalized to HistoricalDocument records
and written as JSONL, ready for BM25 indexing.

Metadata license: UVA Press, CC-BY-NC (noncommercial). The annotated
transcriptions are scholarly editions — cite Founders Online as the
collection and keep the permalink on every record.

Usage:
    python -m foundersbench.corpus.ingest_founders \
        --metadata data/founders-online-metadata.json \
        --founder "Madison, James" \
        --cookie-file data/waf-cookies.txt \
        --output data/founder-madison.jsonl

    # resume an interrupted run:
    python -m foundersbench.corpus.ingest_founders ... --resume
"""

from __future__ import annotations

import argparse
import http.cookiejar
import json
import sys
import time
import urllib.request
from pathlib import Path

API_BASE = "https://founders.archives.gov/API/docdata/"
PERMALINK_PREFIX = "https://founders.archives.gov/documents/"

# Polite rate: API docs ask for max 10 req/sec.
REQUESTS_PER_SECOND = 8.0

# Project slug per founder as used in permalinks/API paths.
FOUNDER_PROJECTS = {
    "Madison, James": "Madison",
    "Hamilton, Alexander": "Hamilton",
    "Jefferson, Thomas": "Jefferson",
    "Adams, John": "Adams",
}


def load_metadata(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    # File is a list of records; tolerate a {"documents": [...]} wrapper.
    if isinstance(data, dict):
        for key in ("documents", "records", "items"):
            if key in data:
                data = data[key]
                break
    return data


def api_id_for(record: dict) -> str | None:
    """Derive the API path from the record's permalink.

    Permalink: https://founders.archives.gov/documents/Adams/06-01-02-0001
    API:       https://founders.archives.gov/API/docdata/Adams/06-01-02-0001
    """
    permalink = record.get("permalink", "")
    if not permalink.startswith(PERMALINK_PREFIX):
        return None
    return permalink[len(PERMALINK_PREFIX):]


def build_opener(cookie_file: Path | None) -> urllib.request.OpenerDirector:
    opener = urllib.request.build_opener()
    opener.addheaders = [("User-Agent", "FoundersBench/0.1 (research; contact via GitHub Fibinachi/FoundersBench)")]
    if cookie_file and cookie_file.exists():
        jar = http.cookiejar.MozillaCookieJar(str(cookie_file))
        try:
            jar.load(ignore_discard=True, ignore_expires=True)
        except Exception:
            # Maybe a raw "Cookie:" header value instead of a jar.
            raw = cookie_file.read_text().strip()
            opener.addheaders.append(("Cookie", raw))
        else:
            opener.add_handler(urllib.request.HTTPCookieProcessor(jar))
    return opener


def fetch_doc(opener, api_id: str, retries: int = 3) -> dict | None:
    url = API_BASE + api_id
    for attempt in range(retries):
        try:
            req = urllib.request.Request(url)
            with opener.open(req, timeout=60) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status}")
                return json.loads(resp.read().decode("utf-8"))
        except Exception as e:
            if attempt + 1 == retries:
                print(f"  FAILED {api_id}: {e}", file=sys.stderr)
                return None
            time.sleep(2 ** attempt)
    return None


def to_document(api_id: str, payload: dict, founder: str) -> dict | None:
    content = (payload.get("content") or "").strip()
    if len(content) < 200:
        return None  # skip stubs / empty transcriptions
    authors = payload.get("authors") or []
    recipients = payload.get("recipients") or []
    title = payload.get("title") or ""
    date_from = payload.get("date-from") or None
    return {
        "document_id": f"founders-online-{api_id.replace('/', '-')}",
        "author": ", ".join(authors) if authors else founder,
        "date": date_from,
        "recipient": ", ".join(recipients) if recipients else None,
        "collection": "Founders Online",
        "corpus_layer": "Writings",
        "title": title,
        "permalink": payload.get("permalink") or (PERMALINK_PREFIX + api_id),
        "full_text": content,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest a founder's corpus from Founders Online")
    parser.add_argument("--metadata", required=True, help="Path to founders-online-metadata.json")
    parser.add_argument("--founder", required=True,
                        help='Founder author string, e.g. "Madison, James"')
    parser.add_argument("--cookie-file", default=None,
                        help="Netscape cookie jar or raw Cookie header for the WAF token")
    parser.add_argument("--output", required=True, help="Output JSONL path")
    parser.add_argument("--resume", action="store_true",
                        help="Skip document_ids already present in the output file")
    parser.add_argument("--limit", type=int, default=0,
                        help="Fetch at most N documents (0 = all)")
    args = parser.parse_args()

    founder = args.founder
    print(f"Loading metadata from {args.metadata}...", file=sys.stderr)
    records = load_metadata(Path(args.metadata))
    print(f"  {len(records)} total records", file=sys.stderr)

    # Keep documents authored by the founder with a real date
    # (undated records are nearly all modern editorial content).
    targets: list[str] = []
    for r in records:
        authors = r.get("authors") or []
        if not any(founder in a for a in authors):
            continue
        if not r.get("date-from"):
            continue
        api_id = api_id_for(r)
        if api_id:
            targets.append(api_id)
    print(f"  {len(targets)} documents authored by {founder}", file=sys.stderr)
    if args.limit:
        targets = targets[: args.limit]
        print(f"  limited to {len(targets)}", file=sys.stderr)

    out_path = Path(args.output)
    done: set[str] = set()
    if args.resume and out_path.exists():
        with out_path.open(encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["document_id"])
                except Exception:
                    pass
        print(f"  resuming: {len(done)} already fetched", file=sys.stderr)

    opener = build_opener(Path(args.cookie_file) if args.cookie_file else None)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mode = "a" if args.resume else "w"

    fetched = skipped = failed = 0
    interval = 1.0 / REQUESTS_PER_SECOND
    t0 = time.time()
    with out_path.open(mode, encoding="utf-8") as f:
        for i, api_id in enumerate(targets):
            doc_id = f"founders-online-{api_id.replace('/', '-')}"
            if doc_id in done:
                skipped += 1
                continue
            tick = time.time()
            payload = fetch_doc(opener, api_id)
            if payload is None:
                failed += 1
            else:
                doc = to_document(api_id, payload, founder)
                if doc:
                    f.write(json.dumps(doc, ensure_ascii=False) + "\n")
                    fetched += 1
                else:
                    skipped += 1
            if (i + 1) % 500 == 0:
                elapsed = time.time() - t0
                rate = (i + 1) / elapsed if elapsed else 0
                print(f"  {i + 1}/{len(targets)}  fetched={fetched} "
                      f"skipped={skipped} failed={failed}  ({rate:.1f}/s)",
                      file=sys.stderr)
            # Rate limit
            wait = interval - (time.time() - tick)
            if wait > 0:
                time.sleep(wait)

    print(f"Done: fetched={fetched} skipped={skipped} failed={failed} -> {out_path}",
          file=sys.stderr)


if __name__ == "__main__":
    main()
