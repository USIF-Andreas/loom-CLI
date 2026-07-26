from __future__ import annotations

import threading
import time
import sys
from pathlib import Path

from ..config import Config, PROVIDERS, load_env_keys
from ..ui.render import console


DEFAULT_SPEC = {
    "name": "thinker-worker-debugger",
    "description": "Planner writes a plan, a worker executes it, a debugger reviews and approves or sends back.",
    "entry": "thinker",
    "nodes": [
        {"name": "thinker", "role": "thinker", "provider": "anthropic", "model": "claude-sonnet-4-6", "tools": ["write_file", "read_file"], "max_iterations": 1},
        {"name": "worker", "role": "worker", "provider": "groq", "model": "llama-3.3-70b-versatile", "tools": ["read_file", "write_file", "edit_file", "bash", "glob", "grep"], "max_iterations": 1},
        {"name": "debugger", "role": "debugger", "provider": "anthropic", "model": "claude-sonnet-4-6", "tools": ["read_file", "bash", "grep"], "max_iterations": 3},
    ],
    "edges": [
        {"source": "thinker", "target": "worker"},
        {"source": "worker", "target": "debugger"},
        {"source": "debugger", "target": "worker", "condition": "needs_fix"},
        {"source": "debugger", "target": "END", "condition": "approved"},
    ],
}


def _render_terminal_graph(spec: dict):
    from rich.panel import Panel
    from rich.text import Text
    from rich import box

    n = {x["name"]: x for x in spec.get("nodes", [])}
    colors = {"thinker": "color(203)", "worker": "color(75)", "debugger": "color(114)"}
    roles = {"thinker": "thinker", "worker": "worker", "debugger": "debugger"}

    console.print("\n  [bold color(222)]\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500[/]")
    console.print("  [bold color(222)]  Architect Pipeline[/]")
    console.print("  [bold color(222)]\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500[/]\n")

    # Render each node in declaration order
    node_names = [n["name"] for n in spec.get("nodes", [])]
    for i, name in enumerate(node_names):
        node = n[name]
        # Reuse the same role -> color mapping as before
        role = node.get("role", "")
        if role == "thinker":
            c = "color(203)"
        elif role == "worker":
            c = "color(75)"
        elif role == "debugger":
            c = "color(114)"
        else:
            c = "white"
        label = Text()
        label.append(f"{name}\n", style=f"bold {c}")
        label.append(f"role: {role}\n", style="dim")
        label.append(f"{node['provider']}: {node['model']}", style=f"dim {c}")
        console.print(Panel(label, border_style=c, padding=(0, 2), box=box.ROUNDED, width=44))
        
        # Vertical spacing between nodes (except after the last)
        if i < len(node_names) - 1:
            console.print("         \u2502")  # unicode box drawings light vertical
            console.print("         \u2193")  # down arrow

    console.print("       [dim]\u252c\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500[/]")
    console.print("       [dim]\u2502[/]                          [dim]\u2502[/]")
    console.print("   [dim]\u2190\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 [/][bold color(222)]needs_fix[/][dim] \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500 [/]")
    console.print("   [dim]\u2502[/]                        [dim]\u2502[/]")
    console.print("  [bold color(75)]worker[/]             [dim]END (approved)[/]")
    console.print("")


def _isatty() -> bool:
    import sys
    return sys.stdin.isatty()


