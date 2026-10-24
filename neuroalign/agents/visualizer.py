"""
Visualizer Agent
================
Attention mode: generate a source-grounded infographic with the OpenAI Images API.
Other modes keep their existing Transformer output and do not invoke image generation.
"""

import base64
import os
from typing import Optional

from openai import OpenAI
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI

from neuroalign.state import NeuroAlignState
from neuroalign.cost_tracker import CostCallback, SessionCost

MODEL = "gpt-4o-mini"
IMAGE_MODEL = os.getenv("OPENAI_IMAGE_MODEL", "gpt-image-2.5-flare")


class VisualizerOutput(BaseModel):
    mermaid_diagram: Optional[str] = Field(
        default=None,
        description="Valid Mermaid.js diagram code (no fences) if useful. Null otherwise."
    )


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
- Prefer 3-5 meaningful branches where supported by the source.
- Keep the map compact, ideally no more than 2 levels below the root.
- Group concepts by explicit meaning or function in the source.
- Do not invent category nodes just to make the layout look balanced.
- Avoid long horizontal chains and excessive width.
- Use short labels and valid Mermaid syntax.
- Preserve important distinctions and relationships; do not invent facts.

OUTPUT:
Return valid Mermaid.js diagram code without Markdown fences.
Do not include explanations outside the diagram.

Selected modes: {modes}
Visual support preference: {visual_support}

TRANSFORMED CONTENT:
{transformed}
"""


def _build_infographic_prompt(state: NeuroAlignState) -> str:
    """Build an image-generation brief from the source, analysis, and adapted text."""
    analysis = state.get("content_analysis", {}) or {}
    controls = state.get("user_controls", {}) or {}
    profile = state.get("cognitive_profile", {}) or {}

    # The image is the primary Attention-mode result, not a decorative diagram.
    # Give the image model both source and analyzed/adapted representations so it
    # can make a content-sensitive composition while checking source fidelity.
    return f"""Create a polished educational infographic for NeuroAlign AI.

GOAL
Turn the supplied material into a genuinely designed visual explanation, not a
Mermaid flowchart, not a plain text page, and not a generic poster. Compose the
layout to fit THIS content. Use clear visual hierarchy, meaningful grouped
blocks, arrows/connectors only where the source supports a relationship, and
selective emphasis. A reader should understand the main idea and how the parts
relate by looking at the graphic.

DESIGN
- Landscape 3:2 composition, high-resolution, clean editorial infographic.
- Strong visual hierarchy: clear title, prominent main idea, distinct content
  regions, concise labels, legible supporting text, generous spacing.
- Choose a layout that fits the material: e.g. sequence/timeline for steps,
  comparison columns for contrasts, cause/effect for explicitly causal content,
  grouped modules for related concepts, or a mixed composition when justified.
- Do not force a fixed number of cards, columns, branches, or levels.
- Use a restrained, accessible palette and high contrast; avoid visual clutter,
  tiny text, decorative stock imagery, and unnecessary icons.
- Keep text in the same language as the source. Render words accurately.
- Prefer concise wording, but retain the key claims, conditions, distinctions,
  and relationships. Do not invent facts or imply unsupported causation.
- Do not include citations or details that are not in the supplied material.
- The result must be a single coherent infographic, not a collage of unrelated
  mini-panels and not a mind-map tree unless that is genuinely the best layout.

USER CONTROLS
Reading density: {controls.get("reading_density", "very low")}
Structure level: {controls.get("structure_level", "high")}
Visual support: {controls.get("visual_support", "high")}
Support mode: {profile.get("modes", ["attention"])}

CONTENT ANALYSIS (structural guidance; verify against source):
{analysis}

ADAPTED TEXT:
{state.get("transformed_output", {}).get("text", "")}

ORIGINAL SOURCE (ground truth for facts and relationships):
{state.get("raw_input", "")}
"""


def _generate_infographic(state: NeuroAlignState) -> tuple[Optional[bytes], Optional[str]]:
    """Return PNG bytes or a readable error; never fail the whole text pipeline."""
    try:
        client = OpenAI()
        response = client.images.generate(
            model=IMAGE_MODEL,
            prompt=_build_infographic_prompt(state),
            size="1536x1024",
            quality="high",
        )
        encoded = response.data[0].b64_json
        if not encoded:
            return None, "The image API returned no image data."
        return base64.b64decode(encoded), None
    except Exception as exc:
        # Text transformation remains available if image generation fails.
        return None, f"{type(exc).__name__}: {exc}"


def visualizer_agent(state: NeuroAlignState) -> dict:
    profile = state.get("cognitive_profile", {}) or {}
    modes = profile.get("modes", [])

    # These modes already produce their final output in the Transformer.
    # Keep their existing behavior unchanged.
    if any(mode in modes for mode in ["reading", "numerical", "structure"]):
        return {
            "final_markdown": state["transformed_output"]["text"],
            "mermaid_diagram": None,
            "infographic_bytes": None,
            "infographic_error": None,
        }

    # Attention now generates a real image instead of another Mermaid tree.
    image_bytes, image_error = _generate_infographic(state)
    return {
        "final_markdown": state["transformed_output"]["text"],
        "mermaid_diagram": None,
        "infographic_bytes": image_bytes,
        "infographic_error": image_error,
    }
