"""Project Knowledge Graph — dependency, class, and module graphs.

Commands:
  /graph          — show full dependency graph
  /graph auth     — show graph centered on a module/symbol
"""

from __future__ import annotations

import ast
import json
import subprocess
from pathlib import Path
from typing import Optional


def _find_source_files(workspace: str) -> list[Path]:
    root = Path(workspace).resolve()
    exts = {".py", ".js", ".ts", ".tsx", ".jsx", ".go", ".rs", ".java", ".rb"}
    ignore = {".git", "__pycache__", "node_modules", ".venv", "venv", "dist", "build", "target"}
    files = []
    for path in root.rglob("*"):
        if not path.is_file() or path.suffix not in exts:
            continue
        if any(p in ignore for p in path.parts):
            continue
        files.append(path)
    return files


def _parse_python_imports(content: str) -> list[str]:
    imports = []
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append(alias.name.split(".")[0])
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module.split(".")[0])
    except SyntaxError:
        pass
    return imports


def _parse_generic_imports(content: str) -> list[str]:
    import re
    imports = []
    patterns = [
        r'(?:from\s+)([\w.]+)(?:\s+import)',
        r'(?:import\s+)(?:[\w*]+\s+from\s+)?[\'"]([\w./-]+)[\'"]',
        r'(?:use\s+)([\w:]+)',
        r'(?:require\s*\(\s*[\'"]([\w./-]+)[\'"]\s*\))',
    ]
    for pat in patterns:
        for m in re.finditer(pat, content):
            imports.append(m.group(1).split("/")[0].split(".")[0])
    return imports


def build_dependency_graph(workspace: str = ".", focus: Optional[str] = None) -> dict:
    """Build a dependency graph of the project.

    Returns dict with nodes (files) and edges (imports).
    """
    files = _find_source_files(workspace)
    root = Path(workspace).resolve()
    nodes: list[dict] = []
    edges: list[dict] = []
    file_imports: dict[str, set[str]] = {}

    for path in files:
        rel = str(path.relative_to(root))
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        if path.suffix == ".py":
            imports = _parse_python_imports(content)
        else:
            imports = _parse_generic_imports(content)

        file_imports[rel] = set(imports)
        lang = path.suffix.lstrip(".")
        lang_map = {"py": "python", "js": "javascript", "ts": "typescript",
                    "go": "go", "rs": "rust", "java": "java", "rb": "ruby"}
        nodes.append({
            "id": rel,
            "label": rel,
            "language": lang_map.get(lang, lang),
            "imports": imports,
        })

    for file_rel, imps in file_imports.items():
        for imp in imps:
            # Find which file this import resolves to
            for other in file_imports:
                other_stem = Path(other).stem
                if imp == other_stem or imp == other:
                    edges.append({
                        "source": file_rel,
                        "target": other,
                        "label": f"imports {imp}",
                    })
                    break

    if focus:
        focus_lower = focus.lower()
        nodes = [n for n in nodes if focus_lower in n["id"].lower() or
                 any(focus_lower in imp.lower() for imp in n["imports"])]
        edges = [e for e in edges if
                 any(n["id"] == e["source"] or n["id"] == e["target"] for n in nodes)]

    return {"nodes": nodes, "edges": edges}


def _render_graph_text(graph: dict) -> str:
    """Render the dependency graph as text."""
    lines = ["\n  Project Dependency Graph\n", "  " + "\u2500" * 40 + "\n"]
    for node in graph.get("nodes", []):
        lines.append(f"  [bold]{node['label']}[/]  ({node['language']})")
        outgoing = [e for e in graph.get("edges", []) if e["source"] == node["id"]]
        incoming = [e for e in graph.get("edges", []) if e["target"] == node["id"]]
        if outgoing:
            for e in outgoing:
                lines.append(f"    \u2192 {e['target']}")
        if incoming:
            for e in incoming:
                lines.append(f"    \u2190 {e['source']}")
        lines.append("")
    lines.append(f"  {len(graph['nodes'])} files, {len(graph['edges'])} dependencies")
    return "\n".join(lines)


def render_dependency_graph(workspace: str = ".", focus: Optional[str] = None) -> None:
    """Render the dependency graph to console."""
    from .ui.render import console

    graph = build_dependency_graph(workspace, focus)
    if not graph["nodes"]:
        if focus:
            console.print(f"  [color(203)]No modules found matching '{focus}'[/]")
        else:
            console.print("  [color(203)]No source files found[/]")
        return

    console.print(f"\n  [bold color(147)]Dependency Graph[/]")
    if focus:
        console.print(f"  [dim]focused on: {focus}[/]")
    console.print(f"  [dim]{len(graph['nodes'])} files, {len(graph['edges'])} edges[/]\n")

    for node in sorted(graph["nodes"], key=lambda n: len(
        [e for e in graph["edges"] if e["source"] == n["id"]]
    ), reverse=True):
        console.print(f"  [bold]{node['label']}[/]")
        outgoing = [e for e in graph["edges"] if e["source"] == node["id"]]
        incoming = [e for e in graph["edges"] if e["target"] == node["id"]]
        if outgoing:
            for e in outgoing:
                console.print(f"    \u2192 [color(117)]{e['target']}[/]")
        if incoming:
            for e in incoming:
                console.print(f"    \u2190 [color(222)]{e['source']}[/]")
    console.print()
