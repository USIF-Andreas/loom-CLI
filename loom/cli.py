"""Typer CLI entry point for loom."""

from __future__ import annotations

import os
import sys
import uuid
from pathlib import Path

import typer

from .agent.graph import run_agent, run_agent_streaming
from .config import Config, PROVIDERS, CONFIG_PATH, load_env_keys
from .session import db
from .tools import shell
from .ui import render

app = typer.Typer(
    help="loom — a terminal-based agentic coding assistant",
    add_completion=False,
    invoke_without_command=True,
)


def _resolve_opt(value: str | None, flag: str) -> str | None:
    """Return an option value, falling back to a sys.argv scan.

    Typer binds the first bare token to the root callback's argument, so options
    placed after a positional (e.g. ``loom "p" --provider groq``) are not seen
    by the callback. This recovers them from argv directly.
    """
    if value:
        return value
    argv = sys.argv[1:]
    for i, a in enumerate(argv):
        if a == flag and i + 1 < len(argv) and not argv[i + 1].startswith("-"):
            return argv[i + 1]
        if a.startswith(flag + "="):
            return a.split("=", 1)[1]
    return None


@app.callback()
def main(
    ctx: typer.Context,
    prompt: list[str] = typer.Argument(
        None, help="Natural language task, or 'models'/'sessions' subcommand"
    ),
    yolo: bool = typer.Option(False, "--yolo", help="Skip permission prompts"),
    resume: str = typer.Option(None, "--resume", help="Resume a session by id"),
    provider: str = typer.Option(None, "--provider", help="Provider: anthropic|openrouter|nvidia|groq"),
    model: str = typer.Option(None, "--model", help="Override the model"),
    no_stream: bool = typer.Option(False, "--no-stream", help="Disable live streaming"),
) -> None:
    """Run the agent on a prompt, e.g. loom \"explain this repo\".

    Subcommands 'models' and 'sessions' are dispatched manually because typer
    cannot mix a catch-all prompt argument with real subcommands.
    """
    if ctx.invoked_subcommand is not None:
        return

    tokens = prompt or []
    if tokens and tokens[0] == "models":
        _cmd_models(_resolve_opt(provider, "--provider"))
        return
    if tokens and tokens[0] == "sessions":
        _cmd_sessions()
        return
    if tokens and tokens[0] == "chat":
        chat(
            provider=_resolve_opt(provider, "--provider"),
            model=_resolve_opt(model, "--model"),
            yolo=yolo or ("--yolo" in sys.argv),
        )
        return

    prompt_text = " ".join(tokens).strip()
    if not prompt_text:
        render.render_error("Supply a prompt, e.g. loom \"explain this repo\"")
        raise typer.Exit(code=1)

    parsed = {
        "yolo": yolo,
        "resume": resume,
        "provider": _resolve_opt(provider, "--provider"),
        "model": _resolve_opt(model, "--model"),
        "no_stream": no_stream,
    }
    _run_agent_from_args(prompt_text, parsed)


def _build_config(provider: str | None, model: str | None) -> Config:
    if provider and provider not in PROVIDERS:
        render.render_error(f"Unknown provider: {provider}")
        raise typer.Exit(code=1)
    config = Config.load(provider_override=provider)
    if provider:
        pinfo = PROVIDERS[provider]
        config.api_key = os.environ.get(pinfo["key_env"]) or config.api_key
        if not model:
            config.model = pinfo["default_model"]
        config.base_url = pinfo["base_url"]
    if model:
        config.model = model
    return config


