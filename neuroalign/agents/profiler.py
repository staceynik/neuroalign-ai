"""
Profiler Agent
==============
Builds the CognitiveProfile from user-selected modes, UI sliders,
and memory retrieved from ChromaDB. No LLM call needed here —
this is pure logic. Fast, free, deterministic.
"""

from neuroalign.state import NeuroAlignState


# Mode names match NeuroAlign_AI_Working_Spec.docx section 3
# Non-diagnostic labels: attention, reading, structure, numerical
# Sensible defaults per mode — override with user sliders
MODE_DEFAULTS = {
    "attention": {
        "reading_density": "very low",
        "structure_level": "high",
        "visual_support": "high",
        "tone": "energetic and direct",
        "strategies": [
            "open with 1-sentence TL;DR",
            "bullet points max 12 words",
            "extract all actions into checklist",
            "add focus reward markers 🔥",
            "max 2 sentences per paragraph",
        ],
    },
    "reading": {
        "reading_density": "very low",
        "structure_level": "medium",
        "visual_support": "medium",
        "tone": "calm and plain",
        "strategies": [
            "one idea per line",
            "max 8 words per line",
            "left-aligned text only",
            "replace complex words with simple alternatives",
            "bold max 3 key terms per section",
            "structure for TTS: no nested parentheticals",
        ],
    },
    "structure": {
        "reading_density": "medium",
        "structure_level": "very high",
        "visual_support": "high",
        "tone": "literal and explicit",
        "strategies": [
            "translate idioms and metaphors to literal meaning",
            "use tables and numbered lists",
            "explicit IF/THEN/ELSE rules for conditions",
            "separate assumptions from facts",
            "no rhetorical questions",
            "exact numbers, dates, quantities — never 'several' or 'soon'",
        ],
    },
    "numerical": {
        "reading_density": "low",
        "structure_level": "high",
        "visual_support": "very high",
        "tone": "grounded and concrete",
        "strategies": [
            "translate every number to real-world analogy",
            "replace numerical ordering with textual ordering",
            "group all statistics in a ## Data Summary section as JSON",
            "add plain-English scale anchors for large numbers",
        ],
    },
}


def profiler_agent(state: NeuroAlignState) -> dict:
    modes    = state.get("selected_modes", [])
    controls = state.get("user_controls", {})
    memory   = state.get("retrieved_memory", [])

    # Merge defaults for all selected modes (last mode wins on conflicts)
    merged_strategies = []
    merged_defaults   = {}
    for mode in modes:
        defaults = MODE_DEFAULTS.get(mode, {})
        merged_defaults.update(defaults)
        merged_strategies.extend(defaults.get("strategies", []))

    profile = {
        "modes":            modes,
        "reading_density":  controls.get("reading_density",  merged_defaults.get("reading_density",  "medium")),
        "structure_level":  controls.get("structure_level",  merged_defaults.get("structure_level",  "high")),
        "visual_support":   controls.get("visual_support",   merged_defaults.get("visual_support",   "medium")),
        "tone":             controls.get("tone",             merged_defaults.get("tone",             "clear and direct")),
        "strategies":       list(dict.fromkeys(merged_strategies)),  # deduplicate, preserve order
        "known_preferences": memory,
    }

    return {"cognitive_profile": profile}
