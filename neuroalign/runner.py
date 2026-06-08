"""
NeuroAlign AI — Shared Core Runner
====================================
Single entry point for the full LangGraph pipeline.
Both Streamlit (app.py) and FastAPI (api.py) call run_pipeline().

Consent rules (enforced here, never in callers):
  memory_consent   = True  → read + write ChromaDB
  research_consent = True  → caller gets back a save_research() function
                             to call ONLY after user submits feedback form.
                             Runner itself never writes research rows —
                             that prevents the double-save bug.

Cost tracking: SessionCost is passed through LangGraph state so each
agent's CostCallback can call session_cost.add() with real token counts.
"""

import uuid
import time
from dataclasses import dataclass, field
from typing import Optional, Callable

from neuroalign.graph import build_graph
from neuroalign.memory.vector_store import retrieve_memory, save_memory
from neuroalign.metrics import measure, compare
from neuroalign.cost_tracker import SessionCost, log_cost


_graph = None

def _get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph


@dataclass
class PipelineInput:
    text:             str
    modes:            list
    reading_density:  str  = "low"
    structure_level:  str  = "high"
    visual_support:   str  = "high"
    memory_consent:   bool = False
    research_consent: bool = False
    demographics:     dict = field(default_factory=dict)
    session_id:       Optional[str] = None
    source:           str = "streamlit"


@dataclass
class PipelineOutput:
    session_id:       str
    status:           str
    final_markdown:   str
    mermaid_diagram:  Optional[str]
    chart_data:       Optional[dict]
    content_analysis: dict
    readability:      dict
    cost:             dict
    duration_seconds: float
    save_research:    Optional[Callable] = None  # call this after feedback form
    error:            Optional[str] = None


def run_pipeline(inp: PipelineInput) -> PipelineOutput:
    session_id   = inp.session_id or str(uuid.uuid4())
    session_cost = SessionCost()
    t_start      = time.time()

    # 1. Memory read (consent-gated)
    retrieved_memory = []
    if inp.memory_consent:
        try:
            retrieved_memory = retrieve_memory(inp.text)
        except Exception:
            pass

    # 2. Readability BEFORE
    metrics_before = measure(inp.text)

    # 3. Build state — session_cost travels through the graph
    #    so CostCallback in each agent can record real token counts
    initial_state = {
        "session_id":       session_id,
        "session_cost":     session_cost,
        "raw_input":        inp.text,
        "selected_modes":   inp.modes,
        "user_controls": {
            "reading_density": inp.reading_density,
            "structure_level": inp.structure_level,
            "visual_support":  inp.visual_support,
            "tone":            "clear, respectful, neurodiversity-affirming",
        },
        "retrieved_memory": retrieved_memory,
    }

    # 4. Run pipeline
    try:
        result = _get_graph().invoke(initial_state)
    except Exception as e:
        return PipelineOutput(
            session_id=session_id, status="error",
            final_markdown="", mermaid_diagram=None, chart_data=None,
            content_analysis={}, readability={}, cost={},
            duration_seconds=round(time.time() - t_start, 2),
            error=str(e),
        )

    # 5. Readability AFTER
    final_md      = result.get("final_markdown", "")
    metrics_after = measure(final_md)
    readability   = compare(metrics_before, metrics_after)
    readability["profile"]   = str(inp.modes)
    readability["intensity"] = inp.structure_level

    # 6. Cost log (not personal data — always persisted)
    log_cost(session_id, session_cost)
    cost_summary = {
        "total_usd":            session_cost.total_cost,
        "total_tokens":         session_cost.total_tokens,
        "per_agent":            session_cost.calls,
        "most_expensive_agent": session_cost.most_expensive_agent,
    }

    # 7. Memory write (consent-gated)
    if inp.memory_consent:
        try:
            save_memory(
                text=f"Modes: {inp.modes}. Density: {inp.reading_density}. Source: {inp.source}.",
                metadata={"type": "preference", "session_id": session_id}
            )
        except Exception:
            pass

    # 8. Research save — return a callable, NOT called here.
    #    Streamlit calls it only after user submits the feedback form.
    #    API callers receive it but should ignore it (research_consent=False by default).
    save_research_fn = None
    if inp.research_consent and inp.demographics:
        def _save(subjective_usefulness: int = 3, open_feedback: str = ""):
            from neuroalign.research_db import save_session
            save_session(
                demographics          = inp.demographics,
                metrics_delta         = readability,
                document_type         = result.get("content_analysis", {}).get("document_type", "unknown"),
                input_word_count      = metrics_before.word_count,
                subjective_usefulness = subjective_usefulness,
                open_feedback         = open_feedback,
            )
        save_research_fn = _save

    return PipelineOutput(
        session_id       = session_id,
        status           = "success",
        final_markdown   = final_md,
        mermaid_diagram  = result.get("mermaid_diagram"),
        chart_data       = result.get("chart_data"),
        content_analysis = result.get("content_analysis", {}),
        readability      = readability,
        cost             = cost_summary,
        duration_seconds = round(time.time() - t_start, 2),
        save_research    = save_research_fn,
    )
