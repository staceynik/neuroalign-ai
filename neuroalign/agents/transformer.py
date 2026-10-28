"""
Transformer Agent
=================
The core rewriting agent. Loads system prompts from neuroalign/prompts/.
 
Key architecture decision:
  System message  = ONLY the transformation rules (no variables)
  Human message   = content to transform + profile context + analysis
 
This separation ensures the LLM treats rules as instructions,
not as data to be mixed with profile JSON.
"""
 
from pathlib import Path
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.output_parsers import StrOutputParser
from neuroalign.state import NeuroAlignState
from neuroalign.cost_tracker import CostCallback, SessionCost
 
MODEL       = "gpt-4o-mini"
PROMPTS_DIR = Path(__file__).parent.parent / "prompts"
 
# Fallback prompts — used only if .md file is missing on disk
_FALLBACK_RULES = {
    "attention": """You are NeuroAlign AI, a neurodiversity-affirming content transformer.
Transform content for a user who prefers Attention Support. NOT a diagnosis.
Rules:
- Open with a bolded 1-sentence TL;DR
- Bullet points, max 12 words each
- ## ✅ Action Items section with checkboxes for every task/deadline
- 🔥 markers on max 3 key insights
- H2 headers for every major theme
- Max 2 sentences per paragraph
- Remove filler, passive voice, abstract commentary""",
 
    "reading": """You are NeuroAlign AI, a neurodiversity-affirming content transformer.
Transform content for a user who prefers Reading Support. NOT a diagnosis.
Rules:
- One idea per line, max 8 words per line
- Plain vocabulary (complex word in parentheses if needed)
- H2 section break every 5-6 lines
- Bold max 3 key terms per section
- No nested parentheticals (for TTS compatibility)
- Left-aligned only""",
 
    "structure": """You are NeuroAlign AI, a neurodiversity-affirming content transformer.
Transform content for a user who prefers Explicit Structure. This is an accessibility preference, NOT a diagnosis.

Rules:
- Start with a Key Facts table using the format Topic | Value.
- Include key facts supported by the source, such as the main topic, author, key figures, dates, theories, and important concepts when relevant.
- Do not invent missing facts. If a relevant detail is not specified in the source, do not guess.
- Use the structure that best represents the content: definitions, lists, hierarchies, sequences, comparison tables, or explicit relationships.
- Use numbered lists only when order or sequence matters.
- Use IF / THEN / ELSE only when the source describes an actual conditional relationship, decision rule, or procedure.
- Do not convert descriptive, historical, theoretical, or definitional statements into conditional rules.
- Clarify idioms, metaphors, and ambiguous expressions only when needed for understanding. Preserve meaningful metaphors and technical terminology.
- Make relationships between concepts explicit when they are supported by the source. Do not invent causal relationships, explanations, assumptions, or conclusions.
- Distinguish stated facts from interpretations and assumptions when relevant. Preserve the author's attribution and level of certainty.
- Explain the significance or implications of a concept only when doing so adds useful information. Do not start every section with "What this means:".
- Avoid repeating facts from the Key Facts table unless additional explanation or context is needed.
- Preserve the substantive information, arguments, and important details of the source.
- Use exact numbers and dates when provided. Do not replace precise information with vague expressions such as "several", "many", or "soon".
- Do not create additional sections or formatting solely to satisfy a rule.
""",
 
    "numerical": """You are NeuroAlign AI, a neurodiversity-affirming content transformer.
Transform content for a user who prefers Numerical Reasoning Support. NOT a diagnosis.
 
CRITICAL RULE: Convert EVERY Arabic numeral (0-9) and Roman numeral to words.
No digit may remain in the final output.
 
Rules:
- 1859 → eighteen fifty-nine
- (1859-1947) → (born eighteen fifty-nine, died nineteen forty-seven)
- 18/30 → eighteen out of thirty
- 12/09/1984 → twelfth of September, nineteen eighty-four
- 6 → six, 3 years → three years
- Ordinals: 1st → first, 2nd → second
- For grades: always state what the score means on its scale
- For large numbers: add a real-world scale anchor
- BEFORE outputting: scan for any remaining digit and rewrite that sentence""",
}
 
 
def _load_rules(mode: str) -> str:
    """Load from prompts/*.md (rules only, no {variables}), fallback to inline."""
    f = PROMPTS_DIR / f"{mode}.md"
    if f.exists():
        content = f.read_text(encoding="utf-8")
        # Strip the trailing {profile}/{analysis}/{known_preferences} lines
        # if they exist in the .md file — those go in the human message now
        lines = content.splitlines()
        clean = [l for l in lines if not l.strip().startswith(
            ("Profile context:", "Content analysis:", "Past user preferences:")
        )]
        return "\n".join(clean).strip()
    return _FALLBACK_RULES.get(mode, _FALLBACK_RULES["attention"])
    print("\n=== ACTIVE MODES ===")
    print(modes)

    print("\n=== ACTIVE SYSTEM PROMPT ===")
    print(rules)

    print("\n=== SOURCE TEXT PREVIEW ===")
    print(state["raw_input"][:500])
 
 
def transformer_agent(state: NeuroAlignState) -> dict:
    profile      = state["cognitive_profile"]
    modes        = profile.get("modes", [])
    session_cost: SessionCost = state.get("session_cost")  # type: ignore
    callbacks    = [CostCallback(session_cost, "transformer", MODEL)] if session_cost else []
 
    # System message = pure rules, no variable substitution
    rules = "\n\n---\n\n".join(_load_rules(m) for m in modes) or _FALLBACK_RULES["attention"]
 
    # Human message = content + context (kept separate so rules stay clean)
    human_content = f"""Transform this content.
 

TRANSFORMATION CONSTRAINTS (apply to all modes):
- Detect the language of the source content and use that same language for the entire transformed output.
- All generated text must remain in the source language, including headings, table headers, table values, labels, summaries, explanations, and bullet points.
- Do not translate the source content into English or any other language unless the user explicitly requests translation.
- Examples and formatting rules written in English do not override this requirement.
- Preserve proper names and technical terms in their original form when appropriate.
- Preserve facts, numerical values, qualifications, and attribution.
- Do not invent explanations, tasks, conclusions, or causal relationships.
- Distinguish the source author's claims from established facts.
- Preserve every substantive idea unless the selected mode explicitly permits summarization or omission.
- Structural changes are allowed when required by the selected mode.
- Any summary must remain faithful to the source.
- Do not introduce grammatical errors or change the original meaning.
 
COGNITIVE PROFILE: {str(profile)}
 
DOCUMENT CONTEXT:
- Main topic: {state['content_analysis'].get('main_topic', 'unknown')}
- Document type: {state['content_analysis'].get('document_type', 'unknown')}
 
CONTENT TO TRANSFORM:
{state['raw_input']}"""
 
    llm = ChatOpenAI(model=MODEL, temperature=0, callbacks=callbacks)
 
    messages = [
        SystemMessage(content=rules),
        HumanMessage(content=human_content),
    ]
 
    transformed = (llm | StrOutputParser()).invoke(messages)
    return {"transformed_output": {"text": transformed}}