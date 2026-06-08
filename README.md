# NeuroAlign AI

NeuroAlign AI is a thesis proof of concept for adaptive cognitive accessibility.
It transforms complex text into clearer, more structured, and more usable formats
through a multi-agent AI pipeline.

The project is not a diagnostic tool. Users choose support modes, not clinical
labels.

## Support Modes

- **Attention Support**: short summary, action checklist, priorities, reduced noise.
- **Reading Support**: shorter sentences, visual spacing, TTS-ready chunks.
- **Explicit Structure**: facts, assumptions, rules, IF/THEN logic, tables.
- **Numerical Reasoning**: numerical data explained with analogies and chart-ready JSON.

## Architecture

```text
Streamlit UI          FastAPI / n8n
      \                  /
       \                /
        Shared Runner
             |
       LangGraph Pipeline
             |
 Profiler -> Analyzer -> Transformer -> Visualizer
             |
  Markdown / Mermaid / Metrics / Cost Summary
```

## Data Layers

NeuroAlign AI separates personalization memory from research data.

- **ChromaDB** stores local preference summaries only when memory consent is enabled.
- **SQLite research database** stores anonymous research rows only after explicit research consent and feedback submission.
- The original text is not stored in the research dataset.
- Cost logs are stored separately and do not include raw user text.

## Cost Tracking

The app tracks token usage and estimated API cost per LLM agent call using a
LangChain callback.

Tracked fields include:

- agent name;
- model name;
- input tokens;
- output tokens;
- total tokens;
- estimated cost in USD.

## Local Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

Add your API key to `.env`:

```bash
OPENAI_API_KEY=your_key_here
```

Run the Streamlit app:

```bash
streamlit run app.py
```

Run the FastAPI server:

```bash
uvicorn api:app --reload --port 8000
```

Open API docs:

```text
http://localhost:8000/docs
```

## n8n Integration

The FastAPI layer exposes the same multi-agent pipeline for automation workflows.

Main endpoint:

```http
POST /transform
```

Example payload:

```json
{
  "text": "847 participants showed a statistically significant improvement after 12 weeks.",
  "modes": ["numerical", "structure"],
  "memory_consent": false,
  "research_consent": false,
  "metadata": {
    "source": "n8n"
  }
}
```

The included `n8n_workflow.json` can be imported into n8n as a starter workflow.

## Research Framing

This project can support exploratory analysis of readability proxies before and
after AI transformation, including sentence length, Flesch Reading Ease, grade
level, Gunning Fog Index, user-rated usefulness, and selected support mode.

These metrics are treated as readability proxies, not direct clinical measures
of cognitive load.

## Project Status

Current status: MVP stabilization.

Immediate next steps:

- run a local Streamlit smoke test;
- run a FastAPI `/transform` smoke test;
- verify n8n workflow compatibility;
- refine prompts and Italian thesis framing;
- add screenshots or demo GIF for the portfolio.

