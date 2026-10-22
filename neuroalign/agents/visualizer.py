"""
Visualizer Agent
================
Takes transformed text and produces final Markdown, optional Mermaid
diagram, and optional chart_data JSON. Uses Pydantic structured output.
Cost is tracked via CostCallback.
"""

from typing import Optional
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from neuroalign.state import NeuroAlignState
from neuroalign.cost_tracker import CostCallback, SessionCost

MODEL = "gpt-4o-mini"

class VisualizerOutput(BaseModel):
    mermaid_diagram: Optional[str] = Field(
        default=None,
        description="Valid Mermaid.js diagram code (no fences) if the content has "
                    "a process, sequence, or hierarchical structure. Null otherwise."
    )
    """ chart_data: Optional[dict] = Field(
        default=None,
        description='JSON for chart rendering: {"data_points":[{"label","value","unit","analogy"}]}. Null if not applicable.'
    ) """


VISUALIZER_PROMPT = """You are NeuroAlign AI's visual output specialist.

Create a compact, readable conceptual map for educational content.
The map should help the reader understand the lesson's structure at a glance.

SOURCE-GROUNDED STRUCTURE:
Use the content analysis as the primary structural specification.
Use transformed content to clarify labels and preserve the source language.

Detected document type:
{document_type}

Detected map structure:
{map_structure_type}

CONCEPTS:
{concepts}

RELATIONS:
{relations}

CONTENT BLOCKS:
{content_blocks}

MAP DESIGN:
- Put the main topic at the top when the structure supports a central topic.
- Prefer 3-5 main branches when appropriate.
- Keep the overview compact, with no more than 2 levels below the main topic where possible.
- Use content blocks as grouping guidance, not mandatory categories.
- Preserve meaningful distinctions between concepts.
- Do not force a hierarchy onto a comparison, sequence, or concept-group structure.
- For concept_group, organize related concepts into compact clusters.
- For hierarchy, show supported parent-child relationships.
- For sequence, preserve the source order.
- For comparison, make compared items and dimensions easy to distinguish.
- For causal, show only explicitly supported cause-and-effect links.
- For mixed, combine structures only where the source supports them.
- For unclear, use a simple overview without inventing relationships.
- Keep labels short and use the source language.
- Do not invent concepts, categories, explanations, or causal relationships.
- Do not add every detail from the text; prioritize the key concepts.
- Do not omit key concepts merely to make the diagram smaller.
- Avoid long horizontal chains and excessive width.
- Use valid Mermaid syntax.

OUTPUT:
Return valid Mermaid.js diagram code without Markdown fences.
Do not include explanations outside the diagram.

Selected modes: {modes}
Visual support preference: {visual_support}

TRANSFORMED CONTENT:
{transformed}
"""

def visualizer_agent(state: NeuroAlignState) -> dict:
    profile = state["cognitive_profile"]
    modes = profile.get("modes", [])

# These modes already produce their final output in the Transformer.
# Skip the second LLM pass to preserve formatting and reduce latency.
    if any(mode in modes for mode in ["reading", "numerical", "structure"]):
        return {
            "final_markdown": state["transformed_output"]["text"],
            "mermaid_diagram": None,
        }

    session_cost: SessionCost = state.get("session_cost")
    callbacks    = [CostCallback(session_cost, "visualizer", MODEL)] if session_cost else []

    llm = ChatOpenAI(model=MODEL, temperature=0, callbacks=callbacks)
    
    content_analysis = state.get("content_analysis", {})
    print("=== VISUALIZER STRUCTURE ===", flush=True)
    print({k: content_analysis.get(k) for k in ("map_structure_type", "content_blocks")}, flush=True)

    result: VisualizerOutput = llm.with_structured_output(VisualizerOutput).invoke(
        VISUALIZER_PROMPT.format(
            modes=str(profile.get("modes", [])),
            visual_support=profile.get("visual_support", "medium"),
            document_type=content_analysis.get("document_type", "unknown"),
            map_structure_type=content_analysis.get("map_structure_type", "unclear"),
            concepts=str(content_analysis.get("concepts", [])),
            relations=str(content_analysis.get("relations", [])),
            content_blocks=str(content_analysis.get("content_blocks", [])),
            transformed=state["transformed_output"]["text"],
        )
    )

    return {
        "final_markdown": state["transformed_output"]["text"],
        "mermaid_diagram": result.mermaid_diagram,
    }


