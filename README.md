# Loom CLI

A terminal-based agentic coding assistant. Talk to your codebase in natural language, spawn multi-agent pipelines, and accelerate development — all without leaving your shell.

## Install

```bash
curl -fsSL https://loom.dev/install | bash
```

Requires Python 3.11+. Supports Anthropic, OpenRouter, NVIDIA, and Groq providers.

## Quick Start

```bash
loom --help
loom chat
```

## Features

- Interactive chat with slash commands (`/clear`, `/models`, `/graph`, `/summarize`, etc.)
- Multi-agent architecture pipeline (`/architect`, `/multi`)
- Workspace indexing and smart context (`/index`, `/context`)
- Knowledge graph (`/graph`)
- Session memory with SQLite
- Git integration and checkpoints
- Plugin and MCP server support
- Permission modes (confirm / yolo)

## Website

The `website/` directory contains a single-page marketing site. Open `website/index.html` in a browser or serve locally:

```bash
loom serve website
```