"""Founder agent orchestration: retrieval → generation → citation extraction.

Recommended model: Claude Sonnet (citation discipline, persona without
caricature, analogical reasoning for brief-and-ask mode).
"""

from __future__ import annotations

from foundersbench.models import BenchSession, BenchTurn, Citation, FounderAgent
from foundersbench.retrieval import CorpusIndex

FALLBACK_LABEL = "[Default response: API key missing or unavailable] "

SYSTEM_PROMPT_TEMPLATE = """\
You are {name}, {role}. You speak in first person, in a voice consistent with \
your writings, but you never invent documents.

You have been provided with excerpts from historical documents. You may ONLY \
cite documents from the provided excerpts. Every substantive claim must cite \
a specific document by its citation label.

If the excerpts contain no relevant document, say so plainly: \
"I have no letter or writing on that subject in the materials provided." \
Never improvise a citation.

{briefing}
"""


class FounderAgentService:
    def __init__(self, index: CorpusIndex, provider):
        self.index = index
        self.provider = provider  # BYOK LLM client (Anthropic, OpenAI, ...)

    def _build_system_prompt(self, agent: FounderAgent, session: BenchSession) -> str:
        briefing = ""
        if session.briefing_context:
            briefing = (
                "The user has briefed you on modern facts you never encountered "
                f"in your lifetime:\n{session.briefing_context}\n"
                "Apply your principles to these facts. Do not pretend you knew them."
            )
        return SYSTEM_PROMPT_TEMPLATE.format(
            name=agent.name, role=agent.role, briefing=briefing
        )

    async def respond(
        self,
        agent: FounderAgent,
        session: BenchSession,
        user_message: str,
    ) -> BenchTurn:
        # 1. Retrieve
        scored = self.index.retrieve(user_message, agent, top_k=10)
        # TODO: optional Haiku rerank stage here

        if not scored:
            return BenchTurn(
                speaker_id=agent.id,
                speaker_name=agent.name,
                text="I have no letter or writing on that subject in the materials provided.",
            )

        # 2. Generate (TODO: wire provider call with system prompt + excerpts)
        # 3. Extract citations (TODO: parse quoted passages back to document IDs)
        raise NotImplementedError("provider wiring pending")
