"""Shell execution tool."""

from __future__ import annotations

import subprocess

DEFAULT_TIMEOUT = 30
MAX_OUTPUT_CHARS = 20000


def _truncate(text: str, limit: int = MAX_OUTPUT_CHARS) -> str:
    if len(text) <= limit:
        return text
    half = limit // 2
    return (
        text[:half]
        + f"\n... [output truncated: {len(text) - limit} chars omitted] ...\n"
        + text[-half:]
    )


def bash(
    command: str,
    timeout: int = DEFAULT_TIMEOUT,
    cwd: str | None = None,
) -> str:
    """Run a shell command and return a formatted result string.

    Captures stdout, stderr, and exit code. Output is truncated if very long.
    Long-running server commands (e.g. `python -m http.server`) are run in the
    background so the agent loop is not blocked; the process keeps running and
    can be reached via the printed URL.
    """
    # Detect server-like commands that would otherwise block forever.
    looks_like_server = any(
        tok in command
        for tok in ("http.server", "http-server", "serve", "0.0.0.0", ":8000", ":8080", "uvicorn", "gunicorn", "npm start", "next dev", "vite")
    )
    if looks_like_server:
        import os
        import signal

        proc = subprocess.Popen(
            command + " &",
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            cwd=cwd,
            preexec_fn=os.setsid,
        )
        return _truncate(
            f"exit_code=0\n"
            f"--- background server started (pid group {proc.pid}) ---\n"
            f"Command is running in the background. To stop it, the session must end "
            f"or you can run:  kill -- -{proc.pid}\n"
        )

    try:
        proc = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd,
        )
    except subprocess.TimeoutExpired as exc:
        out = exc.stdout or ""
        err = exc.stderr or ""
        return _truncate(
            f"Command timed out after {timeout}s.\n"
            f"--- stdout ---\n{out}\n--- stderr ---\n{err}"
        )

    exit_code = proc.returncode
    stdout = proc.stdout or ""
    stderr = proc.stderr or ""
    combined = (
        f"exit_code={exit_code}\n"
        f"--- stdout ---\n{stdout}\n"
        f"--- stderr ---\n{stderr}"
    )
    return _truncate(combined)
