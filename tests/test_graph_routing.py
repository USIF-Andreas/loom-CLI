"""Integration test for graph routing logic using a mocked LLM.

No real API calls. We patch ChatAnthropic to return scripted AIMessages that
either request a tool call or finish, verifying the loop routes correctly.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

from loom.tools.clang import TOOL_SCHEMAS


def _make_llm(responses):
    """responses: list of AIMessage|Exception. Returns a mock bound llm."""
    llm = MagicMock()
    llm.bind_tools.return_value = llm
    llm.invoke = MagicMock(side_effect=responses)
    return llm


def _ai_with_tool():
    msg = AIMessage(content="")
    msg.tool_calls = [
        {"name": "read_file", "args": {"path": "main.py"}, "id": "call_1"}
    ]
    return msg


def _ai_final():
    return AIMessage(content="Done. The file defines main().")


def test_tool_then_finish_loop():
    from langgraph.graph import END, StateGraph

    from loom.tools import execute_tools

    llm = _make_llm([_ai_with_tool(), _ai_final()])

    def call_model(state):
        return {"messages": state["messages"] + [llm.invoke(state["messages"])]}

    def should_continue(state):
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END

    def tools(state):
        return execute_tools({**state, "permission_result": "allow"})

    b = StateGraph(dict)
    b.add_node("agent", call_model)
    b.add_node("tools", tools)
    b.set_entry_point("agent")
    b.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    b.add_edge("tools", "agent")
    graph = b.compile()

    state = {
        "messages": [SystemMessage(content="sys"), HumanMessage(content="read main.py")],
        "permission_result": "allow",
    }
    final = graph.invoke(state)
    # Expect: system, human, ai(tool), tool_result, ai(final)
    roles = [m.__class__.__name__ for m in final["messages"]]
    assert roles == ["SystemMessage", "HumanMessage", "AIMessage", "ToolMessage", "AIMessage"]
    # The tool result should contain file content (main.py exists in repo).
    assert "ToolMessage" in roles


def test_no_tool_stops_immediately():
    from langgraph.graph import END, StateGraph

    llm = _make_llm([_ai_final()])

    def call_model(state):
        return {"messages": state["messages"] + [llm.invoke(state["messages"])]}

    def should_continue(state):
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END

    b = StateGraph(dict)
    b.add_node("agent", call_model)
    b.add_node("tools", lambda s: s)
    b.set_entry_point("agent")
    b.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    graph = b.compile()

    final = graph.invoke({"messages": [HumanMessage(content="hi")], "permission_result": "allow"})
    assert final["messages"][-1].content == "Done. The file defines main()."
