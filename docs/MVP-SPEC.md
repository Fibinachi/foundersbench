# Founders Bench — MVP Specification

**Version:** 0.1 (draft)
**Date:** 2026-10-04
**Status:** In development

---

## 1. Vision

An AI system that answers constitutional questions from the perspective of the founding generation, grounded in their actual writings and the print culture they inhabited. The governing theory is **original public meaning**: the Constitution's words mean what they meant to the people who ratified them.

This is not a chatbot in a powdered wig. It is a corpus-grounded research tool for lawyers, scholars, and students.

---

## 2. MVP Scope

**Era:** Founding (1787–1791)
**Coverage:** Constitution + Bill of Rights
**Flagship use case:** Criminal procedure (4th, 5th, 6th, 8th Amendments)

Out of scope for MVP: Reconstruction bench, later amendments, non-criminal provisions (covered by architecture, built later).

---

## 3. Figures (Founding-Era Bench)

### Federalists / Framers
| Figure | Corpus strengths | Notes |
|---|---|---|
| James Madison | Convention notes, Federalist Papers, letters | Primary drafter; 4th Amendment author |
| Alexander Hamilton | Federalist Papers, Treasury writings, letters | Broad federal power; will disagree with Jefferson |
| John Adams | Diary, letters, Defence of the Constitutions | Witnessed Otis v. writs of assistance (1761) |
| Thomas Jefferson | 19,000+ letters, Notes on Virginia | In France during Convention; strong Anti-Federalist sympathy on Bill of Rights |
| George Washington | Letters, Farewell Address | Sparse writer; lower resolution agent |
| Benjamin Franklin | Letters, Poor Richard, Convention speeches | Elder statesman; pragmatic voice |

### Anti-Federalists (essential for honest originalism)
| Figure | Corpus strengths | Notes |
|---|---|---|
| George Mason | Virginia Declaration of Rights, objections | Author of the Virginia Declaration; refused to sign |
| Patrick Henry | Speeches (reconstructed), letters | Virginia ratification debates |
| "Brutus" | Anti-Federalist Papers | Most systematic Anti-Federalist constitutional theory |
| "Federal Farmer" | Letters | Moderate Anti-Federalist; Bill of Rights advocate |

---

## 4. Corpus Layers

### Layer 1: Founders' writings
- Source: Founders Online (founders.archives.gov)
- Content: Letters, papers, speeches, diaries
- Metadata required: date, author, recipient, collection, document ID

### Layer 2: Print culture
- Ratification debates (Elliot's Debates)
- Newspapers (1787–1791)
- Pamphlets (Federalist + Anti-Federalist)
- Sermons (election sermons, fast-day sermons — major political genre)

### Layer 3: Early legal authority
- Blackstone's Commentaries (1765–1769) — the founders' law school
- Coke's Institutes
- Early Supreme Court: Jay through Marshall courts
- Kent's Commentaries, Story's works
- State court decisions (1780s–1790s)

---

## 5. Interaction Modes

### Mode 1: 1:1 Conversation
User clicks a founder's portrait (Sid Meier's Colonization model) and converses. Agent speaks in first person, cites specific documents: *"In my May 18, 1790 letter to [recipient], I wrote..."*

### Mode 2: Brief and Ask
User supplies modern factual context the founders never encountered (silicon wafers, Flock cameras, thermal imaging). Agent applies period principles to the briefed facts. The user provides facts; the agent provides principles.

### Mode 3: Full Bench
User poses a question to the entire bench. Agents deliberate — including genuine disagreement (Hamilton vs. Jefferson). Each cites their own corpus. Verdict's deliberation engine adapted for founder agents.

---

## 6. Citation Requirements (Non-Negotiable)

- Every substantive claim must cite a real retrieved document
- Citations include: author, date, recipient (if letter), collection, document ID
- **Hallucinated citations are a correctness failure.** An agent that invents a letter destroys trust permanently.
- Source viewer: clicking a citation displays the original document text
- If the corpus has no relevant document, the agent must say so — not improvise

---

## 7. Technical Architecture

### BYOK Model
User brings their own API keys. Multi-provider support (same abstraction as Verdict).

### Recommended Model
**Claude Sonnet** — best citation discipline, persona without caricature, analogical reasoning for brief-and-ask mode.

Supported: OpenAI, Gemini, DeepSeek, Grok, Ollama (local).

### Retrieval Pipeline
1. **BM25 + metadata index** (free, deterministic) → top candidates. Pre-indexed; zero API cost. Well-suited to precise 18th-century legal vocabulary.
2. **Optional Haiku rerank** — semantic refinement for conceptual queries
3. **Sonnet generation** — grounded response with mandatory citations

Default: stages 1 + 3. User's only API spend is the final generation.

### Anti-Hallucination Measures
- Retrieval metadata passed through to generation prompt
- System prompt constrains agent to cite only retrieved documents
- Explicit "no relevant document" response when retrieval is empty
- (Future: citation verification pass against source text)

---

## 8. UI Concept

Visual bench: founder portraits in a row. Click to converse (Mode 1). "Brief the bench" input for Mode 2. "Full bench" button for Mode 3 deliberation. Source documents shown alongside chat; citations clickable.

---

## 9. Licensing

PolyForm Noncommercial 1.0.0, 14QBD273 LLC as licensor. Same as Verdict. Commercial use (including legal-services-for-a-fee) requires a separate license.

---

## 10. Roadmap

- [ ] MVP: Founding-era bench, Bill of Rights, criminal procedure focus
- [ ] Corpus ingestion: Founders Online + Elliot's Debates + Blackstone
- [ ] Three interaction modes
- [ ] Citation-grounded generation with source viewer
- [ ] Reconstruction bench (13th/14th/15th Amendments)
- [ ] SaaS evaluation (post-alpha, demand-dependent)

---

## 11. Rip — The Translator Agent

**Role:** Translates modern user input into period-accessible concepts for the founder agents.

**The problem:** Users cannot be expected to explain a Flock camera in 1791 terms. The briefing input needs an intermediary.

**The character:** Rip Van Winkle — Washington Irving's sleeper who fell asleep under King George and woke up under the Constitution. A man out of time, catching up. Not a historical figure (no corpus, no hallucination risk), but a period voice who bridges the gap.

**Pipeline:**
1. User types modern input: "Flock cameras track everyone's location"
2. Rip translates to period concepts: silhouette portraits, post roads, constables, central repositories
3. Founder agent receives the translated briefing and reasons from their principles

**UX label:** "Ask Rip to explain it to the bench."

**Design notes:**
- Rip can ask clarifying questions when input is ambiguous
- Rip is not citable (no corpus) — he is infrastructure, not a bench member
- The translation itself is a prompt engineering task worth getting right;
  consider example briefings for common technologies
