"""
Content Analyzer Agent
======================
Parses the raw input BEFORE transformation. Extracts structure so
the Transformer Agent receives clean, classified data rather than
trying to understand AND rewrite simultaneously.

Uses Pydantic structured output — no fragile string splitting.
Cost is tracked via CostCallback attached to the LLM instance.
"""

from pydantic import BaseModel, Field
from typing import List
from langchain_openai import ChatOpenAI
from neuroalign.state import NeuroAlignState
from neuroalign.cost_tracker import CostCallback, SessionCost

MODEL = "gpt-4o-mini"

class ContentAnalysis(BaseModel):
    main_topic:        str       = Field(description="One-sentence summary of what this text is about")
    key_points:        List[str] = Field(description="The 3-7 most important concepts or arguments")
    actions:           List[str] = Field(description="Explicit action items or tasks mentioned")
    deadlines:         List[str] = Field(description="Any dates, deadlines, or time references")
    ambiguous_phrases: List[str] = Field(description="Idioms, metaphors, or vague language that may confuse literal readers")
    numerical_data:    List[str] = Field(description="All numbers, percentages, statistics found in the text")
    cognitive_load:    str       = Field(description="Estimated complexity: low / medium / high / very high")
    document_type:     str       = Field(description="e.g. academic article, task list, email, news article, instructions")

ANALYZER_PROMPT = """You are a cognitive accessibility analyst.
Analyze the following content carefully.
Be exhaustive with actions, deadlines, ambiguous phrases, and numerical data.
Do not transform or rewrite the content — only analyze its structure.

CONTENT:
{text}
"""

def content_analyzer_agent(state: NeuroAlignState) -> dict:
    session_cost: SessionCost = state.get("session_cost")  # type: ignore
    callbacks = [CostCallback(session_cost, "analyzer", MODEL)] if session_cost else []

    llm = ChatOpenAI(model=MODEL, temperature=0, callbacks=callbacks)
    structured_llm = llm.with_structured_output(ContentAnalysis)

    result: ContentAnalysis = structured_llm.invoke(
        ANALYZER_PROMPT.format(text=state["raw_input"])
    )
    return {"content_analysis": result.model_dump()}
