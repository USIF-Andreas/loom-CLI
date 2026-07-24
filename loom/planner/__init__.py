"""Planning Agent — generates structured plans before execution.

When a user gives a task, the planner:
  1. Analyzes the request
  2. Generates a step-by-step plan with estimated file edits
  3. Shows the plan for confirmation
  4. Only then begins execution
"""

from __future__ import annotations

import json
from typing import Optional

from ..config import Config
from ..provider import build_chat_model


PLAN_PROMPT = """You are a planning agent. Given a user request and context about the project,
create a structured plan with specific steps. Each step should identify files to
read, search queries to run, edits to make, or tests to run.

Return your plan as valid JSON with this exact structure:
{
  "goal": "brief summary of the goal",
  "steps": [
    {"order": 1, "action": "read|search|write|edit|test|run|git", "file": "relative/file/path", "description": "what to do here"},
    {"order": 2, "action": "...", ...}
  ],
  "estimated_edits": 3,
  "files_touched": ["file1.py", "file2.py"]
}

Be specific about files and actions. Read files before editing them.
"""


def generate_plan(
    prompt: str,
    config: Config,
    context: Optional[str] = None,
) -> dict:
    """Generate a plan for the given prompt."""
    llm = build_chat_model(config=config)

    messages = [
        {"role": "system", "content": PLAN_PROMPT},
        {"role": "user", "content": f"Task: {prompt}\n\nProject context:\n{context or 'No additional context.'}"},
    ]

    try:
        response = llm.invoke(messages)
        content = response.content if hasattr(response, "content") else str(response)
        # Extract JSON from response
        content = content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()
        plan = json.loads(content)
    except (json.JSONDecodeError, Exception) as exc:
        plan = {
            "goal": prompt,
            "steps": [{"order": 1, "action": "run", "description": str(content), "file": ""}],
            "estimated_edits": 1,
            "files_touched": [],
        }

    required = {"goal", "steps"}
    if not all(k in plan for k in required):
        plan["goal"] = plan.get("goal", prompt)
        plan["steps"] = plan.get("steps", [])

    return plan


def render_plan(plan: dict) -> str:
    """Render a plan as readable text for user confirmation."""
    lines = [
        f"\n  \u2500" * 30,
        f"  Plan: {plan.get('goal', '')}",
        f"  \u2500" * 30,
    ]
    for step in plan.get("steps", []):
        action = step.get("action", "?")
        desc = step.get("description", "")
        file = step.get("file", "")
        file_str = f"  \u2192 {file}" if file else ""
        lines.append(f"  {step.get('order', 1)}. [{action}] {desc}")
        if file_str:
            lines.append(file_str)
    touches = plan.get("files_touched", [])
    if touches:
        lines.append(f"\n  Files: {', '.join(touches)}")
    edits = plan.get("estimated_edits", 0)
    lines.append(f"  Estimated edits: {edits}")
    lines.append("  \u2500" * 30)
    return "\n".join(lines)
