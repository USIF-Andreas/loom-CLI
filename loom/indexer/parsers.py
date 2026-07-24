"""Language-specific parsers for extracting symbols, imports, classes, functions."""

from __future__ import annotations

import ast
import re
from pathlib import Path

LANG_MAP: dict[str, str] = {
    ".py": "Python",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".go": "Go",
    ".rs": "Rust",
    ".java": "Java",
    ".cpp": "C++",
    ".c": "C",
    ".h": "C",
    ".hpp": "C++",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".r": "R",
    ".m": "Objective-C",
}

IGNORE_DIRS = {
    ".git", "__pycache__", "node_modules", ".venv", "venv", "env",
    ".tox", ".eggs", "dist", "build", ".next", ".nuxt",
    "vendor", ".bundle", "target", "bin", "obj",
    ".terraform", ".serverless", ".svelte-kit",
}

IGNORE_FILES = {
    "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "poetry.lock",
    ".DS_Store", "Thumbs.db",
}

EXTENSIONS = set(LANG_MAP.keys())


def should_index(path: Path) -> bool:
    if any(p.startswith(".") for p in path.parts):
        return False
    if any(p in IGNORE_DIRS for p in path.parts):
        return False
    if path.name in IGNORE_FILES:
        return False
    return path.suffix in EXTENSIONS


# ── Python parser ─────────────────────────────────────────────────────

def parse_python(content: str, file_path: str) -> dict:
    symbols = []
    imports = []
    comments = []
    try:
        tree = ast.parse(content)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                symbols.append({
                    "name": node.name,
                    "kind": "function",
                    "line": node.lineno,
                    "parent": "",
                })
            elif isinstance(node, ast.AsyncFunctionDef):
                symbols.append({
                    "name": node.name,
                    "kind": "function",
                    "line": node.lineno,
                    "parent": "",
                })
            elif isinstance(node, ast.ClassDef):
                symbols.append({
                    "name": node.name,
                    "kind": "class",
                    "line": node.lineno,
                    "parent": "",
                })
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        symbols.append({
                            "name": item.name,
                            "kind": "method",
                            "line": item.lineno,
                            "parent": node.name,
                        })
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    imports.append({
                        "source": alias.name or "",
                        "target": alias.asname or alias.name or "",
                    })
            elif isinstance(node, ast.ImportFrom):
                module = node.module or ""
                for alias in node.names:
                    imports.append({
                        "source": module,
                        "target": alias.name,
                    })
    except SyntaxError:
        pass

    for i, line in enumerate(content.split("\n"), 1):
        stripped = line.strip()
        if stripped.startswith("#") and len(stripped) > 2:
            comments.append({"content": stripped, "line": i})

    return {"symbols": symbols, "imports": imports, "comments": comments}


# ── Generic regex-based parser for JS/TS/Go/Rust/Java etc. ────────────

_FUNC_RE = re.compile(
    r"(?:async\s+)?(?:def|function|fn|func|defn|fun)\s+(\w+)"
)
_CLASS_RE = re.compile(
    r"(?:class|struct|trait|interface|impl|enum)\s+(\w+)"
)
_IMPORT_RE = re.compile(
    r"(?:import|require|from|use|extern crate|include)\s+[\"']?([\w./-]+)[\"']?"
)
_CONST_RE = re.compile(
    r"(?:const|let|var|val|let\s+mut)\s+(\w+)\s*(?::\s*\w+)?\s*="
)


def parse_generic(content: str, file_path: str) -> dict:
    symbols = []
    imports = []
    comments = []

    lines = content.split("\n")
    for i, line in enumerate(lines, 1):
        stripped = line.strip()

        if "//" in stripped:
            idx = stripped.index("//")
            comment = stripped[idx:].strip()
            if len(comment) > 2:
                comments.append({"content": comment, "line": i})

        if stripped.startswith("/*") or "/*" in stripped:
            if stripped.endswith("*/"):
                comments.append({"content": stripped, "line": i})

        for match in _FUNC_RE.finditer(stripped):
            symbols.append({
                "name": match.group(1),
                "kind": "function",
                "line": i,
                "parent": "",
            })

        for match in _CLASS_RE.finditer(stripped):
            symbols.append({
                "name": match.group(1),
                "kind": "class",
                "line": i,
                "parent": "",
            })

        for match in _IMPORT_RE.finditer(stripped):
            target = match.group(1)
            if target and not target.startswith(".") and "/" not in target:
                imports.append({
                    "source": file_path,
                    "target": target,
                })

        for match in _CONST_RE.finditer(stripped):
            symbols.append({
                "name": match.group(1),
                "kind": "variable",
                "line": i,
                "parent": "",
            })

    return {"symbols": symbols, "imports": imports, "comments": comments}


PARSERS: dict[str, callable] = {
    "Python": parse_python,
}


def parse_file(content: str, file_path: str) -> dict:
    ext = Path(file_path).suffix
    lang = LANG_MAP.get(ext, "")
    parser = PARSERS.get(lang, parse_generic)
    return parser(content, file_path)
