"""Multi-Agent System — a pipeline of specialized agents.

Pipeline:
  Planner → Researcher → Coder → Reviewer → Tester → Summarizer

Each agent has its own prompt, tools, and short-term memory.
The output of each agent feeds into the next.
"""

from __future__ import annotations

import json
import time
from typing import Optional

from ..config import Config
from ..provider import build_chat_model
from ..tools import execute_tool_call


def _call_llm(system: str, user: str, config: Config) -> str:
    llm = build_chat_model(config=config)
    try:
        response = llm.invoke([
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ])
        return response.content if hasattr(response, "content") else str(response)
    except Exception as exc:
        return f"Error: {exc}"


# ── Agent prompts ─────────────────────────────────────────────────────

PLANNER_PROMPT = """You are the Planner agent. Given a user task, analyze what needs to be done
and produce a structured plan. Break the task into concrete steps.

Return your response as valid JSON:
{
  "goal": "what the user wants",
  "steps": [
    {"step": 1, "action": "what to do", "files": ["file1.py", "file2.py"]}
  ],
  "research_queries": ["search terms to look up"],
  "estimated_complexity": "low|medium|high"
}"""

RESEARCHER_PROMPT = """You are the Researcher agent. Given a plan, research how to implement it.
Look at existing code, check imports, find relevant patterns.

Return:
- Key files that need to be read
- Patterns or conventions in the codebase
- Potential pitfalls
- Recommended approach"""

CODER_PROMPT = """You are the Coder agent. Given research findings, write the actual code.
Use the tools available to read, write, and edit files.

Plan your edits carefully. Read files before modifying them."""

REVIEWER_PROMPT = """You are the Reviewer agent. Review the code changes for:
1. Correctness - does it work?
2. Style - does it match project conventions?
3. Edge cases - are there bugs?
4. Security - are there vulnerabilities?

Be thorough but constructive. List specific issues."""

TESTER_PROMPT = """You are the Tester agent. Given the code changes, write and run tests.
Check that:
1. Existing tests still pass
2. New code has appropriate tests
3. Edge cases are covered

Run the actual test commands."""

SUMMARIZER_PROMPT = """You are the Summarizer agent. Given the full pipeline output, create
a concise summary for the user covering:
- What was done
- Which files were changed
- Tests that were run
- Any issues or follow-ups needed"""


# ── Agent runner ──────────────────────────────────────────────────────

def _run_agent(
    prompt: str,
    system_prompt: str,
    config: Config,
    context: str = "",
    tools: Optional[list[str]] = None,
) -> str:
    """Run a single agent with optional tool access."""
    from ..agent.graph import run_agent_streaming

    if tools:
        from ..tools.clang import TOOL_SCHEMAS
        from langchain_openai import ChatOpenAI

        llm = build_chat_model(config=config)
        available = [s for s in TOOL_SCHEMAS if s["name"] in tools]
        llm_with_tools = llm.bind_tools(available) if available else llm

        from langgraph.graph import END, StateGraph

        def call_model(state):
            return {"messages": state["messages"] + [llm_with_tools.invoke(state["messages"])]}

        def should_continue(state):
            last = state["messages"][-1]
            return "tools" if getattr(last, "tool_calls", None) else END

        def tools_node(state):
            last = state["messages"][-1]
            tool_messages = []
            for call in getattr(last, "tool_calls", []) or []:
                content = execute_tool_call(call["name"], call["args"], allow=True)
                from langchain_core.messages import ToolMessage
                tool_messages.append(ToolMessage(content=content, tool_call_id=call["id"]))
            return {"messages": state["messages"] + tool_messages}

        g = StateGraph(dict)
        g.add_node("agent", call_model)
        g.add_node("tools", tools_node)
        g.set_entry_point("agent")
        g.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
        g.add_edge("tools", "agent")
        app = g.compile()

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"{context}\n\nTask: {prompt}"},
        ]
        try:
            result = app.invoke({"messages": messages})
            return str(result["messages"][-1].content)
        except Exception as exc:
            return f"Error: {exc}"

    return _call_llm(system_prompt, f"{context}\n\nTask: {prompt}", config)


# ── Pipeline ──────────────────────────────────────────────────────────

def run_pipeline(
    task: str,
    config: Config,
    working_dir: str = ".",
    session_id: str = "",
) -> dict:
    """Run the full multi-agent pipeline.

    Returns dict with outputs from each agent.
    """
    from ..ui.render import console

    results = {
        "task": task,
        "planner": "",
        "researcher": "",
        "coder": "",
        "reviewer": "",
        "tester": "",
        "summarizer": "",
        "status": "running",
    }

    console.print(f"\n  [bold color(147)]\u25a0 Multi-Agent Pipeline[/]")
    console.print(f"  [dim]Task: {task}[/]\n")

    # 1. Planner
    console.print(f"  [bold color(222)]Planning...[/]")
    plan = _run_agent(task, PLANNER_PROMPT, config)
    results["planner"] = plan
    console.print(f"  \u2713 [dim]Plan generated[/]\n")

    # 2. Researcher
    console.print(f"  [bold color(117)]Researching...[/]")
    research = _run_agent(
        task, RESEARCHER_PROMPT, config,
        context=f"Plan: {plan[:1000]}",
        tools=["read_file", "glob", "grep"],
    )
    results["researcher"] = research
    console.print(f"  \u2713 [dim]Research complete[/]\n")

    # 3. Coder
    console.print(f"  [bold color(203)]Coding...[/]")
    coder_input = f"Plan: {plan[:500]}\n\nResearch: {research[:1000]}"
    code = _run_agent(
        task, CODER_PROMPT, config,
        context=coder_input,
        tools=["read_file", "write_file", "edit_file", "delete_file", "rename_file", "bash", "glob", "grep"],
    )
    results["coder"] = code
    console.print(f"  \u2713 [dim]Code written[/]\n")

    # 4. Reviewer
    console.print(f"  [bold color(114)]Reviewing...[/]")
    review = _run_agent(
        task, REVIEWER_PROMPT, config,
        context=f"Code changes: {code[:1000]}",
        tools=["read_file", "grep"],
    )
    results["reviewer"] = review
    console.print(f"  \u2713 [dim]Review complete[/]\n")

    # 5. Tester
    console.print(f"  [bold color(153)]Testing...[/]")
    test = _run_agent(
        task, TESTER_PROMPT, config,
        context=f"Review: {review[:500]}\n\nCode: {code[:500]}",
        tools=["read_file", "bash", "grep", "glob"],
    )
    results["tester"] = test
    console.print(f"  \u2713 [dim]Testing complete[/]\n")

    # 6. Summarizer
    console.print(f"  [bold color(147)]Summarizing...[/]")
    summary_input = (
        f"Plan: {plan[:500]}\n\n"
        f"Research: {research[:500]}\n\n"
        f"Code: {code[:1000]}\n\n"
        f"Review: {review[:500]}\n\n"
        f"Tests: {test[:500]}"
    )
    summary = _run_agent(task, SUMMARIZER_PROMPT, config, context=summary_input)
    results["summarizer"] = summary
    results["status"] = "completed"
    console.print(f"  \u2713 [bold color(114)]Pipeline complete[/]\n\n  {summary}\n")

    return results
