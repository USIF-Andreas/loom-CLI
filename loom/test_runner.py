"""Test Runner — runs tests and reports results.

Commands:
  /test [path]   — run tests
"""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path


def detect_test_framework(workspace: str = ".") -> str:
    root = Path(workspace)
    if (root / "pyproject.toml").exists() and "pytest" in (root / "pyproject.toml").read_text():
        return "pytest"
    if (root / "Cargo.toml").exists():
        return "cargo"
    if (root / "package.json").exists():
        pkg = json.loads((root / "package.json").read_text())
        dev = pkg.get("devDependencies", {})
        if "jest" in dev:
            return "jest"
        if "vitest" in dev:
            return "vitest"
        return "npm"
    if (root / "go.mod").exists():
        return "go"
    return "pytest"


def run_tests(path: str = "", workspace: str = ".") -> dict:
    framework = detect_test_framework(workspace)
    start = time.time()

    cmd_map = {
        "pytest": ["python", "-m", "pytest", path, "-v", "--tb=short"] if path else ["python", "-m", "pytest", "-v", "--tb=short"],
        "jest": ["npx", "jest", path] if path else ["npx", "jest"],
        "vitest": ["npx", "vitest", "run", path] if path else ["npx", "vitest", "run"],
        "cargo": ["cargo", "test"],
        "go": ["go", "test", "./..."],
        "npm": ["npm", "test"],
    }

    cmd = cmd_map.get(framework, ["python", "-m", "pytest"])

    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=120, cwd=workspace)
        elapsed = time.time() - start
        return {
            "framework": framework,
            "passed": r.returncode == 0,
            "stdout": r.stdout[-2000:] if r.stdout else "",
            "stderr": r.stderr[-1000:] if r.stderr else "",
            "elapsed": round(elapsed, 2),
            "exit_code": r.returncode,
        }
    except subprocess.TimeoutExpired:
        return {"framework": framework, "passed": False, "error": "Timed out after 120s", "elapsed": 120}
    except FileNotFoundError:
        return {"framework": framework, "passed": False, "error": f"Command not found: {cmd[0]}", "elapsed": 0}