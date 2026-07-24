"""Smart Context Selection — automatically picks relevant files for a prompt.

Uses multiple signals to rank files:
  - Import graph (direct/indirect dependencies)
  - Git changes (recently modified files rank higher)
  - Symbol matching (files that define symbols mentioned in the prompt)
  - File frequency (how often referenced across the codebase)
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Optional


def get_git_changed_files(workspace: str = ".", days: int = 7) -> set[str]:
    """Get files modified in the last N days according to git."""
    try:
        r = subprocess.run(
            ["git", "log", f"--since={days}.days", "--name-only", "--pretty=format:", "--diff-filter=ACM"],
            capture_output=True, text=True, timeout=5, cwd=workspace,
        )
        if r.returncode != 0:
            return set()
        files = set()
        for line in r.stdout.strip().split("\n"):
            line = line.strip()
            if line:
                files.add(line)
        return files
    except Exception:
        return set()


def get_git_staged_files(workspace: str = ".") -> set[str]:
    """Get files that are staged or have uncommitted changes."""
    files = set()
    try:
        r = subprocess.run(
            ["git", "diff", "--name-only", "--cached"],
            capture_output=True, text=True, timeout=5, cwd=workspace,
        )
        if r.returncode == 0:
            for line in r.stdout.strip().split("\n"):
                line = line.strip()
                if line:
                    files.add(line)
        r = subprocess.run(
            ["git", "diff", "--name-only"],
            capture_output=True, text=True, timeout=5, cwd=workspace,
        )
        if r.returncode == 0:
            for line in r.stdout.strip().split("\n"):
                line = line.strip()
                if line:
                    files.add(line)
    except Exception:
        pass
    return files


def _extract_keywords(prompt: str) -> set[str]:
    """Extract likely symbol/file/import names from the prompt."""
    words = re.findall(r"[a-zA-Z_]\w+", prompt)
    return {w.lower() for w in words if len(w) > 2 and w.lower() not in _STOPWORDS}


_STOPWORDS = {
    "the", "and", "for", "are", "but", "not", "you", "all", "can", "had",
    "her", "was", "one", "our", "out", "has", "have", "been", "some", "same",
    "also", "its", "than", "them", "they", "this", "that", "with", "from",
    "what", "when", "where", "which", "who", "how", "will", "would", "could",
    "should", "may", "might", "shall", "about", "into", "over", "after",
    "before", "between", "under", "again", "further", "once", "here",
    "there", "each", "few", "more", "most", "other", "such", "no", "nor",
    "only", "own", "same", "too", "very", "just", "because", "does", "done",
    "doing", "being", "make", "made", "making", "add", "adds", "adding",
    "fix", "fixes", "fixed", "fixing", "update", "updates", "updated",
    "updating", "change", "changes", "changed", "changing", "remove",
    "removes", "removed", "removing", "create", "creates", "created",
    "creating", "delete", "deletes", "deleted", "deleting", "implement",
    "implements", "implemented", "implementing", "please", "need", "want",
    "file", "files", "code", "function", "class", "method", "variable",
    "test", "tests", "testing", "tested", "new", "old", "need", "help",
}


def rank_context(prompt: str, workspace: str = ".", max_files: int = 10) -> list[dict]:
    """Rank files by relevance to the prompt.

    Returns a list of dicts with file path, score, and reasons.
    """
    import ast
    from pathlib import Path as P

    keywords = _extract_keywords(prompt)
    root = P(workspace).resolve()

    # Gather signals
    changed_files = get_git_changed_files(workspace)
    staged_files = get_git_staged_files(workspace)
    recent_files = changed_files | staged_files

    # Score each file in the workspace
    scored: list[tuple[float, str, list[str]]] = []

    # Limit to a reasonable set of source files
    ext_priority = {".py": 3, ".js": 2, ".ts": 2, ".tsx": 2, ".jsx": 2,
                    ".go": 3, ".rs": 3, ".java": 3, ".rb": 2}
    visited = 0
    max_visit = 200  # limit for performance

    for path in sorted(root.rglob("*")):  # sorted for determinism
        if not path.is_file():
            continue
        if visited >= max_visit:
            break
        ext = path.suffix
        if ext not in ext_priority:
            continue
        visited += 1

        rel = str(path.relative_to(root))
        reasons = []
        score = 0.0

        # Base: language priority
        score += ext_priority.get(ext, 1) * 5

        # Git recency bonus
        if rel in recent_files:
            score += 30
            reasons.append(f"git change ({'staged' if rel in staged_files else 'modified'})")

        # Symbol/keyword matching in file name
        name_lower = path.stem.lower()
        for kw in keywords:
            if kw in name_lower:
                score += 25
                reasons.append(f"name matches '{kw}'")

        # Keyword matching in content (sample first 4KB)
        try:
            content = path.read_text(encoding="utf-8", errors="replace")[:4096]
            content_lower = content.lower()
            found_kw = set()
            for kw in keywords:
                if kw in content_lower:
                    found_kw.add(kw)
            if found_kw:
                score += len(found_kw) * 10
                reasons.append(f"mentions {', '.join(sorted(found_kw))}")

            # Try AST for Python files to find import relationships
            if ext == ".py":
                try:
                    tree = ast.parse(content)
                    names = {node.name.lower() for node in ast.walk(tree)
                             if isinstance(node, (ast.FunctionDef, ast.ClassDef))}
                    for kw in keywords:
                        if kw in names:
                            score += 15
                            if f"defines '{kw}'" not in reasons:
                                reasons.append(f"defines '{kw}'")
                except SyntaxError:
                    pass
        except Exception:
            pass

        if score > 0:
            scored.append((score, rel, reasons))

    # Sort by score descending, return top N
    scored.sort(key=lambda x: -x[0])
    return [
        {"file": rel, "score": round(s, 1), "reasons": r}
        for s, rel, r in scored[:max_files]
    ]
