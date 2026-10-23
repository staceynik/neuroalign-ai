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
The map must communicate the logical structure of the source, not merely
place all concepts around a central heading.

SOURCE-GROUNDED STRUCTURE:
Use content analysis as a structural hint, not as unquestionable truth.
Use transformed content as the primary source for verifying concepts and relations.
Preserve the source language.

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

STRUCTURE AND LAYOUT RULES:
- Use one main root node for the lesson's main topic.
- For concept_group, create meaningful intermediate branches when the source
  supports them. Do not connect every concept directly to the root.
- Use content blocks to identify the overall topic and possible groupings.
  A single content block containing many concepts does not mean that all
  concepts must be direct children of the root.
- Prefer 3-5 meaningful branches where supported by the source.
- Keep the map compact, ideally no more than 2 levels below the root.
- Group concepts by explicit meaning or function in the source.
- Do not invent category nodes just to make the layout look balanced.
- If the source does not support meaningful subgroups, use a simple root
  with direct concept children rather than fabricating a hierarchy.
- Avoid long horizontal chains and excessive width.
- Use short labels and valid Mermaid syntax.

RELATION RULES:
- Treat the listed relations as candidate relations, not guaranteed facts.
- Include a relation only when it is supported by the transformed content
  or by the supplied source excerpts.
- Do not infer that one concept is an example of another unless the source
  explicitly supports that classification.
- Do not convert similarity, contrast, or thematic association into causation.
- Use relation labels only when they add useful information.
- Do not draw a second edge between concepts already connected in a way
  that communicates the same relationship.
- Do not connect every concept to the root if the hierarchy already makes
  its membership clear.
- Preserve important distinctions and do not omit key concepts merely
  to reduce the diagram size.
- Do not invent concepts, categories, explanations, or causal relationships.

STRUCTURE TYPE GUIDANCE:
- hierarchy: show supported parent-child relationships.
- sequence: preserve the source order.
- comparison: make compared items and dimensions easy to distinguish.
- causal: show only explicitly supported cause-and-effect links.
- concept_group: group related concepts only when the source supports
  the grouping; otherwise use a compact flat overview.
- mixed: combine structures only where the source supports them.
- unclear: use a simple overview without inventing relationships.

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


