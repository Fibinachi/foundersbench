"""Founder agent orchestration: retrieval -> generation -> citation extraction.

Recommended model: Claude Sonnet (citation discipline, persona without
caricature, analogical reasoning for brief-and-ask mode).

Citation discipline (non-negotiable):
- Every substantive claim must cite a retrieved document.
- Only cite documents from the retrieval results. Never improvise.
- If retrieval is empty: say so plainly, do not generate.
- Fallback output (provider unreachable) is labeled, never silent.
"""

from __future__ import annotations

import random
import re

from foundersbench.models import (
    BenchSession,
    BenchTurn,
    Citation,
    FounderAgent,
    HistoricalDocument,
)
from foundersbench.providers.base import LLMProvider, ProviderError
from foundersbench.retrieval import CorpusIndex

FALLBACK_LABEL = "[Default response: API key missing or unavailable] "

FALLBACK_TEMPLATES = [
    "I do not have sufficient materials before me to give a grounded answer.",
    "On the documents provided, I cannot speak with confidence to this question.",
    "I would need to consult my papers further before offering a view.",
]

SYSTEM_PROMPT_TEMPLATE = """\
You are {name}, {role}. You speak in first person, in a voice consistent with \
your writings, but you never invent documents.

You know only what is in the documents provided below and what the user has \
briefed you on. You do not know anything after {cutoff}.

RULES:
1. You may ONLY cite documents from the excerpts provided below. Every \
substantive claim must cite a specific document by its citation label, \
e.g. [Federalist No. 78] or [May 18, 1790 letter to James Madison].
2. If the excerpts contain no relevant document, say so plainly: \
"I have no letter or writing on that subject in the materials provided." \
Never improvise a citation. Never cite a document not listed below.
3. Quote briefly and accurately. Do not paraphrase a quote as if it were verbatim.
{briefing}
"""


def _excerpt_block(docs: list[tuple[HistoricalDocument, float]]) -> str:
    parts = []
    for doc, _score in docs:
        parts.append(
            f"--- [{doc.citation_label}] (id: {doc.document_id})\n{doc.full_text[:4000]}"
        )
    return "\n\n".join(parts)


class FounderAgentService:
    def __init__(self, index: CorpusIndex, provider: LLMProvider):
        self.index = index
        self.provider = provider

    def _build_system_prompt(
        self, agent: FounderAgent, session: BenchSession
    ) -> str:
        briefing = ""
        if session.briefing_context:
            briefing = (
                "4. The user has briefed you on modern facts you never encountered "
                f"in your lifetime:\n{session.briefing_context}\n"
                "Apply your principles to these facts. Do not pretend you knew them."
            )
        # Death-year cutoff keeps the agent honest about anachronism.
        cutoff = agent.death_year if agent.death_year else "your death"
        return SYSTEM_PROMPT_TEMPLATE.format(
            name=agent.name,
            role=agent.role or "founder",
            cutoff=cutoff,
            briefing=briefing,
        )

    def _build_user_message(
        self,
        agent: FounderAgent,
        session: BenchSession,
        user_message: str,
        docs: list[tuple[HistoricalDocument, float]],
    ) -> str:
        return (
            f"Question: {user_message}\n\n"
            f"Document excerpts:\n{_excerpt_block(docs)}\n\n"
            f"Answer as {agent.name}, citing the excerpts above."
        )

    def _extract_citations(
        self,
        text: str,
        docs: list[tuple[HistoricalDocument, float]],
    ) -> list[Citation]:
        """Pull citations back to retrieved documents.

        Matches [label] markers in the response text against the retrieved
        documents' citation labels and document IDs. Only citations that
        resolve to a retrieved document are kept — this is the
        anti-hallucination gate.
        """
        by_label = {d.citation_label.lower(): d for d, _ in docs}
        by_id = {d.document_id.lower(): d for d, _ in docs}
        by_title = {d.title.lower(): d for d, _ in docs}
        found: list[Citation] = []
        seen: set[str] = set()
        for m in re.finditer(r"\[([^\]]+)\]", text):
            key = m.group(1).strip().lower()
            doc = by_label.get(key) or by_id.get(key) or by_title.get(key)
            if not doc:
                # Substring fallback: "[Federalist No. 78]" should match
                # label "May 28, 1788 \u2014 Federalist No. 78"
                for d, _ in docs:
                    if key in d.citation_label.lower() or key in d.title.lower():
                        doc = d
                        break
            if doc and doc.document_id not in seen:
                seen.add(doc.document_id)
                # Grab a short quoted passage near the marker, if any
                quote_m = re.search(r'"([^"]{10,300})"', text[max(0, m.start() - 400):m.end() + 400])
                found.append(Citation(
                    document_id=doc.document_id,
                    label=doc.citation_label,
                    quoted_text=quote_m.group(1) if quote_m else "",
                ))
        return found

    def _fallback_turn(self, agent: FounderAgent) -> BenchTurn:
        return BenchTurn(
            speaker_id=agent.id,
            speaker_name=agent.name,
            text=FALLBACK_LABEL + random.choice(FALLBACK_TEMPLATES),
            is_fallback=True,
        )

    async def respond(
        self,
        agent: FounderAgent,
        session: BenchSession,
        user_message: str,
    ) -> BenchTurn:
        # 1. Retrieve (BM25 + metadata, free)
        scored = self.index.retrieve(user_message, agent, top_k=10)
        # TODO: optional Haiku rerank stage here

        if not scored:
            return BenchTurn(
                speaker_id=agent.id,
                speaker_name=agent.name,
                text=(
                    "I have no letter or writing on that subject "
                    "in the materials provided."
                ),
            )

        # 2. Generate
        system_prompt = self._build_system_prompt(agent, session)
        prompt = self._build_user_message(agent, session, user_message, scored)
        try:
            resp = await self.provider.generate(system_prompt, prompt)
        except ProviderError:
            return self._fallback_turn(agent)
        except Exception:
            return self._fallback_turn(agent)

        # 3. Extract citations (anti-hallucination gate)
        citations = self._extract_citations(resp.text, scored)

        return BenchTurn(
            speaker_id=agent.id,
            speaker_name=agent.name,
            text=resp.text,
            citations=citations,
        )

    async def respond_with_history(
        self,
        agent: FounderAgent,
        session: BenchSession,
        history: list[BenchTurn],
    ) -> BenchTurn:
        """Deliberation turn: agent sees prior speakers before responding."""
        # Use the session question; history is injected via the deliberation
        # service's prompt builder. Here we fold recent history into the message.
        hist_text = "\n".join(
            f"{t.speaker_name}: {t.text[:800]}" for t in history[-6:]
            if t.speaker_id != agent.id
        )
        message = session.user_question
        if hist_text:
            message += f"\n\nWhat your fellow bench members have said:\n{hist_text}"
        return await self.respond(agent, session, message)
