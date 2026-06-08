"""
NeuroAlign Graph
================
Assembles the four agents into a LangGraph StateGraph.

Pipeline:
  profiler → analyzer → transformer → visualizer → END

Each node is a pure function: (state) -> dict of updates.
LangGraph merges the returned dict into the shared state automatically.
"""

from langgraph.graph import StateGraph, END

from neuroalign.state import NeuroAlignState
from neuroalign.agents.profiler    import profiler_agent
from neuroalign.agents.analyzer    import content_analyzer_agent
from neuroalign.agents.transformer import transformer_agent
from neuroalign.agents.visualizer  import visualizer_agent


def build_graph():
    graph = StateGraph(NeuroAlignState)

    graph.add_node("profiler",    profiler_agent)
    graph.add_node("analyzer",    content_analyzer_agent)
    graph.add_node("transformer", transformer_agent)
    graph.add_node("visualizer",  visualizer_agent)

    graph.set_entry_point("profiler")
    graph.add_edge("profiler",    "analyzer")
    graph.add_edge("analyzer",    "transformer")
    graph.add_edge("transformer", "visualizer")
    graph.add_edge("visualizer",  END)

    return graph.compile()
