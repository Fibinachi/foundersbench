"""BM25 + metadata retrieval over the historical corpus.

Free, deterministic, zero API cost. Pre-indexed at ingest time.
Well-suited to precise 18th-century legal vocabulary.
"""

from __future__ import annotations

from rank_bm25 import BM25Okapi

from foundersbench.models import FounderAgent, HistoricalDocument


class CorpusIndex:
    """In-memory BM25 index with metadata faceting. Swap for persistent
    store (SQLite FTS5, Tantivy) when corpus grows."""

    def __init__(self, documents: list[HistoricalDocument]):
        self.documents = documents
        tokenized = [self._tokenize(d.full_text) for d in documents]
        self.bm25 = BM25Okapi(tokenized)

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        # TODO: period-aware tokenizer (handle long-s, archaic spelling variants)
        return text.lower().split()

    def retrieve(
        self,
        query: str,
        agent: FounderAgent,
        top_k: int = 50,
        corpus_layer: str | None = None,
    ) -> list[tuple[HistoricalDocument, float]]:
        """BM25 retrieval filtered to the agent's corpus collections."""
        allowed = set(agent.corpus_collections)
        scores = self.bm25.get_scores(self._tokenize(query))
        ranked = sorted(zip(self.documents, scores), key=lambda x: x[1], reverse=True)
        out = []
        for doc, score in ranked:
            if doc.collection not in allowed:
                continue
            if corpus_layer and doc.corpus_layer != corpus_layer:
                continue
            out.append((doc, float(score)))
            if len(out) >= top_k:
                break
        return out


# TODO: ingest pipelines
#   - Founders Online API → HistoricalDocument
#   - Elliot's Debates (ratification) → HistoricalDocument
#   - Blackstone's Commentaries → HistoricalDocument (LegalAuthority layer)
