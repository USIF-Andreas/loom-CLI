"""Slash-command registry for the interactive chat.

Commands open by typing `/` (the REPL prints the menu). `/commands` is
intentionally listed first.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from langchain_core.messages import AIMessage


@dataclass
class SlashCommand:
    name: str
    description: str
    handler: Callable[["ChatController"], None]


class ChatController:
    """Handle passed to command handlers (avoids circular imports)."""

    def __init__(self, ctx: dict) -> None:
        self.ctx = ctx

    @property
    def history(self):
        return self.ctx["history"]

    def clear_history(self) -> None:
        self.ctx["history"].clear()

    def print(self, role: str, text: str) -> None:
        self.ctx["print"](role, text)

    def exit(self) -> None:
        self.ctx["exit"] = True


def _cmd_commands(ctrl: ChatController) -> None:
    picker = ctrl.ctx.get("_show_commands")
    if picker is not None:
        picker()  # use the chat's numbered command picker (consistent for /commands and /com)
    else:
        from . import commands as _cmds

        ctrl.print("system", "Available commands:")
        for c in _cmds.COMMAND_LIST:
            ctrl.print("system", f"  /{c.name}  - {c.description}")


def _cmd_clear(ctrl: ChatController) -> None:
    import sys
    ctrl.clear_history()
    sys.stdout.write("\033[3J\033[2J\033[H")
    sys.stdout.flush()


def _cmd_models(ctrl: ChatController) -> None:
    picker = ctrl.ctx.get("_show_models")
    if picker is not None:
        picker()  # use the chat's numbered picker (consistent for /models and /mod)
    else:
        from ..cli import _cmd_models as run_models

        run_models(ctrl.ctx.get("provider"))


def _cmd_provider(ctrl: ChatController) -> None:
    picker = ctrl.ctx.get("_show_providers")
    if picker is not None:
        picker()  # chat's numbered provider picker
    else:
        ctrl.print("system", f"Current provider: {ctrl.ctx.get('provider')}")


def _cmd_help(ctrl: ChatController) -> None:
    from .palette import run_command_palette
    result = run_command_palette()
    if result:
        cmd = get_command(result)
        if cmd:
            cmd.handler(ctrl)


def _cmd_exit(ctrl: ChatController) -> None:
    ctrl.exit()


def _cmd_architect(ctrl: ChatController) -> None:
    from ..architect.server import run_architect_terminal

    ctrl.print("system", "Launching interactive architect...")
    run_architect_terminal(ctrl.ctx["config"])
    ctrl.print("system", "Architect finished. Use /commands to continue.")


def _cmd_serve(ctrl: ChatController) -> None:
    from ..cli import _serve_command as run_serve

    # Optional path argument: "/serve portfolio"
    args = ctrl.ctx.get("_last_args", [])
    path = args[0] if args else "."
    run_serve(path)


def _cmd_sessions(ctrl: ChatController) -> None:
    from ..architect.server import _interactive_select
    from ..session import db as _db

    _db.init_db()
    rows = _db.list_sessions()
    if not rows:
        ctrl.print("system", "No saved sessions yet.")
        return

    items = []
    ids = []
    for r in rows:
        sid = r["id"]
        dt = r["created_at"][:19] if r["created_at"] else ""
        wd = r["working_dir"]
        label = f"{sid}  {dt}  {wd}"
        items.append(label)
        ids.append(sid)

    selected = _interactive_select(items)
    if selected is None:
        ctrl.print("system", "Cancelled.")
        return

    idx = items.index(selected)
    session_id = ids[idx]

    messages = _db.load_session_messages(session_id)
    messages = [m for m in messages if m.__class__.__name__ != "SystemMessage"]

    ctrl.ctx["session_id"] = session_id
    ctrl.ctx["history"] = messages
    ctrl.ctx["live_session"] = True
    ctrl.ctx["tokens"]["input"] = 0
    ctrl.ctx["tokens"]["output"] = 0

    ctrl.print("system", f"Resumed session {session_id}")
    if messages:
        ctrl.print("system", "Showing previous conversation:")
        for msg in messages:
            role = "assistant" if msg.__class__.__name__ == "AIMessage" else (
                "user" if msg.__class__.__name__ == "HumanMessage" else "system"
            )
            content = str(msg.content)[:200]
            if content.strip():
                ctrl.print(role, content)


def _cmd_graph(ctrl: ChatController) -> None:
    """Show the project dependency graph."""
    from ..graph import render_dependency_graph

    args = ctrl.ctx.get("_last_args", [])
    focus = args[0] if args else None
    render_dependency_graph(ctrl.ctx.get("working_dir", "."), focus)


def _cmd_index(ctrl: ChatController) -> None:
    """Index the workspace for smart context."""
    from ..indexer import index_workspace
    from ..ui.render import console

    ctrl.print("system", "Indexing workspace...")
    stats = index_workspace(ctrl.ctx.get("working_dir", "."))
    ctrl.print("system",
        f"Indexed {stats['files']} files, {stats['symbols']} symbols, "
        f"{stats['imports']} imports in {stats['elapsed']}s"
    )


def _cmd_context(ctrl: ChatController) -> None:
    """Show context about the current workspace."""
    from ..context import rank_context, get_git_changed_files, get_git_staged_files
    from ..ui.render import console

    args = ctrl.ctx.get("_last_args", [])
    query = " ".join(args) or "current project"
    ctrl.print("system", f"Context analysis for: {query}")
    results = rank_context(query, ctrl.ctx.get("working_dir", "."), max_files=15)
    if not results:
        ctrl.print("system", "No relevant files found.")
        return
    for r in results:
        reasons = ", ".join(r["reasons"][:3]) if r["reasons"] else ""
        ctrl.print("system", f"  {r['file']}  (score: {r['score']})")
        if reasons:
            ctrl.print("system", f"    {reasons}")


def _cmd_remember(ctrl: ChatController) -> None:
    from ..memory import remember
    args = ctrl.ctx.get("_last_args", [])
    if len(args) < 2:
        ctrl.print("system", "Usage: /remember <key> <value>")
        return
    key = args[0]
    value = " ".join(args[1:])
    result = remember(key, value)
    ctrl.print("system", result)


def _cmd_forget(ctrl: ChatController) -> None:
    from ..memory import forget
    args = ctrl.ctx.get("_last_args", [])
    if not args:
        ctrl.print("system", "Usage: /forget <key>")
        return
    result = forget(args[0])
    ctrl.print("system", result)


def _cmd_memory(ctrl: ChatController) -> None:
    from ..memory import list_memories
    items = list_memories()
    if not items:
        ctrl.print("system", "No memories stored.")
        return
    ctrl.print("system", "Memories:")
    for key, value in items:
        ctrl.print("system", f"  {key}: {value}")


def _cmd_multi(ctrl: ChatController) -> None:
    """Run the multi-agent pipeline (planner→researcher→coder→reviewer→tester→summarizer)."""
    from ..multiagent import run_pipeline

    args = ctrl.ctx.get("_last_args", [])
    if args:
        task = " ".join(args)
    else:
        ctrl.print("system", "Enter a task for the multi-agent pipeline:")
        try:
            from .input_box import read_input
            task = read_input("task> ")
        except (EOFError, KeyboardInterrupt):
            ctrl.print("system", "Cancelled.")
            return
        if not task:
            ctrl.print("system", "No task provided.")
            return

    config = ctrl.ctx.get("config")
    working_dir = ctrl.ctx.get("working_dir", ".")
    session_id = ctrl.ctx.get("session_id", "")
    run_pipeline(task, config, working_dir, session_id)


def _cmd_goat(ctrl: ChatController) -> None:
    from .goat import play_goat_show

    args = ctrl.ctx.get("_last_args", [])
    action = args[0] if args else "all"
    play_goat_show(action)


def _cmd_checkpoint(ctrl: ChatController) -> None:
    from ..checkpoints import create_checkpoint
    result = create_checkpoint(ctrl.ctx.get("working_dir", "."))
    ctrl.print("system", f"Checkpoint #{result['id']} created")


def _cmd_checkpoints(ctrl: ChatController) -> None:
    from ..checkpoints import list_checkpoints
    items = list_checkpoints()
    if not items:
        ctrl.print("system", "No checkpoints yet.")
        return
    ctrl.print("system", "Checkpoints:")
    for cp in items:
        meta = cp.get("meta", {})
        label = f"  #{cp['id']}"
        if meta.get("workspace"):
            label += f"  {meta['workspace']}"
        if cp["has_diff"]:
            label += "  (has diff)"
        ctrl.print("system", label)


def _cmd_undo(ctrl: ChatController) -> None:
    from ..checkpoints import undo
    args = ctrl.ctx.get("_last_args", [])
    if not args:
        ctrl.print("system", "Usage: /undo <checkpoint_id>")
        return
    try:
        cid = int(args[0])
    except ValueError:
        ctrl.print("system", "Usage: /undo <checkpoint_id>")
        return
    result = undo(cid)
    ctrl.print("system", result)


def _cmd_git(ctrl: ChatController) -> None:
    from ..tools.shell import git
    args = ctrl.ctx.get("_last_args", [])
    cmd = " ".join(args) if args else "status"
    result = git(cmd)
    ctrl.print("system", f"git {cmd}")
    ctrl.print("system", result)


def _cmd_plan(ctrl: ChatController) -> None:
    """Toggle planning mode — shows plan before execution."""
    current = ctrl.ctx.get("plan_mode", False)
    ctrl.ctx["plan_mode"] = not current
    if ctrl.ctx["plan_mode"]:
        ctrl.print("system", "Planning mode enabled. I'll show a plan before each task.")
    else:
        ctrl.print("system", "Planning mode disabled.")


def _cmd_tools(ctrl: ChatController) -> None:
    from ..tools.clang import TOOL_SCHEMAS
    ctrl.print("system", "Available tools:")
    for schema in TOOL_SCHEMAS:
        name = schema.get("name", "?")
        desc = schema.get("description", "")
        required = schema.get("input_schema", {}).get("required", [])
        props = schema.get("input_schema", {}).get("properties", {})
        params = ", ".join(props.keys()) if props else "none"
        ctrl.print("system", f"  \u2713 {name}")
        ctrl.print("system", f"      {desc}")
        ctrl.print("system", f"      args: {params}")


def _cmd_test(ctrl: ChatController) -> None:
    from ..test_runner import run_tests
    args = ctrl.ctx.get("_last_args", [])
    path = args[0] if args else ""
    ctrl.print("system", "Running tests...")
    result = run_tests(path, ctrl.ctx.get("working_dir", "."))
    status = "PASS" if result.get("passed") else "FAIL"
    ctrl.print("system", f"  {status}  ({result.get('framework', '?')})  [{result.get('elapsed', 0)}s]")
    if result.get("stdout"):
        ctrl.print("system", result["stdout"][:500])


def _cmd_bench(ctrl: ChatController) -> None:
    from ..benchmark import run_benchmark
    config = ctrl.ctx.get("config")
    ctrl.print("system", "Running benchmark...")
    result = run_benchmark(config)
    if "error" in result:
        ctrl.print("system", f"Error: {result['error']}")
        return
    ctrl.print("system", f"  Model: {result['provider']}:{result['model']}")
    ctrl.print("system", f"  Latency: {result['latency']}s")
    ctrl.print("system", f"  Tokens: {result['tokens']['input']} in / {result['tokens']['output']} out")


def _cmd_plugins(ctrl: ChatController) -> None:
    from ..plugins import list_plugins
    plugins = list_plugins()
    if not plugins:
        ctrl.print("system", "No plugins installed.")
        ctrl.print("system", "Install plugins at ~/.loom/plugins/")
        return
    ctrl.print("system", "Installed plugins:")
    for p in plugins:
        ctrl.print("system", f"  {p.get('name', '?')}  v{p.get('version', '?')}  — {p.get('description', '')}")


def _cmd_mcp(ctrl: ChatController) -> None:
    from ..mcp import list_servers
    servers = list_servers()
    if not servers:
        ctrl.print("system", "No MCP servers configured.")
        ctrl.print("system", "Configure at ~/.loom/mcp.json")
        return
    ctrl.print("system", "MCP servers:")
    for s in servers:
        ctrl.print("system", f"  {s.get('name', '?')}  ({s.get('command', '?')})")


def _cmd_config(ctrl: ChatController) -> None:
    from ..config import PROVIDERS
    args = ctrl.ctx.get("_last_args", [])
    config = ctrl.ctx.get("config")
    if not config:
        ctrl.print("system", "No active config.")
        return
    ctrl.print("system", "Current configuration:")
    ctrl.print("system", f"  Provider: {config.provider}")
    ctrl.print("system", f"  Model: {config.model}")
    ctrl.print("system", f"  Permission mode: {ctrl.ctx.get('permission_mode', 'confirm')}")
    ctrl.print("system", f"  Planning mode: {ctrl.ctx.get('plan_mode', False)}")


def _cmd_summarize(ctrl: ChatController) -> None:
    """Print a project summary with a Mermaid structure diagram."""
    from ..graph import build_dependency_graph
    from pathlib import Path

    working_dir = ctrl.ctx.get("working_dir", ".")
    project = Path(working_dir).resolve().name

    graph = build_dependency_graph(working_dir)
    if not graph["nodes"]:
        ctrl.print("system", "No source files found.")
        return

    langs: dict[str, int] = {}
    modules: dict[str, list[str]] = {}
    root_files: list[str] = []
    for node in graph["nodes"]:
        lang = node.get("language", "?")
        langs[lang] = langs.get(lang, 0) + 1
        parts = node["id"].split("/")
        if len(parts) > 1:
            modules.setdefault(parts[0], []).append(node["id"])
        else:
            root_files.append(node["id"])

    total_files = len(graph["nodes"])
    total_edges = len(graph["edges"])
    total_nodes_mod = len(modules)

    summary = [
        f"[bold]{project}[/]  —  {total_files} files, {total_edges} dependencies, {total_nodes_mod} modules",
        "",
    ]
    if langs:
        lang_line = "  ".join(f"{k}: {v}" for k, v in sorted(langs.items(), key=lambda x: -x[1]))
        summary.append(f"[dim]{lang_line}[/]")
        summary.append("")

    for mod, files in sorted(modules.items()):
        sub_count = len(files)
        summary.append(f"  [color(147)]{mod}/[/]  ({sub_count} files)")
        for f in sorted(files)[:8]:
            summary.append(f"    [dim]\u2514[/] {f.split('/', 1)[1]}")
        if sub_count > 8:
            summary.append(f"    [dim]\u2514 ... +{sub_count - 8} more[/]")
    for f in sorted(root_files):
        summary.append(f"  [dim]\u2514[/] {f}")

    edges_done: set[tuple[str, str]] = set()
    mermaid_lines = ["```mermaid", "flowchart TB"]
    if root_files:
        mermaid_lines.append("  subgraph root[root]")
        for f in sorted(root_files):
            sid = f.replace(".", "_").replace("/", "_").replace("-", "_")
            mermaid_lines.append(f"    {sid}[\"{f}\"]")
        mermaid_lines.append("  end")
    for mod, files in sorted(modules.items()):
        mermaid_lines.append(f"  subgraph {mod}[{mod}]")
        for f in sorted(files)[:15]:
            sid = f.replace(".", "_").replace("/", "_").replace("-", "_")
            mermaid_lines.append(f"    {sid}[\"{f}\"]")
        if len(files) > 15:
            mermaid_lines.append(f"    _more[\"+{len(files) - 15} more\"]")
        mermaid_lines.append("  end")
    for edge in graph["edges"]:
        src_mod = edge["source"].split("/")[0] if "/" in edge["source"] else "__root__"
        tgt_mod = edge["target"].split("/")[0] if "/" in edge["target"] else "__root__"
        if src_mod != tgt_mod and (src_mod, tgt_mod) not in edges_done:
            edges_done.add((src_mod, tgt_mod))
            mermaid_lines.append(f"  {src_mod} --> {tgt_mod}")
    mermaid_lines.append("```")

    summary.append("")
    summary.append("[dim]Mermaid diagram (paste into GitHub markdown):[/]")
    summary.append("")
    summary.extend(mermaid_lines)

    ctrl.print("system", "\n".join(summary))


def _cmd_export(ctrl: ChatController) -> None:
    from pathlib import Path
    from datetime import datetime

    history = ctrl.ctx.get("history", [])
    session_id = ctrl.ctx.get("session_id", "unknown")
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    export_path = f"session_{session_id}_{now}.md"

    lines = [f"# Session {session_id}\n", f"Exported: {now}\n\n"]
    for msg in history:
        role = msg.__class__.__name__ if hasattr(msg, "__class__") else "unknown"
        content = str(getattr(msg, "content", ""))
        lines.append(f"## {role}\n\n{content}\n\n")

    Path(export_path).write_text("\n".join(lines))
    ctrl.print("system", f"Exported to {export_path}")


COMMANDS: dict[str, SlashCommand] = {}


def _register(name, description, handler):
    COMMANDS[name] = SlashCommand(name, description, handler)


_register("commands", "list all available commands", _cmd_commands)
_register("clear", "clear the conversation history", _cmd_clear)
_register("models", "list models for the current provider", _cmd_models)
_register("provider", "switch provider (groq/openrouter/nvidia/anthropic)", _cmd_provider)
_register("sessions", "list / resume a past session", _cmd_sessions)
_register("architect", "interactive multi-agent pipeline with provider/model picker", _cmd_architect)
_register("serve", "serve a folder over http (e.g. /serve portfolio)", _cmd_serve)
_register("graph", "show project dependency graph", _cmd_graph)
_register("index", "index workspace for smart context", _cmd_index)
_register("context", "show context analysis for a query", _cmd_context)
_register("multi", "run multi-agent pipeline (plan→research→code→review→test→summary)", _cmd_multi)
_register("remember", "store a memory (e.g. /remember lang Python)", _cmd_remember)
_register("forget", "remove a memory (/forget lang)", _cmd_forget)
_register("memory", "list all stored memories", _cmd_memory)
_register("goat", "play pixel goat animation (walk/think/dance/jump)", _cmd_goat)
_register("git", "run a git command (/git status)", _cmd_git)
_register("checkpoint", "create a checkpoint", _cmd_checkpoint)
_register("checkpoints", "list checkpoints", _cmd_checkpoints)
_register("undo", "roll back to a checkpoint (/undo 1)", _cmd_undo)
_register("plan", "toggle planning mode — shows plan before execution", _cmd_plan)
_register("tools", "list available tools", _cmd_tools)
_register("test", "run tests (/test [path])", _cmd_test)
_register("bench", "run a quick benchmark", _cmd_bench)
_register("plugins", "list installed plugins", _cmd_plugins)
_register("mcp", "list MCP servers", _cmd_mcp)
_register("config", "show current configuration", _cmd_config)
_register("export", "export session history", _cmd_export)
_register("summarize", "generate Mermaid diagram of project structure", _cmd_summarize)
_register("help", "show help", _cmd_help)
_register("exit", "exit the chat", _cmd_exit)

COMMAND_LIST = [
    COMMANDS["commands"],
    COMMANDS["clear"],
    COMMANDS["models"],
    COMMANDS["provider"],
    COMMANDS["sessions"],
    COMMANDS["architect"],
    COMMANDS["multi"],
    COMMANDS["plan"],
    COMMANDS["graph"],
    COMMANDS["index"],
    COMMANDS["context"],
    COMMANDS["tools"],
    COMMANDS["test"],
    COMMANDS["bench"],
    COMMANDS["plugins"],
    COMMANDS["mcp"],
    COMMANDS["config"],
    COMMANDS["git"],
    COMMANDS["checkpoint"],
    COMMANDS["checkpoints"],
    COMMANDS["undo"],
    COMMANDS["remember"],
    COMMANDS["forget"],
    COMMANDS["memory"],
    COMMANDS["serve"],
    COMMANDS["summarize"],
    COMMANDS["goat"],
    COMMANDS["help"],
    COMMANDS["exit"],
]


def get_command(name: str) -> SlashCommand | None:
    return COMMANDS.get(name)


def resolve_command(text: str) -> SlashCommand | None:
    """Resolve a typed command, supporting unique prefixes (e.g. /m -> /models)."""
    if not text or not text.startswith("/"):
        return None
    token = text[1:].split()[0]
    if not token:
        return None
    # Exact match first.
    if token in COMMANDS:
        return COMMANDS[token]
    # Unique prefix match.
    matches = [c for c in COMMANDS.values() if c.name.startswith(token)]
    if len(matches) == 1:
        return matches[0]
    return None


def is_command(text: str) -> bool:
    return resolve_command(text) is not None


def menu_text() -> str:
    return "  ".join(f"/{c.name}" for c in COMMAND_LIST)
