"""Checkpoints — create and roll back to saved states.

Commands:
  /checkpoint       — create a checkpoint
  /checkpoints      — list checkpoints
  /undo <N>         — roll back to checkpoint N
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

CHECKPOINT_DIR = Path.home() / ".loom" / "checkpoints"


def _next_id() -> int:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    existing = [int(d.name) for d in CHECKPOINT_DIR.iterdir() if d.is_dir() and d.name.isdigit()]
    return max(existing) + 1 if existing else 1


def create_checkpoint(workspace: str = ".") -> dict:
    cid = _next_id()
    target = CHECKPOINT_DIR / str(cid)
    target.mkdir(parents=True, exist_ok=True)

    # Save git diff if available
    try:
        r = subprocess.run(
            ["git", "diff", "--cached"],
            capture_output=True, text=True, timeout=5, cwd=workspace,
        )
        staged = r.stdout
        r = subprocess.run(
            ["git", "diff"],
            capture_output=True, text=True, timeout=5, cwd=workspace,
        )
        unstaged = r.stdout
        diff = staged + "\n" + unstaged

        if diff.strip():
            (target / "diff.patch").write_text(diff)

        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5, cwd=workspace,
        )
        (target / "head.txt").write_text(r.stdout.strip())
    except Exception:
        pass

    (target / "meta.json").write_text(json.dumps({
        "id": cid,
        "workspace": os.path.abspath(workspace),
    }))

    return {"id": cid, "path": str(target)}


def list_checkpoints() -> list[dict]:
    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)
    checkpoints = []
    for d in sorted(CHECKPOINT_DIR.iterdir(), key=lambda p: p.name, reverse=True):
        if d.is_dir() and d.name.isdigit():
            meta = {}
            meta_path = d / "meta.json"
            if meta_path.exists():
                meta = json.loads(meta_path.read_text())
            has_diff = (d / "diff.patch").exists()
            checkpoints.append({
                "id": int(d.name),
                "has_diff": has_diff,
                "meta": meta,
            })
    return checkpoints


def undo(checkpoint_id: int) -> str:
    target = CHECKPOINT_DIR / str(checkpoint_id)
    if not target.exists():
        return f"Checkpoint {checkpoint_id} not found"

    diff_path = target / "diff.patch"
    if not diff_path.exists():
        return f"No diff saved for checkpoint {checkpoint_id}"

    try:
        r = subprocess.run(
            ["git", "apply", "--reverse", str(diff_path)],
            capture_output=True, text=True, timeout=10,
        )
        if r.returncode == 0:
            return f"Rolled back to checkpoint {checkpoint_id}"
        return f"Rollback failed: {r.stderr or r.stdout}"
    except Exception as exc:
        return f"Error: {exc}"
