"""Full-bench deliberation engine.

Ported from Verdict's DeliberationService (C#/.NET) as the base for
Founders Bench Mode 3: all participating agents respond to a question,
may agree or disagree, each citing their own corpus.

Key differences from Verdict:
- Agents are founders, not jurors. No verdict lean; positions are
  interpretive stances that may converge or diverge.
- Each agent retrieves from their OWN corpus collections.
- Influence dynamics differ: founders persuade by citation and
  reasoning, not conformity pressure. (Design decision: start without
  Verdict's conformity-influence model; add if needed.)
- Fallback labeling preserved: canned responses are tagged, not silent.
"""

from __future__ import annotations

import random

from foundersbench.models import BenchSession, BenchTurn, FounderAgent

FALLBACK_LABEL = "[Default response: API key missing or unavailable] "

# Canned fallback templates. Labeled, never silent.
# cf. Verdict DeliberationService.GenerateFallbackStatement
FALLBACK_TEMPLATES = [
    "I do not have sufficient materials before me to give a grounded answer.",
    "On the documents provided, I cannot speak with confidence to this question.",
    "I would need to consult my papers further before offering a view.",
]


class BenchDeliberationService:
    """Orchestrates multi-agent deliberation rounds."""

    def __init__(self, agent_service):
        # agent_service: FounderAgentService (respond method)
        self.agent_service = agent_service

    async def deliberate(
        self,
        session: BenchSession,
        max_rounds: int = 3,
    ) -> list[BenchTurn]:
        """Run deliberation: each agent responds in turn, seeing prior turns."""
        all_turns: list[BenchTurn] = []
        participants = self._get_deliberating_agents(session)

        for round_num in range(max_rounds):
            for agent in self._select_speaking_order(participants, session):
                turn = await self._execute_turn(agent, session, all_turns)
                all_turns.append(turn)
                session.transcript.append(turn)

            if self._is_deliberation_complete(session, all_turns):
                break

        return all_turns

    # ------------------------------------------------------------------
    # Turn execution (cf. Verdict DeliberationService.ExecuteTurnAsync)
    # ------------------------------------------------------------------

    async def _execute_turn(
        self,
        agent: FounderAgent,
        session: BenchSession,
        history: list[BenchTurn],
    ) -> BenchTurn:
        """One agent takes a turn: see history, retrieve, respond."""
        try:
            # Build prompt with deliberation history so the agent can
            # respond to (or rebut) prior speakers
            turn = await self.agent_service.respond_with_history(
                agent, session, history
            )
            return turn
        except Exception:
            # Provider unreachable: labeled fallback, never silent
            return BenchTurn(
                speaker_id=agent.id,
                speaker_name=agent.name,
                text=FALLBACK_LABEL + random.choice(FALLBACK_TEMPLATES),
                is_fallback=True,
            )

    # ------------------------------------------------------------------
    # Speaker selection (cf. Verdict DeliberationService.SelectNextSpeaker)
    # ------------------------------------------------------------------

    def _get_deliberating_agents(self, session: BenchSession) -> list[FounderAgent]:
        return session.participants

    def _select_speaking_order(
        self,
        participants: list[FounderAgent],
        session: BenchSession,
    ) -> list[FounderAgent]:
        """Order speakers for a round.

        Default: stable order, but consider seniority/role weighting —
        e.g., Madison speaks first on constitutional questions, Hamilton
        responds. Override for era-specific conventions.
        """
        # TODO: role-weighted ordering (cf. Verdict's influence-weighted selection)
        return list(participants)

    # ------------------------------------------------------------------
    # Completion (cf. Verdict DeliberationService.IsDeliberationComplete)
    # ------------------------------------------------------------------

    def _is_deliberation_complete(
        self,
        session: BenchSession,
        turns: list[BenchTurn],
    ) -> bool:
        """Stop when agents converge, repeat themselves, or hit max rounds.

        For founders (not jurors), 'complete' is fuzzier than a verdict vote.
        Heuristics: all agents have spoken twice with no new citations introduced,
        or explicit consensus language detected.
        """
        # TODO: implement convergence detection
        # Placeholder: never early-stop in v0.1; rely on max_rounds
        return False

    # ------------------------------------------------------------------
    # Prompt construction (cf. Verdict DeliberationService.BuildDeliberationPrompt)
    # ------------------------------------------------------------------

    def build_deliberation_prompt(
        self,
        agent: FounderAgent,
        session: BenchSession,
        history: list[BenchTurn],
    ) -> str:
        """Build the prompt for an agent's deliberation turn, including
        prior speakers' statements so they can agree, disagree, or rebut."""
        lines = [
            f"The question before the bench: {session.user_question}",
            "",
            "Prior speakers:",
        ]
        for turn in history:
            if turn.speaker_id == agent.id:
                continue
            lines.append(f"\n{turn.speaker_name}: {turn.text}")
        lines += [
            "",
            f"{agent.name}, respond to the question and to your fellow bench members. "
            "Agree or disagree as your principles dictate. Cite your sources.",
        ]
        return "\n".join(lines)
