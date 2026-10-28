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
from typing import List, Optional, Literal
from langchain_openai import ChatOpenAI
from neuroalign.state import NeuroAlignState
from neuroalign.cost_tracker import CostCallback, SessionCost

MODEL = "gpt-4o-mini"

class Concept(BaseModel):
    id: str
    label: str
    description: str
    source_excerpt: str


class Relation(BaseModel):
    source_id: str
    target_id: str
    relation_type: Literal[
        "is_a",
        "causes",
        "explains",
        "leads_to",
        "contrasts_with",
        "influences",
        "is_example_of",
        "is_part_of",
        "is_attributed_to",
        "is_used_for",
        "other",
    ]
    explanation: str
    source_excerpt: str


class ContentBlock(BaseModel):
    id: str
    title: str
    concept_ids: List[str]
    source_excerpt: str

class ContentAnalysis(BaseModel):
    
    document_type: str = Field(
        description="e.g. academic article, task list, email, news article, instructions"
    )

    concepts: List[Concept] = Field(
        default_factory=list,
        description="Important concepts identified in the source"
    )
    relations: List[Relation] = Field(
        default_factory=list,
        description="Relationships between concepts explicitly supported by the source"
    )
    content_blocks: List[ContentBlock] = Field(
        default_factory=list,
        description="Meaningful groups of concepts supported by the source"
    )
    map_structure_type: Literal[
        "concept_group",
        "hierarchy",
        "sequence",
        "comparison",
        "causal",
        "mixed",
        "unclear"
    ] = Field(
        description="Dominant structure best suited for a visual overview"
    )
    main_topic: str = Field(
    description="The central topic of the source, expressed in the source language"
    )

    cognitive_load: Literal[
        "low",
        "medium",
        "high"
    ] = Field(
        description=(
            "Estimated cognitive load of the source material, based on "
            "concept density, complexity of relationships, terminology, "
            "and information structure"
        )
    )


ANALYZER_PROMPT = """You are a cognitive accessibility analyst.

Analyze the following content carefully.
Be exhaustive with actions, deadlines, ambiguous phrases, and numerical data.
Do not transform or rewrite the content — only analyze its structure.

CONCEPTS:
- Extract the important concepts needed to understand the source.
- Give each concept a unique ID.
- Preserve the source terminology and meaning.
- Include a short description and a supporting source excerpt.

RELATIONS:
- Identify meaningful relationships between extracted concepts.
- Use source and target concept IDs.
- Select relation types that accurately describe the source.
- Do not invent causal, hierarchical, or other relationships.
- Include a supporting source excerpt for every relation.

CONTENT BLOCKS:
- Group concepts only when the source supports a meaningful grouping.
- Give each block a unique ID and a concise title.
- Reference concepts using their IDs.
- Do not create artificial categories just to make a map look balanced.
- Concepts may remain ungrouped if no meaningful grouping is supported.

VISUAL MAP STRUCTURE:
Choose the dominant structure for a compact visual overview:
- concept_group: a set of related concepts at a similar level
- hierarchy: concepts organized into parent-child levels
- sequence: ordered stages or events
- comparison: items compared along shared dimensions
- causal: explicitly supported cause-and-effect relationships
- mixed: multiple important structural patterns
- unclear: insufficient evidence for a reliable structure

Choose based on the relationships expressed in the source,
not on the number of concepts or the desired appearance of the map.

For educational material with many concepts:
- Identify meaningful groups when supported by the source.
- Distinguish main concepts from their explanations and examples.
- Avoid treating every detail as an equally important top-level node.
- Do not omit important concepts merely to reduce map size.
- If the source does not support meaningful groups, do not invent them.

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

    print("ANALYZER RESULT:", result.model_dump())

    print("\n=== CONTENT ANALYSIS ===")
    print(result.model_dump_json(indent=2, ensure_ascii=False))

    return {"content_analysis": result.model_dump()}
