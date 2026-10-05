# Founders Bench — Python scaffold

## Requirements

- Python 3.11+
- pip

## Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Project layout

```
src/foundersbench/
├── models/          # FounderAgent, HistoricalDocument, BenchSession, Citation
├── corpus/          # Ingest pipelines (Founders Online, Elliot's Debates, Blackstone)
├── retrieval/       # BM25 + metadata index, optional rerank
├── agents/          # Founder agent orchestration, prompt builders
├── deliberation/   # Full-bench deliberation engine
├── providers/       # BYOK LLM provider abstraction (Anthropic, OpenAI, Gemini, Ollama)
├── api/             # FastAPI (online mode)
└── cli/             # On-site CLI mode
```

## Online vs on-site

- **Online:** `uvicorn foundersbench.api:app` — FastAPI, web UI
- **On-site:** `python -m foundersbench.cli` — local CLI, same engine, no server

Both share the same retrieval + agent core. BYOK keys via environment or config menu.
