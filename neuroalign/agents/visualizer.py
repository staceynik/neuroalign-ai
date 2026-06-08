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
    final_markdown: str = Field(
        description="Complete clean Markdown document ready for rendering."
    )
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
Take the transformed content and produce a clean distraction-free final Markdown document.
If the content describes a process, workflow, or hierarchy — add a Mermaid.js diagram.
If numerical data was translated to analogies — extract chart_data JSON.
Do not add new content. Only restructure and visualise what is already there.

Selected modes: {modes}
Visual support preference: {visual_support}

TRANSFORMED CONTENT:
{transformed}
"""

def visualizer_agent(state: NeuroAlignState) -> dict:
    profile      = state["cognitive_profile"]
    session_cost: SessionCost = state.get("session_cost")  # type: ignore
    callbacks    = [CostCallback(session_cost, "visualizer", MODEL)] if session_cost else []

    llm    = ChatOpenAI(model=MODEL, temperature=0, callbacks=callbacks)
    result: VisualizerOutput = llm.with_structured_output(VisualizerOutput).invoke(
        VISUALIZER_PROMPT.format(
            modes          = str(profile.get("modes", [])),
            visual_support = profile.get("visual_support", "medium"),
            transformed    = state["transformed_output"]["text"],
        )
    )
    return {
        "final_markdown":  result.final_markdown,
        "mermaid_diagram": result.mermaid_diagram,
        "chart_data":      None,
    }