def _interactive_select(items: list[str], header: str = "") -> str | None:
    """Filtered item picker using raw terminal I/O with full-screen redraw."""
    import tty, termios, sys, os, select

    COLORS = {"openai": "2", "anthropic": "3", "meta-llama": "6", "qwen": "5", "groq": "4"}
    filtered = items[:]
    selected = 0
    query = ""

    def redraw():
        nonlocal filtered, selected
        q = query.lower()
        filtered = [s for s in items if q in s.lower()][:50] if q else items[:50]
        if filtered and selected >= len(filtered):
            selected = max(0, len(filtered) - 1)

        sys.stdout.write("\033[3J\033[H\033[J")  # clear scrollback + home + clear screen
        if header:
            sys.stdout.write(f"\033[2m  {header}\033[0m\r\n\r\n")
        for i, item in enumerate(filtered):
            vendor = item.split("/", 1)[0] if "/" in item else ""
            c = COLORS.get(vendor, "7")
            pointer = "\u25b6" if i == selected else " "
            sys.stdout.write(f"  \033[3{c}m{pointer} {item}\033[0m\r\n")
        info = f"  filter: [{query}]  \u2191\u2193 move  \u23ce select  Esc cancel"
        sys.stdout.write(f"{info}\r\n")
        sys.stdout.flush()

    def read_key() -> str:
        b = os.read(fd, 1)
        if b == b"\x1b":
            r, _, _ = select.select([fd], [], [], 0.05)
            if r:
                b2 = os.read(fd, 1)
                if b2 == b"[":
                    b3 = os.read(fd, 1)
                    return {"A": "UP", "B": "DOWN", "C": "RIGHT", "D": "LEFT"}.get(chr(b3[0]), "ESC")
            return "ESC"
        if b in (b"\r", b"\n"):
            return "ENTER"
        if b == b"\x7f":
            return "BS"
        return b.decode()

    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        redraw()

        while True:
            ch = read_key()
            if ch == "UP":
                selected = max(0, selected - 1)
                redraw()
            elif ch == "DOWN":
                selected = min(len(filtered) - 1, selected + 1)
                redraw()
            elif ch == "ENTER":
                result = filtered[selected] if filtered else None
                break
            elif ch == "ESC":
                result = None
                break
            elif ch == "BS":
                query = query[:-1]
                redraw()
            elif len(ch) == 1 and ch.isprintable():
                query += ch
                redraw()
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)
        sys.stdout.write("\033[3J\033[2J\033[H")
        sys.stdout.flush()

    return result


def _pick_provider(current: str, header: str = "") -> str | None:
    names = _available_providers()
    if not names:
        console.print("  [color(203)]No API keys found. Set a key in ~/.loom/.env[/]")
        return None
    if _isatty():
        result = _interactive_select(names, header=header)
        return result  # None = cancelled
    console.print("\n  [bold]Select a provider:[/]")
    for i, name in enumerate(names, 1):
        marker = " *" if name == current else ""
        console.print(f"    {i}. {name}{marker}")
    while True:
        try:
            choice = input("  Provider [1-{}]: ".format(len(names))).strip()
            if not choice:
                return current
            idx = int(choice) - 1
            if 0 <= idx < len(names):
                return names[idx]
        except (ValueError, IndexError):
            pass
        console.print("  [color(203)]Invalid choice[/]")


def _pick_model(provider: str, current: str, header: str = "") -> str | None:
    from ..provider import list_models
    from ..config import Config, PROVIDERS, load_env_keys
    import os

    pinfo = PROVIDERS.get(provider, {})
    env_keys = load_env_keys()
    api_key = (
        os.environ.get(pinfo.get("key_env", ""))
        or env_keys.get(pinfo.get("key_env", ""), "")
    )
    base_url = pinfo.get("base_url", "")
    cfg = Config(provider=provider, api_key=api_key or "dummy", base_url=base_url)
    try:
        models = list_models(cfg)
    except Exception as exc:
        console.print(f"  [color(203)]Could not fetch models: {exc}[/]")
        return current

    # Filter out content-safety / safeguard models (not chat models)
    def _is_safeguard(mid: str) -> bool:
        low = mid.lower()
        return any(x in low for x in ("guard", "safeguard", "prompt_", "gpt-oss", "whisper", "orpheus"))

    models = [m for m in models if not _is_safeguard(m["id"])]

    if _isatty():
        model_ids = [m["id"] for m in models]
        result = _interactive_select(model_ids, header=header)
        return result  # None = cancelled

    from ..provider import model_line_parts
    display_models = models[:30]
    console.print(f"\n  [bold]Select a model for [color(75)]{provider}[/]:[/]")
    console.print("  [dim]Pick one with higher ctx to avoid rate limits[/]")
    for i, m in enumerate(display_models, 1):
        marker = " *" if m["id"] == current else ""
        parts = model_line_parts(m, active_provider=provider)
        model_desc = f"{m['id']}  {parts['note']}"
        extra = f"  (ctx={m['context_length']})" if m.get("context_length") else ""
        console.print(f"    {i}. {model_desc}{marker}{extra}")
    if len(models) > 30:
        console.print(f"    ... and {len(models) - 30} more")

    while True:
        try:
            choice = input("  Model [1-{}]: ".format(min(len(models), 30))).strip()
            if not choice:
                return current
            idx = int(choice) - 1
            if 0 <= idx < min(len(models), 30):
                return models[idx]["id"]
        except (ValueError, IndexError):
            pass
        console.print("  [color(203)]Invalid choice[/]")


