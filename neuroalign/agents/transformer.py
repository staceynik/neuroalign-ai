"""
Transformer Agent
=================
The core rewriting agent. Uses CognitiveProfile + ContentAnalysis
to produce a restructured document. Loads system prompts from
neuroalign/prompts/ so they can be tuned without touching Python code.
Cost is tracked via CostCallback.
"""

from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from neuroalign.state import NeuroAlignState
from neuroalign.cost_tracker import CostCallback, SessionCost

MODEL      = "gpt-4o-mini"
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

_FALLBACK_PROMPTS = {
    "attention": """You are NeuroAlign AI, a neurodiversity-affirming content transformer.
Transform content for a user who prefers Attention Support.
NOT a diagnosis — adapting to stated preferences only.
Rules: bold 1-sentence TL;DR, bullets max 12 words, ## ✅ Action Items checklist,
🔥 markers on max 3 key insights, H2 headers per theme, max 2 sentences/paragraph,
remove filler and passive voice.
Profile: {profile} | Analysis: {analysis} | Preferences: {known_preferences}""",

    "reading": """You are NeuroAlign AI, a neurodiversity-affirming content transformer.
Transform content for a user who prefers Reading Support.
NOT a diagnosis — adapting to stated preferences only.
Rules: one idea per line, max 8 words per line, plain vocabulary (complex word in parentheses),
H2 break every 5-6 lines, bold max 3 key terms per section, no nested parentheticals for TTS.
Profile: {profile} | Analysis: {analysis} | Preferences: {known_preferences}""",

    "structure": """You are NeuroAlign AI, a neurodiversity-affirming content transformer.
Transform content for a user who prefers Explicit Structure.
NOT a diagnosis — adapting to stated preferences only.
Rules: translate ALL idioms/metaphors to literal meaning, use tables and numbered lists,
start every section with "What this means:", IF/THEN/ELSE for conditions,
Key Facts table at top (Topic | Value), exact numbers only — never "several" or "soon".
Profile: {profile} | Analysis: {analysis} | Preferences: {known_preferences}""",

    "numerical": """You are NeuroAlign AI, a neurodiversity-affirming content transformer.
Transform content for a user who prefers Numerical Reasoning Support.
NOT a diagnosis — adapting to stated preferences only.
Rules: every number → real-world analogy (e.g. "47% — nearly half, like 47 of 100 people"),
replace 1st/2nd/3rd with first/second/third, scale anchors for large numbers,
group ALL data at end under ## 📊 Data Summary as JSON:
{"data_points":[{"label":"...","value":"...","unit":"...","analogy":"..."}]}
Profile: {profile} | Analysis: {analysis} | Preferences: {known_preferences}""",
}

def _load_prompt(mode: str) -> str:
    f = PROMPTS_DIR / f"{mode}.md"
    return f.read_text(encoding="utf-8") if f.exists() else _FALLBACK_PROMPTS.get(mode, "")

def transformer_agent(state: NeuroAlignState) -> dict:
    profile      = state["cognitive_profile"]
    modes        = profile.get("modes", [])
    session_cost: SessionCost = state.get("session_cost")  # type: ignore
    callbacks    = [CostCallback(session_cost, "transformer", MODEL)] if session_cost else []

    system_prompt = "\n\n---\n\n".join(_load_prompt(m) for m in modes) or _FALLBACK_PROMPTS["attention"]

    llm    = ChatOpenAI(model=MODEL, temperature=0.2, callbacks=callbacks)
    chain  = ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", "Transform this content:\n\n{text}")
    ]) | llm | StrOutputParser()

    transformed = chain.invoke({
        "profile":           str(profile),
        "analysis":          str(state["content_analysis"]),
        "known_preferences": str(profile.get("known_preferences", [])),
        "text":              state["raw_input"],
    })
    return {"transformed_output": {"text": transformed}}
