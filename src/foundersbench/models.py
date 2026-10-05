"""Domain models for Founders Bench."""

from __future__ import annotations

from datetime import datetime
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class BenchMode(str, Enum):
    ONE_ON_ONE = "one_on_one"      # click portrait, converse
    BRIEF_AND_ASK = "brief_and_ask"  # user supplies modern facts
    FULL_BENCH = "full_bench"      # all agents deliberate


class FounderAgent(BaseModel):
    """An AI agent embodying a historical figure."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    era: str = "Founding"  # Founding, Reconstruction, ...
    role: str = ""  # Framer, Anti-Federalist, Justice, ...
    affiliation: str = ""  # Federalist, Anti-Federalist, ...
    portrait_path: str = ""
    corpus_collections: list[str] = Field(default_factory=list)
    system_prompt: str = ""  # built from corpus metadata, not hardcoded


class HistoricalDocument(BaseModel):
    """A single citable document: letter, speech, pamphlet, legal authority."""

    document_id: str
    author: str
    date: datetime | None = None
    recipient: str | None = None  # for letters
    collection: str = ""  # Founders Online, Elliot's Debates, ...
    corpus_layer: str = ""  # Writings, PrintCulture, LegalAuthority
    title: str = ""
    full_text: str = ""

    @property
    def citation_label(self) -> str:
        if self.corpus_layer == "LegalAuthority":
            return self.title
        if self.date:
            d = self.date.strftime("%B %-d, %Y")
            return f"{d} letter to {self.recipient}" if self.recipient else f"{d} — {self.title}"
        return self.title


class Citation(BaseModel):
    document_id: str
    label: str
    quoted_text: str


class BenchTurn(BaseModel):
    speaker_id: str  # agent id or "user"
    speaker_name: str
    text: str
    citations: list[Citation] = Field(default_factory=list)
    is_fallback: bool = False  # provider unreachable; cf. Verdict labeling
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class BenchSession(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    mode: BenchMode
    era: str = "Founding"
    user_question: str
    briefing_context: str | None = None  # Mode 2: modern facts from user
    participants: list[FounderAgent] = Field(default_factory=list)
    transcript: list[BenchTurn] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
