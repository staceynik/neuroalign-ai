"""
NeuroAlign AI — Shared State
============================
NeuroAlignState flows through every LangGraph node.
Each agent reads from it and returns a dict of updates.

session_cost is carried in state so agents can call
session_cost.add() via CostCallback without global variables.
"""

from typing import TypedDict, List, Dict, Any, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from neuroalign.cost_tracker import SessionCost


class NeuroAlignState(TypedDict, total=False):

    # ── SESSION ──────────────────────────────────────────────────────
    session_id:   str
    session_cost: Any   # SessionCost instance — passed through state for agent access

    # ── INPUT ────────────────────────────────────────────────────────
    raw_input:        str
    selected_modes:   List[str]
    user_controls:    Dict[str, Any]
    retrieved_memory: List[str]

    # ── AGENT OUTPUTS ─────────────────────────────────────────────────
    cognitive_profile:  Dict[str, Any]
    content_analysis:   Dict[str, Any]
    transformed_output: Dict[str, Any]

    # ── FINAL RENDER ──────────────────────────────────────────────────
    final_markdown:  str
    mermaid_diagram: Optional[str]
    chart_data:      Optional[Dict[str, Any]]