def _save_key_to_env(key_env: str, value: str) -> None:
    """Append or update a KEY=VALUE line in the project-local .env file."""
    from .config import ENV_PATHS

    path = ENV_PATHS[0]  # project .env (cwd)
    lines: list[str] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()
    # Remove any existing line for this key.
    lines = [ln for ln in lines if not ln.strip().startswith(f"{key_env}=")]
    lines.append(f"{key_env}={value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _load_cfg_data() -> dict:
    """Load config.toml into a dict (best-effort), for reusing saved keys."""
    try:
        import tomllib

        if CONFIG_PATH.exists():
            with open(CONFIG_PATH, "rb") as fh:
                return tomllib.load(fh)
    except Exception:
        pass
    return {}


def _run_agent_from_args(prompt_text: str, parsed: dict) -> None:
    try:
        config = _build_config(parsed["provider"], parsed["model"])
    except RuntimeError as exc:
        render.render_error(str(exc))
        raise typer.Exit(code=1)

    permission_mode = "yolo" if parsed["yolo"] else config.permission_mode
    if permission_mode not in ("yolo", "deny", "confirm"):
        permission_mode = "confirm"

    working_dir = str(Path.cwd())

    if parsed["resume"]:
        session_id = parsed["resume"]
        db.init_db()
        history = db.load_session_messages(session_id)
        from ..agent.prompts import build_system_prompt
        from ..session.tree import project_tree
        from langchain_core.messages import HumanMessage, SystemMessage

        summary = project_tree(working_dir)
        messages = [
            SystemMessage(content=build_system_prompt(summary, working_dir)),
            *history,
            HumanMessage(content=prompt_text),
        ]
        run_resume(messages, config, session_id, working_dir, permission_mode)
        return

    session_id = uuid.uuid4().hex[:12]
    db.create_session(session_id, working_dir)
    render.render_role("system", f"Session {session_id}")

    messages = run_agent(
        prompt=prompt_text,
        config=config,
        session_id=session_id,
        working_dir=working_dir,
        permission_mode=permission_mode,
    )
    for msg in messages:
        db.save_message(session_id, msg)


def run_resume(messages, config, session_id, working_dir, permission_mode):
    """Run with a prebuilt message list (resumed session)."""
    from langgraph.graph import END, StateGraph

    from ..provider import build_chat_model
    from ..tools import execute_tools
    from ..tools.clang import TOOL_SCHEMAS as SCHEMAS
    from ..ui import confirm as confirm_ui

    llm = build_chat_model(config=config).bind_tools(SCHEMAS)

    def call_model(state):
        return {"messages": state["messages"] + [llm.invoke(state["messages"])]}

    def should_continue(state):
        last = state["messages"][-1]
        return "tools" if getattr(last, "tool_calls", None) else END

    def tools(state):
        last = state["messages"][-1]
        allow = True
        for call in last.tool_calls or []:
            if permission_mode == "deny":
                allow = False
            elif permission_mode != "yolo" and confirm_ui.needs_permission(
                call["name"], call["args"]
            ):
                ans = render.confirm_prompt(f"Run: {call['name']} {call['args']}")
                if ans != "allow" and ans != "always":
                    allow = False
        return execute_tools({**state, "permission_result": "allow" if allow else "deny"})

    b = StateGraph(dict)
    b.add_node("agent", call_model)
    b.add_node("tools", tools)
    b.set_entry_point("agent")
    b.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
    b.add_edge("tools", "agent")
    app_graph = b.compile()

    final = app_graph.invoke({"messages": messages})
    for msg in final["messages"]:
        if msg.__class__.__name__ == "AIMessage" and msg.content:
            render.render_text("assistant", str(msg.content))
        db.save_message(session_id, msg)


def _cmd_models(provider: str | None) -> None:
    """List available models for the configured provider."""
    from .provider import list_models

    try:
        config = _build_config(provider, None)
    except RuntimeError as exc:
        render.render_error(str(exc))
        raise typer.Exit(code=1)

    try:
        model_list = list_models(config)
    except Exception as exc:  # network / auth errors
        render.render_error(f"Failed to fetch models: {exc}")
        raise typer.Exit(code=1)

    render.render_role("system", f"{config.provider}: {len(model_list)} model(s)")
    for m in model_list:
        extra = ""
        if m.get("context_length"):
            extra = f"  (ctx={m['context_length']})"
        render.render_text("system", f"  {m['id']}{extra}")


def _cmd_sessions() -> None:
    """List past sessions."""
    db.init_db()
    rows = db.list_sessions()
    if not rows:
        render.render_text("system", "No sessions yet.")
        return
    render.render_role("system", f"{len(rows)} session(s):")
    for r in rows:
        render.render_text(
            "system", f"  {r['id']}  {r['created_at']}  {r['working_dir']}"
        )


@app.command()
def chat(
    provider: str = typer.Option(None, "--provider", help="Provider: anthropic|openrouter|nvidia|groq"),
    model: str = typer.Option(None, "--model", help="Override the model"),
    yolo: bool = typer.Option(False, "--yolo", help="Skip permission prompts"),
) -> None:
    """Start the interactive chat session with the agent."""
    if "--help" in sys.argv:
        render.render_text(
            "system",
            "loom chat [--provider X] [--model Y] [--yolo]\n"
            "Interactive chat. Type `/` to see commands; `/commands` lists all.",
        )
        return

    try:
        config = _build_config(provider, model)
    except RuntimeError as exc:
        render.render_error(str(exc))
        raise typer.Exit(code=1)

    # Cached config.toml data so provider switching can reuse saved keys.
    _cfg_data = _load_cfg_data()

    permission_mode = "yolo" if yolo else config.permission_mode
    session_id = uuid.uuid4().hex[:12]
    db.create_session(session_id, str(Path.cwd()))
    history: list = []
    working_dir = str(Path.cwd())

    def _print(role: str, text: str) -> None:
        from .ui.render import render_role, render_text

        if role == "user":
            render.render_text("user", text)
        elif role == "assistant":
            render.render_text("assistant", text)
        elif role == "tool_call":
            render.render_role("tool_call", text)
        elif role == "tool_result":
            render.render_text("tool_result", text)
        else:
            render.render_text("system", text)

    from .ui.logo import render_logo
    from .ui import commands as slash
    from .ui.input_box import read_input

    render_logo()
    render.render_role("system", f"provider={config.provider} model={config.model}")
    render.render_role("system", f"commands: {slash.menu_text()}  (type `/` to use)")

    # Selection state: when set, the next line picks from this list.
    pending_menu: dict = {}

    def _render_models(models: list, all_models: list) -> None:
        pending_menu["kind"] = "model"
        pending_menu["items"] = [m["id"] for m in models]
        pending_menu["all"] = all_models
        filt = pending_menu.get("filter", "")
        # On a router (openrouter) the model id embeds the upstream vendor,
        # e.g. "openai/gpt-5.1" or "anthropic/claude-opus-4.7". Surface that.
        header = f"Provider (router): {config.provider}   (active model: {config.model})"
        if filt:
            header += f"   [filter: '{filt}']"
        render.render_role("system", header)
        render.render_text(
            "system", f"Showing {len(models)} of {len(all_models)} models — pick a number:"
        )
        for i, m in enumerate(models, 1):
            mid = m["id"] or ""
            vendor = mid.split("/", 1)[0] if "/" in mid else config.provider
            extra = f"  (ctx={m['context_length']})" if m.get("context_length") else ""
            render.render_text("system", f"  {i}. {mid}  [{vendor}]{extra}")
        # Show available vendors so the user knows what to type to filter.
        if not filt and len(all_models) > 20:
            vendors = {}
            for m in all_models:
                mid = m["id"] or ""
                v = mid.split("/", 1)[0] if "/" in mid else config.provider
                vendors[v] = vendors.get(v, 0) + 1
            top = ", ".join(f"{v}({n})" for v, n in sorted(vendors.items(), key=lambda x: -x[1]))
            render.render_text("system", f"Vendors: {top}")
            if config.provider in ("openrouter", "nvidia"):
                render.render_text(
                    "system",
                    "Tip: these all run VIA openrouter. To see a vendor's own models "
                    "only, run /provider and pick that vendor (e.g. groq).",
                )
        render.render_text(
            "system",
            "Pick a number, type a vendor (e.g. 'openai'/'qwen') to filter, or 'c' to cancel.",
        )

    def _show_models():
        from .provider import list_models

        try:
            models = list_models(config)
        except Exception as exc:
            render.render_error(f"Failed to fetch models: {exc}")
            return
        pending_menu.clear()
        pending_menu["filter"] = ""
        _render_models(models, models)

    def _show_providers():
        from .config import PROVIDERS

        pending_menu.clear()
        pending_menu["kind"] = "provider"
        pending_menu["items"] = list(PROVIDERS.keys())
        render.render_role("system", "Providers — pick a number:")
        for i, name in enumerate(pending_menu["items"], 1):
            marker = " *" if name == config.provider else ""
            render.render_text(
                "system",
                f"  {i}. {name}  (default: {PROVIDERS[name]['default_model']}){marker}",
            )
        render.render_text("system", "Pick a number, or any text to cancel.")

    def _switch_provider(name: str) -> None:
        """Switch the active provider live and reset to its default model."""
        from .config import PROVIDERS

        if name not in PROVIDERS:
            render.render_error(f"Unknown provider: {name}")
            return
        # Resolve API key for the new provider (same precedence as Config.load).
        pinfo = PROVIDERS[name]
        env_keys = load_env_keys()
        api_key = (
            os.environ.get(pinfo["key_env"])
            or env_keys.get(pinfo["key_env"])
            or _cfg_data.get(pinfo["key_cfg"])
        )
        if not api_key:
            render.render_error(
                f"No API key for {name} ({pinfo['key_env']}) found in env/.env/config."
            )
            render.render_text(
                "system",
                "Paste your API key now, or type any text to cancel. "
                "It will be used for this session only (or saved to .env with 'y').",
            )
            try:
                pasted = read_input(f"{pinfo['key_env']}> ")
            except (EOFError, KeyboardInterrupt):
                return
            pasted = (pasted or "").strip()
            if not pasted or len(pasted) < 8:
                render.render_text("system", "Cancelled — provider not changed.")
                return
            api_key = pasted
            # Offer to persist the key to the project .env for future sessions.
            try:
                save = read_input("Save to .env for future sessions? [y/N]: ")
            except (EOFError, KeyboardInterrupt):
                save = ""
            if save.strip().lower() == "y":
                _save_key_to_env(pinfo["key_env"], api_key)
                render.render_text("system", f"Saved {pinfo['key_env']} to .env")
            else:
                render.render_text("system", "Key kept in this session only.")
        config.provider = name
        config.api_key = api_key
        config.base_url = pinfo["base_url"]
        config.model = pinfo["default_model"]
        render.render_role("system", f"Provider set to: {name} (model={config.model})")
        render.render_text("system", "Tip: run /models to pick a specific model.")

    def _show_commands():
        pending_menu.clear()
        pending_menu["kind"] = "command"
        pending_menu["items"] = [c.name for c in slash.COMMAND_LIST]
        render.render_role("system", "Commands:")
        for i, name in enumerate(pending_menu["items"], 1):
            render.render_text("system", f"  {i}. /{name}")
        render.render_text("system", "Pick a number, or any text to cancel.")

    ctx = {
        "config": config,
        "session_id": session_id,
        "working_dir": working_dir,
        "permission_mode": permission_mode,
        "history": history,
        "provider": config.provider,
        "exit": False,
        "print": _print,
        "_show_models": _show_models,
        "_show_providers": _show_providers,
        "_show_commands": _show_commands,
    }

    while not ctx["exit"]:
        try:
            user_input = read_input("> ")
        except (EOFError, KeyboardInterrupt):
            render.render_text("system", "bye.")
            break
        if not user_input:
            continue

        # If we are waiting for a menu selection, handle it first.
        if pending_menu:
            kind = pending_menu.get("kind")
            items = pending_menu.get("items", [])

            # 'c' cancels any pending menu.
            if user_input.strip().lower() == "c":
                pending_menu.clear()
                render.render_text("system", "Cancelled.")
                continue

            # In model mode, non-numeric text filters the list instead of canceling.
            if kind == "model" and not user_input.isdigit():
                all_models = pending_menu.get("all", [])
                q = user_input.strip().lower()
                if q:
                    filtered = [
                        m for m in all_models if q in (m["id"] or "").lower()
                    ]
                    pending_menu["filter"] = q
                    if not filtered:
                        render.render_text(
                            "system", f"No models match '{q}'. Try another filter."
                        )
                        _render_models(all_models, all_models)
                    else:
                        _render_models(filtered, all_models)
                else:
                    pending_menu["filter"] = ""
                    _render_models(all_models, all_models)
                continue

            if user_input.isdigit() and 1 <= int(user_input) <= len(items):
                choice = items[int(user_input) - 1]
                pending_menu.clear()
                if kind == "model":
                    config.model = choice
                    render.render_role("system", f"Model set to: {choice}")
                elif kind == "provider":
                    _switch_provider(choice)
                elif kind == "command":
                    cmd = slash.get_command(choice)
                    if cmd:
                        cmd.handler(slash.ChatController(ctx))
                continue
            # Any other text cancels the pending menu.
            pending_menu.clear()
            render.render_text("system", "Cancelled.")
            continue

        if user_input in ("/exit", "/quit"):
            break
        if slash.is_command(user_input):
            parts = user_input[1:].split()
            cmd = slash.resolve_command(user_input)
            if cmd is None:
                render.render_error(f"Unknown command: {user_input}")
                continue
            # Pass trailing args (e.g. "/serve portfolio") via ctx.
            ctx["_last_args"] = parts[1:]
            cmd.handler(slash.ChatController(ctx))
            continue
        # Agent turn (streaming).
        try:
            from .ui.logo import animate_thinking

            animate_thinking("thinking", duration=0.8)
            new_history = run_agent_streaming(
                prompt=user_input,
                config=config,
                session_id=session_id,
                working_dir=working_dir,
                permission_mode=permission_mode,
                history=history,
                on_token=lambda t: _stream_write(t),
            )
            history[:] = new_history
            _stream_flush()
        except Exception as exc:
            render.render_error(f"Agent error: {exc}")
        for msg in history:
            db.save_message(session_id, msg)

    render.render_text("system", "bye.")


_streaming_buffer = ""


def _stream_write(token: str) -> None:
    """Write streamed assistant tokens to stdout, line-buffered."""
    global _streaming_buffer
    _streaming_buffer += token
    # Print complete lines; keep the trailing partial line in the buffer.
    if "\n" in _streaming_buffer:
        head, _, tail = _streaming_buffer.rpartition("\n")
        render.console.print(head, end="", highlight=False)
        _streaming_buffer = tail
    else:
        render.console.print(token, end="", highlight=False)


def _stream_flush() -> None:
    """Flush any trailing partial line left in the stream buffer."""
    global _streaming_buffer
    if _streaming_buffer:
        render.console.print(_streaming_buffer, highlight=False)
        _streaming_buffer = ""


def _serve_command(path: str = ".") -> None:
    """Serve a folder over http so the user can preview a static site."""
    from pathlib import Path as _P

    target = _P(path)
    if not target.exists():
        render.render_error(f"Path not found: {path}")
        return
    if target.is_file():
        target = target.parent

    import socket
    import webbrowser

    # Find a free port.
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    port = s.getsockname()[1]
    s.close()

    url = f"http://localhost:{port}/"
    render.render_role("system", f"Serving {target} at {url}")
    render.render_text("system", "Press Ctrl-C to stop. (server runs for this session)")

    # Best-effort: open the browser.
    try:
        webbrowser.open(url)
    except Exception:
        pass

    # Run the server in a background thread so chat stays usable.
    import threading

    def _run():
        shell.bash(
            f"cd {target} && python -m http.server {port}",
            timeout=3600,
            cwd=str(target),
        )

    worker = threading.Thread(target=_run, daemon=True)
    worker.start()


if __name__ == "__main__":
    app()
