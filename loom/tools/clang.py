"""JSON tool schemas (Anthropic input_schema style).

These are intentionally framework-agnostic so they can be used either with
``ChatAnthropic.bind_tools`` (which accepts these dicts) or the raw Anthropic
SDK.
"""

from __future__ import annotations

TOOL_SCHEMAS: list[dict] = [
    {
        "name": "read_file",
        "description": "Read a file and return its contents as a string.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
    {
        "name": "write_file",
        "description": (
            "Write content to a file, creating parent directories as needed. "
            "Overwrites the file if it exists."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
    {
        "name": "edit_file",
        "description": (
            "Replace an exact, unique string match in a file. Fails if the "
            "match is not found or is ambiguous."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_str": {"type": "string"},
                "new_str": {"type": "string"},
            },
            "required": ["path", "old_str", "new_str"],
        },
    },
    {
        "name": "bash",
        "description": (
            "Run a shell command. Returns exit code, stdout, and stderr. "
            "Use for running tests, builds, git, and other CLI tools."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout": {
                    "type": "integer",
                    "description": "Timeout in seconds (default 30).",
                },
            },
            "required": ["command"],
        },
    },
    {
        "name": "glob",
        "description": "Find files matching a glob pattern (e.g. '**/*.py').",
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "root": {"type": "string"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "grep",
        "description": (
            "Search file contents for a pattern. Returns matching lines with "
            "file:line:content."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string"},
                "ignore_case": {"type": "boolean"},
            },
            "required": ["pattern"],
        },
    },
    {
        "name": "web_search",
        "description": (
            "Search the web for a query and return a list of results with "
            "titles, URLs, and snippets. Use this to find current information, "
            "docs, or facts not in your training data. No API key required."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {
                    "type": "integer",
                    "description": "Max results to return (default 5).",
                },
            },
            "required": ["query"],
        },
    },
    {
        "name": "fetch_url",
        "description": (
            "Download and read the contents of a web page or URL. Returns the "
            "readable text (HTML stripped). Use after web_search to read a page."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "max_chars": {
                    "type": "integer",
                    "description": "Max characters to return (default 12000).",
                },
            },
            "required": ["url"],
        },
    },
]
