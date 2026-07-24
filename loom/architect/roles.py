from __future__ import annotations

from typing import Any, Callable

from langchain_core.messages import AIMessage, SystemMessage, ToolMessage

from ..config import Config, ProviderSpec
from ..provider import build_chat_model
from ..tools import execute_tool_call
from ..tools.clang import TOOL_SCHEMAS

from .schema import NodeSpec
from .state import ArchitectState

from ..ui.render import render_file_op


def _build_node(
    spec: NodeSpec,
    base_config: Config,
    role_prompt: str,
    routes: bool = False,
) -> Callable[[dict], dict]:
    """Build a LangGraph node function for a given role."""

    def node_fn(state: dict) -> dict:
        node_name = spec.name

        # Track iterations for this node
        iterations = dict(state.iterations) if state.iterations else {}
        count = iterations.get(node_name, 0) + 1
        iterations[node_name] = count
        if count > spec.max_iterations:
            return {"route": "approved" if routes else None, "iterations": iterations}

        # Resolve provider/model for this node
        provider_name = spec.provider or base_config.provider
        model_name = spec.model or base_config.model
        api_key = base_config.api_key
        base_url = base_config.base_url

        if spec.provider and spec.provider != base_config.provider:
            from ..config import PROVIDERS, load_env_keys
            import os

            pinfo = PROVIDERS.get(spec.provider, {})
            env_keys = load_env_keys()
            api_key = (
                os.environ.get(pinfo.get("key_env", ""))
                or env_keys.get(pinfo.get("key_env", ""), "")
            )
            base_url = pinfo.get("base_url", "")

        model_spec = ProviderSpec(
            name=provider_name,
            api_key=api_key,
            model=model_name,
            base_url=base_url,
        )

        node_tools = [s for s in TOOL_SCHEMAS if s["name"] in spec.tools]
        model = build_chat_model(spec=model_spec, streaming=False, max_tokens=2048).bind_tools(node_tools)

        # Build the role-specific system prompt
        system_parts = [role_prompt]
        if spec.system_prompt:
            system_parts.append(spec.system_prompt)
        review = state.review_notes
        if review:
            system_parts.append(f"\nReview notes from previous iteration:\n{review}")
        system = SystemMessage(content="\n\n".join(system_parts))

        messages = list(state.messages)

        # Agent loop for this node: model -> tools -> model -> ... -> final answer
        node_messages = [system] + messages
        max_depth = 10
        token_usage = {"input": 0, "output": 0}

        for _ in range(max_depth):
            response = model.invoke(node_messages)
            node_messages.append(response)

            # Accumulate token usage from response metadata
            meta = getattr(response, "usage_metadata", None) or {}
            token_usage["input"] += meta.get("input_tokens", 0)
            token_usage["output"] += meta.get("output_tokens", 0)
            if not meta:
                meta2 = getattr(response, "response_metadata", None) or {}
                tu = meta2.get("token_usage", {}) or {}
                token_usage["input"] += tu.get("prompt_tokens", 0)
                token_usage["output"] += tu.get("completion_tokens", 0)

            if not getattr(response, "tool_calls", None):
                break

            for call in response.tool_calls:
                content = execute_tool_call(call["name"], call["args"], allow=True)
                node_messages.append(
                    ToolMessage(content=content, tool_call_id=call["id"])
                )
                # Render file operation if applicable
                if call["name"] == "write_file":
                    # Extract path from result like "Wrote 42 bytes to path"
                    path = str(content)
                    for prefix in ("Wrote",):
                        if path.startswith(prefix):
                            path = path.split(" to ", 1)[-1].strip()
                            break
                    render_file_op("+", path)
                elif call["name"] == "edit_file":
                    # Extract path from result like "Edited path (..)"
                    path = str(content)
                    for prefix in ("Edited",):
                        if path.startswith(prefix):
                            # Remove "Edited " and trailing " (...)"
                            path = path.replace("Edited ", "", 1)
                            if " (" in path:
                                path = path.split(" (", 1)[0]
                            break
                    render_file_op("~", path)
                elif call["name"] == "bash":
                    # Check if it's a delete command
                    result_str = str(content).lower()
                    if any(x in result_str for x in ("removed", "deleted", "rm ")):
                        # For simplicity, show the command as the "path" (truncated)
                        display = str(content)[:100].strip()
                        if len(str(content)) > 100:
                            display += "..."
                        render_file_op("-", display)

        # Return updated state: original messages + new AI/tool messages (exclude system prompt)
        new_messages = node_messages[len(messages) + 1 :]  # after system + original

        result: dict[str, Any] = {
            "messages": messages + new_messages,
            "current_node": node_name,
            "iterations": iterations,
        }

        result["_token_usage"] = {node_name: token_usage}

        # For routing roles (e.g. debugger), extract route from the final AI message
        if routes:
            for m in reversed(node_messages):
                if isinstance(m, AIMessage) and m.content:
                    content = m.content.strip().upper()
                    if "APPROVED" in content:
                        result["route"] = "approved"
                    elif "NEEDS_FIX" in content:
                        result["route"] = "needs_fix"
                        result["review_notes"] = m.content
                    break

        return result

    return node_fn


_ROLE_CONFIGS = {
    "thinker": {
        "prompt": (
            "You are a strategic planner. Analyze the task and create a detailed "
            "plan. Write the plan to plan.md using write_file. Be thorough and "
            "specific about what needs to be done."
        ),
        "routes": False,
    },
    "worker": {
        "prompt": (
            "You are a skilled implementer. Follow the plan in plan.md and "
            "implement it using the available tools. Be thorough and complete."
        ),
        "routes": False,
    },
    "debugger": {
        "prompt": (
            "You are a code reviewer. Review the implementation created by the "
            "worker. Check for correctness, completeness, and best practices. "
            "If everything looks good, end your review with 'APPROVED'. "
            "If changes are needed, end with 'NEEDS_FIX' followed by specific "
            "feedback notes."
        ),
        "routes": True,
    },
}


def _make_factory(role_config: dict) -> Callable[[NodeSpec, Config], Callable]:
    def factory(spec: NodeSpec, base_config: Config) -> Callable[[dict], dict]:
        return _build_node(
            spec=spec,
            base_config=base_config,
            role_prompt=role_config["prompt"],
            routes=role_config["routes"],
        )

    return factory


ROLE_FACTORIES: dict[str, Callable] = {
    name: _make_factory(cfg) for name, cfg in _ROLE_CONFIGS.items()
}