_ROLE_DESCRIPTIONS = {
    "thinker": "Strategic planner — creates a detailed plan and writes it to plan.md",
    "worker": "Implementer — follows the plan and implements the code",
    "debugger": "Code reviewer — checks for correctness, approves or sends back for fixes",
}


def _available_providers() -> list[str]:
    from ..config import PROVIDERS, load_env_keys
    import os

    env_keys = load_env_keys()
    available = []
    for name, pinfo in PROVIDERS.items():
        key = os.environ.get(pinfo["key_env"]) or env_keys.get(pinfo["key_env"])
        if key:
            available.append(name)
    return available


def _configure_nodes(spec: dict) -> bool:
    """Configure provider/model per node.  Returns False if cancelled."""
    for node in spec["nodes"]:
        console.print(f"\n  [bold]\u2500\u2500 {node['name']} ({node['role']}) \u2500\u2500[/]")
        desc = _ROLE_DESCRIPTIONS.get(node["role"], "")
        provider = _pick_provider(node["provider"], header=desc)
        if provider is None:
            console.print("  [color(203)]Cancelled.[/]")
            return False
        node["provider"] = provider
        model = _pick_model(provider, node["model"], header=desc)
        if model is None:
            console.print("  [color(203)]Cancelled.[/]")
            return False
        node["model"] = model
    return True


_COLORS = {"thinker": "color(203)", "worker": "color(75)", "debugger": "color(114)"}


def _animate(label: str, color: str, stop: threading.Event):
    frames = ["\u280f", "\u2819", "\u2839", "\u2838", "\u283c", "\u2834", "\u2826", "\u2807"]
    i = 0
    while not stop.is_set():
        console.print(f"  [{color}]{frames[i % 8]} {label}           [/]", end="\r")
        i += 1
        time.sleep(0.08)
    console.print(f"  \033[K", end="\r")


