<p align="center">
  <pre>
    ▐   ▐
  ▄███████▄                    ██╗      ██████╗  ██████╗ ███╗   ███╗
 ██  ▐ ▐  ██                   ██║     ██╔═══██╗██╔═══██╗████╗ ████║
 ██       ██                   ██║     ██║   ██║██║   ██║██╔████╔██║
  ▀███████▀                    ██║     ██║   ██║██║   ██║██║╚██╔╝██║
   ▄▀   ▀▄                     ███████╗╚██████╔╝╚██████╔╝██║ ╚═╝ ██║
                               ╚══════╝ ╚═════╝  ╚═════╝ ╚═╝     ╚═╝
  </pre>
</p>

<h1 align="center">LOOM CLI</h1>

<p align="center">
  <b>Agentic coding in your terminal</b><br>
  Talk to your codebase, spawn multi-agent pipelines, and ship faster.
</p>

<p align="center">
  <a href="https://USIF-Andreas.github.io/loom-CLI"><img src="https://img.shields.io/badge/website-live-7c3aed?style=flat-square&logo=githubpages&logoColor=white" alt="Website"></a>
  <a href="#install"><img src="https://img.shields.io/badge/python-3.11%2B-22d3ee?style=flat-square&logo=python&logoColor=white" alt="Python"></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-a78bfa?style=flat-square" alt="License"></a>
  <a href="https://github.com/USIF-Andreas/loom-CLI/actions"><img src="https://img.shields.io/github/actions/workflow/status/USIF-Andreas/loom-CLI/pages.yml?style=flat-square&label=deploy&color=c084fc" alt="Deploy"></a>
</p>

---

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/USIF-Andreas/loom-CLI/main/install.sh | bash
```

**Requirements:** Python 3.11+ · Pip or pipx

<details>
<summary><b>Manual install</b></summary>

```bash
pip install git+https://github.com/USIF-Andreas/loom-CLI.git
# or
git clone https://github.com/USIF-Andreas/loom-CLI.git
cd loom-CLI
pip install -e .
```
</details>

---

## Quick Start

```bash
# Start chatting with your codebase
loom chat

# List everything
loom --help

# Switch provider on the fly
/models
/provider groq
```

Set your API key:
```bash
export ANTHROPIC_API_KEY=sk-...
# or
echo 'ANTHROPIC_API_KEY=sk-...' >> ~/.loom/.env
```

---

## Features

| Category | Tools |
|----------|-------|
| **Chat** | `/clear` `/summarize` `/help` — persistent sessions with SQLite memory |
| **Code** | `/index` `/context` `/graph` — index your workspace, search symbols, trace imports |
| **Agents** | `/architect` `/multi` — multi-agent pipelines: plan → research → code → review → test → summary |
| **Dev** | `/git` `/checkpoint` `/test` `/bench` — git integration, checkpoints, test runner, benchmarks |
| **Extend** | `/plugins` `/mcp` `/tools` — custom tools, MCP servers, plugin system |
| **Memory** | `/remember` `/forget` — persistent key-value memory across sessions |

### Supported Providers

<p>
  <img src="https://img.shields.io/badge/Anthropic-f97316?style=flat-square&logo=anthropic&logoColor=white" alt="Anthropic">
  <img src="https://img.shields.io/badge/OpenRouter-22d3ee?style=flat-square&logo=openai&logoColor=black" alt="OpenRouter">
  <img src="https://img.shields.io/badge/NVIDIA-76b900?style=flat-square&logo=nvidia&logoColor=white" alt="NVIDIA">
  <img src="https://img.shields.io/badge/Groq-c084fc?style=flat-square&logo=groq&logoColor=white" alt="Groq">
  <img src="https://img.shields.io/badge/Vercel-6366f1?style=flat-square&logo=vercel&logoColor=white" alt="Vercel">
</p>

---

## Usage

### Interactive Chat

```
┏━━ LOOM ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃  ▐   ▐                                    ┃
┃ ▄███████▄                                  ┃
┃ ██  ▐ ▐  ██    groq · llama-3.3-70b       ┃
┃  ▀███████▀     type / for commands         ┃
┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛

> explain the auth flow
✓ Found auth middleware in src/middleware/auth.js
The JWT validation chain checks tokens against Redis...
```

### Architect Pipeline

```bash
> /architect "add dark mode to the settings page"
```

Spawns four agents: **architect** (plan) → **researcher** (gather context) → **coder** (implement) → **reviewer** (validate).

### One-shot Multi-Agent

```bash
> /multi "refactor the payment service to use Stripe"
```

Runs the full pipeline: plan → research → code → review → test → summary in one command.

---

## Configuration

**`~/.loom/.env`** — API keys and defaults:

```env
ANTHROPIC_API_KEY=sk-...
OPENROUTER_API_KEY=...
NVIDIA_API_KEY=...
GROQ_API_KEY=...
LOOM_DEFAULT_PROVIDER=groq
LOOM_DEFAULT_MODEL=llama-3.3-70b
```

Or pass flags:
```bash
loom chat --provider openrouter --model anthropic/claude-3.5-sonnet
```

---

## Project Structure

```
loom/
├── cli.py              # Main CLI entrypoint + chat loop
├── config.py           # Providers, config loading
├── provider.py         # Model listing
├── agent/              # LangGraph agent pipeline
│   ├── graph.py        # Agent graph with tools
│   └── state.py        # State schema
├── tools/              # Tool implementations
├── ui/                 # Terminal rendering
│   ├── render.py       # Role-based text output
│   ├── logo.py         # Logo and animations
│   └── commands.py     # Slash command system
├── architect/          # Multi-agent orchestration
├── session/            # SQLite session storage
└── multiagent/         # One-shot pipeline
website/                # Marketing site (GitHub Pages)
install.sh              # Curl-installable script
```

---

## Links

- [Website](https://USIF-Andreas.github.io/loom-CLI) — live demo with ghost game
- [Install](https://raw.githubusercontent.com/USIF-Andreas/loom-CLI/main/install.sh) — one-liner install script
- [GitHub](https://github.com/USIF-Andreas/loom-CLI) — source code

---

<p align="center">
  <sub>Built with ❤️ and Python · MIT License</sub>
</p>
