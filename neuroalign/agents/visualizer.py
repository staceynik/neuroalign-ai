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

Create a clear, compact conceptual map for educational content.

For Attention Support:
- Put the main topic at the top.
- Organize the map into 4-6 meaningful main branches when appropriate.
- Prefer a maximum of 2 levels below the main topic in the overview.
- Group related concepts instead of creating long chains of nodes.
- Avoid duplicate concepts and redundant intermediate nodes.
- Show only relationships supported by the source content.
- Preserve the distinction between theories, practices, historical criticism,
  and later developments.
- Attribute historical claims to the person who held them.
- Use concise Italian labels when the source is in Italian.
- Optimize for readability and a complete, compact overview, not maximum detail.
- Do not invent future research, consequences, or causal relationships.
- If the map becomes too large, prioritize the main relationships and leave
  secondary details to the accompanying text.

Return valid Mermaid.js diagram code without Markdown fences.
Do not add unsupported content.

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
    result: VisualizerOutput = llm.with_structured_output(VisualizerOutput).invoke(
        VISUALIZER_PROMPT.format(
            modes=str(profile.get("modes", [])),
            visual_support=profile.get("visual_support", "medium"),
            transformed=state["transformed_output"]["text"],
        )
    )

    return {
        "final_markdown": state["transformed_output"]["text"],
        "mermaid_diagram": result.mermaid_diagram
}
