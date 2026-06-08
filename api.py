"""
NeuroAlign AI — FastAPI REST Layer
====================================
Exposes the LangGraph pipeline as a clean REST API.
All pipeline logic is in neuroalign/runner.py — this file only
handles HTTP request/response serialisation.

Run:   uvicorn api:app --reload --port 8000
Docs:  http://localhost:8000/docs

n8n integration:
  HTTP Request node → POST http://localhost:8000/transform
  Body type: JSON, fields: text, modes, memory_consent, research_consent
  Response: parse {{ $json.final_markdown }}, {{ $json.cost.total_usd }}, etc.
"""

from typing import Optional, List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv

from neuroalign.runner import run_pipeline, PipelineInput, PipelineOutput

load_dotenv()

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="NeuroAlign AI",
    description=(
        "Multi-agent cognitive accessibility transformer. "
        "Thesis PoC — not a diagnostic tool. "
        "Both memory_consent and research_consent default to False: "
        "no data is stored without explicit opt-in."
    ),
    version="0.2.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Schemas ───────────────────────────────────────────────────────────────────

class TransformRequest(BaseModel):
    text: str = Field(
        ...,
        min_length=10,
        description="Raw text to transform.",
        examples=["The quarterly report shows a 47% increase in user engagement..."]
    )
    modes: List[str] = Field(
        default=["attention"],
        description="attention | reading | structure | numerical"
    )
    reading_density: str  = Field(default="low",  description="very low | low | medium | high")
    structure_level: str  = Field(default="high", description="low | medium | high | very high")
    visual_support:  str  = Field(default="high", description="low | medium | high")
    memory_consent:  bool = Field(
        default=False,
        description="If true, read + write ChromaDB personalization memory."
    )
    research_consent: bool = Field(
        default=False,
        description="If true, write one anonymous row to the SQLite research dataset."
    )
    metadata: Optional[dict] = Field(
        default=None,
        description="Arbitrary caller metadata (e.g. {source: 'n8n'}). Not stored."
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "text": "847 participants showed a statistically significant improvement (p<0.05) after 12 weeks.",
                "modes": ["numerical", "structure"],
                "memory_consent": False,
                "research_consent": False,
                "metadata": {"source": "n8n"}
            }
        }
    }


class CostSummary(BaseModel):
    total_usd:    float
    total_tokens: int
    most_expensive_agent: str
    per_agent:    list


class TransformResponse(BaseModel):
    session_id:       str
    status:           str
    final_markdown:   str
    mermaid_diagram:  Optional[str]
    chart_data:       Optional[dict]
    content_analysis: dict
    readability:      dict
    cost:             dict
    duration_seconds: float


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "status": "ok",
        "version": "0.2.0",
        "pipeline": "profiler → analyzer → transformer → visualizer",
        "docs": "/docs",
    }

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/modes")
async def list_modes():
    """Returns all valid cognitive support modes. Useful for n8n dropdown."""
    return {
        "modes": {
            "attention": "Immediate summary, action checklists, priority focus, reduced noise",
            "reading":   "Line-by-line structure, plain vocabulary, TTS-ready chunks",
            "structure": "Literal language, IF/THEN rules, tables, facts vs assumptions",
            "numerical": "Numbers translated to real-world analogies, chart-ready data",
        }
    }


@app.post("/transform", response_model=TransformResponse)
async def transform(request: TransformRequest):
    """
    Main transformation endpoint.

    Consent behaviour:
      memory_consent=false   → ChromaDB is NOT read or written
      research_consent=false → SQLite research row is NOT written
      Both default to false — safe for automated / n8n calls.

    n8n usage:
      Node: HTTP Request
      Method: POST
      URL: http://localhost:8000/transform
      Body: JSON (map fields from previous nodes with expressions)
      Parse response: {{ $json.final_markdown }}, {{ $json.cost.total_usd }}
    """
    valid_modes = {"attention", "reading", "structure", "numerical"}
    invalid = set(request.modes) - valid_modes
    if invalid:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid mode(s): {invalid}. Valid: {valid_modes}"
        )

    source = "api"
    if request.metadata and request.metadata.get("source"):
        source = request.metadata["source"]

    inp = PipelineInput(
        text             = request.text,
        modes            = request.modes,
        reading_density  = request.reading_density,
        structure_level  = request.structure_level,
        visual_support   = request.visual_support,
        memory_consent   = request.memory_consent,
        research_consent = request.research_consent,
        demographics     = {},      # API callers don't submit demographics
        source           = source,
    )

    output = run_pipeline(inp)

    if output.status == "error":
        return JSONResponse(
            status_code=500,
            content={
                "session_id": output.session_id,
                "status":     "error",
                "error":      output.error,
            }
        )

    return TransformResponse(
        session_id       = output.session_id,
        status           = output.status,
        final_markdown   = output.final_markdown,
        mermaid_diagram  = output.mermaid_diagram,
        chart_data       = output.chart_data,
        content_analysis = output.content_analysis,
        readability      = output.readability,
        cost             = output.cost,
        duration_seconds = output.duration_seconds,
    )


@app.post("/transform/batch")
async def transform_batch(requests: List[TransformRequest]):
    """Transform up to 10 texts in one call. Useful for n8n loop nodes."""
    if len(requests) > 10:
        raise HTTPException(status_code=422, detail="Max 10 items per batch.")
    results = []
    for req in requests:
        result = await transform(req)
        results.append(result)
    return {"batch_size": len(results), "results": results}


@app.post("/webhook/n8n")
async def n8n_webhook(request_data: dict):
    """
    n8n Webhook trigger compatibility endpoint.
    n8n's Webhook node wraps the payload in a 'body' key.
    This endpoint unwraps it and routes to /transform.

    In n8n: use a Webhook trigger node pointing to this URL.
    Downstream nodes access results with {{ $json.final_markdown }} etc.
    """
    payload = request_data.get("body", request_data)
    try:
        req = TransformRequest(**payload)
    except Exception as e:
        raise HTTPException(status_code=422, detail=str(e))
    return await transform(req)
