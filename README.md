# Claims Assistant — Principal Life Insurance

AI chatbot for life insurance, built on a **real policy document**
(Principal Life, Group Policy GL S655). The brief allows combining its focus
areas; this solution **covers all three**, with emphasis on 1 and 2:

| Option | Focus | How it's covered |
|---|---|---|
| **1** | Claims Processor | Extracts data from uploaded claims (PDF/DOCX/JSON), validates and flags missing fields |
| **2** | Fraud Detection | Detects fraud across 3 layers and **explains** each alert citing its source |
| **3** | Policy Manager | Chatbot that answers questions about terms, coverage and exclusions |

## Features

- **RAG/CAG chatbot** over the policy, with page citations and an "I can't find
  this in the policy" fallback (anti-hallucination).
- **Claim processing**: extraction into a typed schema (Pydantic) + validation.
- **3-layer fraud detection**, all explainable:
  1. **Policy rules** (deterministic code anchored to real clauses).
  2. **Historical analysis** (statistics: duplicates, frequency, z-score).
  3. **Semantic analysis** (embeddings: similar narratives).
- **Orchestrated with LangGraph**; the model **never decides** whether something
  is fraud (rules do), it only **reads** the document and **explains** the alerts.

## Installation and usage

**Requirements:** Python 3.10+. **No ChromaDB account needed** — it runs locally
(the first run only downloads an ~80 MB embedding model, no credentials required).

### 1) Install

```bash
git clone https://github.com/karisaylema/insurance-assistant.git
cd insurance-assistant
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2) Add the policy PDF (required, not included)

Place a life insurance policy PDF in `data/policy/` (see [data/policy/README.md](data/policy/README.md)).
This case used the **Principal Life — Group Policy GL S655** sample; the values in
`insurance_assistant/domain/policy.py` (`POLICY_FACTS`) are calibrated to that policy.

### 3) Choose a model — two options

```bash
cp .env.example .env      # then edit .env based on the option you pick
```

**Option A — Claude API** (recommended). You'll need an Anthropic API key:
1. Go to <https://console.anthropic.com> → **Settings → Billing** and add credit (from ~$5).
2. **Settings → API Keys → Create Key**, copy the key (`sk-ant-...`).
3. In `.env`: `LLM_PROVIDER=anthropic` and `ANTHROPIC_API_KEY=sk-ant-...`
   (optionally `ANTHROPIC_MODEL=claude-sonnet-5` to reduce cost).

> A Claude.ai subscription (Pro/Max) does **not** grant API access; the API is billed separately.

**Option B — Ollama, local and free** (no API key). Ideal if you don't have an Anthropic account:
1. Install Ollama from <https://ollama.com> and pull a model: `ollama pull llama3.1`
2. `pip install langchain-ollama`
3. In `.env`: `LLM_PROVIDER=ollama`

### 4) Run

```bash
streamlit run app.py      # opens the app (chat + claim review)
pytest                    # rule tests (no model or network required)
```

### Notes for evaluators
- **ChromaDB**: local by default (`CHROMA_MODE=local`); no account or credentials needed.
- **Fraud detection does not depend on the model**: the flags and the decision are
  deterministic code. The model (option A or B) is only used for the chatbot, document
  extraction, and to **write** the explanation behind the alerts.
- The policy is **cached in the prompt** by default (`POLICY_MODE=cached`), so no
  indexing is required. For `rag`/`hybrid`: `python -m insurance_assistant.retrieval.ingest`.
- The history uses included **synthetic** data (`data/history/`), regenerable with
  `python -m scripts.generate_history`.

## Sample claims (demo)

Upload these in the "Review a claim" tab (`data/claims/`):

| File | Result | What it demonstrates |
|---|---|---|
| `claim_clean.json` | Auto-approve | consistent claim |
| `claim_fraud.json` | Reject | policy rules (amount, related physician, accused beneficiary…) |
| `claim_history_anomaly.json` | Reject | historical analysis (frequent beneficiary, amount outlier) |
| `claim_semantic.json` | Manual review | narrative semantically similar to a previous claim |

## Architecture

A context engine over the policy powers both the chatbot and the fraud reasoning.
The claim pipeline is orchestrated with LangGraph:

```
extract → validate → fraud_rules → historical_analysis → semantic_analysis
        → consolidate ─┬─(flags)→ reasoning → END
                       └─(no flags)→ auto_ok → END
```

- **extract / reasoning** use the LLM (reading the document / explaining).
- **fraud_rules / historical / semantic / consolidate** are code → the **verdict
  can't be hallucinated**.

Layered organization (the UI only talks to `application/`, `domain/` has no
external dependencies):

```
insurance_assistant/
├── settings.py         Typed config (Pydantic)
├── domain/             Pure business logic: POLICY_FACTS, Pydantic schemas
├── llm/                Model factory (Claude/Ollama) + prompt caching
├── documents/          PDF/DOCX loading + claim extraction
├── retrieval/          ChromaDB (local/cloud), context strategies, narratives
├── fraud/               rules · anomaly · semantic · scoring · history
├── agent/               LangGraph graph
└── application/         Use cases (chat_service, claim_service)
app.py                  Streamlit UI
tests/                  pytest
```

### Context strategy (`POLICY_MODE`)

The policy (~30K tokens) fits in context, so there are three interchangeable modes:

| Mode | How | When |
|---|---|---|
| `cached` (default) | full policy cached (prompt caching) | 1 policy; maximum accuracy |
| `hybrid` | RAG selects pages → loads the full pages | balance; scales better |
| `rag` | retrieves chunks from ChromaDB | large corpus |

## Design decisions

- **Rules for the verdict, LLM for reading/explaining.** Fraud is decided with
  deterministic code (auditable, testable, hallucination-free, immune to document
  injection); the LLM extracts data and writes the reasoning.
- **Statistics for numbers, embeddings for meaning.** History is compared with
  z-scores/counts; similar narratives, with embeddings (ChromaDB). The semantic
  signal is **soft** (low weight → review, never a rejection on its own).
- **CAG with caching** instead of RAG for a single small policy: more accuracy
  with no retrieval-miss risk; RAG/hybrid remain available to scale.
- **Patterns**: Strategy (context modes), Factory/registry (LLM provider),
  layers + SRP, Pydantic Settings.

## Stack

Python · Streamlit · LangGraph · Claude (Anthropic) via `langchain-anthropic` ·
ChromaDB · Pydantic · pytest.