def _run_architecture_terminal(spec: dict, config: Config, task: str):
    from .schema import ArchitectureSpec, NodeSpec, EdgeSpec
    from .builder import build_architect_graph
    from .state import ArchitectState
    from ..session import db
    from langchain_core.messages import HumanMessage
    import uuid

    arch_spec = ArchitectureSpec(
        name=spec.get("name", "custom"),
        entry=spec.get("entry", "thinker"),
        nodes=[NodeSpec(**n) for n in spec["nodes"]],
        edges=[EdgeSpec(**e) for e in spec.get("edges", [])],
        description=spec.get("description", ""),
    )

    session_id = uuid.uuid4().hex[:12]
    db.create_session(session_id, str(Path.cwd()))

    console.print(f"\n  [bold color(222)]Running architecture:[/] {arch_spec.name}")
    console.print(f"  [dim]Task:[/] {task}")
    console.print(f"  [dim]Session:[/] {session_id}")
    console.print(f"  [dim]Press Ctrl+C to cancel and return to chat[/]\n")

    app = build_architect_graph(arch_spec, config)
    initial_state = ArchitectState(
        messages=[HumanMessage(content=task)],
        session_id=session_id,
        current_node=arch_spec.entry,
    )

    roles = {n.name: n.role for n in arch_spec.nodes}
    node_models = {n["name"]: f"{n['provider']}: {n['model']}" for n in spec["nodes"]}

    stop_anim = threading.Event()
    anim_thread = threading.Thread(
        target=_animate,
        args=(f"[bold]{arch_spec.entry}[/] ({roles.get(arch_spec.entry, '')})", _COLORS.get(roles.get(arch_spec.entry, ""), "white"), stop_anim),
        daemon=True,
    )
    anim_thread.start()

    final_state = None
    token_usage: dict[str, dict] = {}
    try:
        for update in app.stream(initial_state, stream_mode="updates"):
            for node_name, node_output in update.items():
                final_state = node_output

                if anim_thread:
                    stop_anim.set()
                    anim_thread.join(timeout=0.3)
                    anim_thread = None

                role = roles.get(node_name, "")
                c = _COLORS.get(role, "white")
                model_info = node_models.get(node_name, "")
                console.print(f"  [{c}]\u2503[/] [bold]{node_name}[/]  [dim]{role} ({model_info})[/]           ")

                tu = node_output.get("_token_usage", {}).get(node_name, {})
                if tu:
                    token_usage[node_name] = tu
                    # Show per-node token usage right after node completion
                    if tu.get("input", 0) or tu.get("output", 0):
                        console.print(f"    [{c}]✦ {tu.get('input', 0):,} in / {tu.get('output', 0):,} out[/]")

                next_target = None
                for e in arch_spec.edges:
                    if e.source == node_name:
                        if not e.condition:
                            next_target = e.target if e.target != "END" else None
                            break
                        route = node_output.get("route") if isinstance(node_output, dict) else ""
                        if route == e.condition:
                            next_target = e.target if e.target != "END" else None
                            break

                if next_target:
                    time.sleep(0.5)
                    stop_anim.clear()
                    anim_thread = threading.Thread(
                        target=_animate,
                        args=(f"[bold]{next_target}[/] ({roles.get(next_target, '')})", _COLORS.get(roles.get(next_target, ""), "white"), stop_anim),
                        daemon=True,
                    )
                    anim_thread.start()
    except KeyboardInterrupt:
        if anim_thread:
            stop_anim.set()
            anim_thread.join(timeout=0.3)
        console.print(f"\n  [color(203)]\u2717 Cancelled by user[/]")
        return None

    if final_state is not None:
        line = "\u2500" * 36
        console.print(f"\n  [bold color(114)]{line}[/]")
        console.print("  [bold color(114)]  Results[/]")
        console.print(f"  [bold color(114)]{line}[/]\n")
        for msg in final_state.get("messages", []):
            if hasattr(msg, "name") and msg.name:
                console.print(f"  [dim]\u2514 {msg.name}[/]")
            if hasattr(msg, "content") and msg.content:
                text = str(msg.content)[:300]
                console.print(f"   {text}")
            db.save_message(session_id, msg)

        route = final_state.get("route", "")
        if route:
            console.print(f"\n  [bold color(222)]Final route:[/] {route}")

        if token_usage:
            total_in = sum(t.get("input", 0) for t in token_usage.values())
            total_out = sum(t.get("output", 0) for t in token_usage.values())
            console.print(f"\n  [bold color(222)]Tokens used:[/]")
            for node_name, tu in token_usage.items():
                c = _COLORS.get(roles.get(node_name, ""), "white")
                console.print(f"    [{c}]{node_name}:[/] {tu.get('input', 0):,} in / {tu.get('output', 0):,} out")
            console.print(f"    [dim]Total: {total_in:,} in / {total_out:,} out[/]")
    return final_state


def run_architect_terminal(config: Config):
    spec = dict(DEFAULT_SPEC)
    # deep-copy the nested lists/dicts
    spec["nodes"] = [dict(n) for n in DEFAULT_SPEC["nodes"]]
    spec["edges"] = [dict(e) for e in DEFAULT_SPEC["edges"]]

    console.print("[bold color(222)]═══ Architect — Multi-Agent Pipeline ═══[/]")
    _render_terminal_graph(spec)

    if not _configure_nodes(spec):
        console.print("  [dim]Architect setup cancelled.[/]")
        return

    # Show final config
    from rich.panel import Panel
    from rich.text import Text
    from rich import box

    colors = {"thinker": "color(203)", "worker": "color(75)", "debugger": "color(114)"}
    console.print("\n  [bold color(222)]\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500[/]")
    console.print("  [bold color(222)]  Configured Architecture[/]")
    console.print("  [bold color(222)]\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500[/]\n")
    for nd in spec["nodes"]:
        c = colors.get(nd["role"], "white")
        label = Text()
        label.append(f"{nd['name']}\n", style=f"bold {c}")
        label.append(f"{nd['provider']}: {nd['model']}\n", style=f"dim {c}")
        label.append(f"tools: {', '.join(nd['tools'])}", style="dim white")
        console.print(Panel(label, border_style=c, padding=(0, 2), box=box.ROUNDED, width=44))

    try:
        task = input("\n  Task: ").strip()
    except (EOFError, KeyboardInterrupt):
        console.print("  [color(203)]Cancelled.[/]")
        return
    if not task:
        console.print("  [color(203)]No task given, exiting.[/]")
        return

    _run_architecture_terminal(spec, config, task)
