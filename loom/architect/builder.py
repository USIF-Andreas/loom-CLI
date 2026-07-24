from __future__ import annotations

from langgraph.graph import END, StateGraph

from .registry import get_role_factory
from .schema import ArchitectureSpec
from .state import ArchitectState
from ..config import Config


def build_architect_graph(spec: ArchitectureSpec, base_config: Config):
    graph = StateGraph(ArchitectState)

    for node in spec.nodes:
        factory = get_role_factory(node.role)
        graph.add_node(node.name, factory(node, base_config))

    graph.set_entry_point(spec.entry)

    for node in spec.nodes:
        outgoing = spec.edges_from(node.name)
        if not outgoing:
            continue

        if len(outgoing) == 1 and outgoing[0].condition in (None, "*", "default"):
            target = outgoing[0].target
            graph.add_edge(node.name, END if target == "END" else target)
            continue

        route_map = {
            e.condition: (END if e.target == "END" else e.target) for e in outgoing
        }

        def _router(state: ArchitectState, _route_map=route_map):
            return _route_map.get(state.route, _route_map.get("default", END))

        graph.add_conditional_edges(node.name, _router)

    return graph.compile()


def run_architecture(spec: ArchitectureSpec, base_config: Config, initial_prompt: str, session_id: str):
    from langchain_core.messages import HumanMessage

    app = build_architect_graph(spec, base_config)
    initial_state = ArchitectState(
        messages=[HumanMessage(content=initial_prompt)],
        session_id=session_id,
        current_node=spec.entry,
    )
    return app.invoke(initial_state)
