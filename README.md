# 🧵 loom - Terminal Agentic Coding Assistant

![version](https://img.shields.io/badge/version-0.1.0-blue)
![python](https://img.shields.io/badge/python-3.11%2B-blue)
![license](https://img.shields.io/badge/license-MIT-green)
![tests](https://img.shields.io/badge/tests-35%20passing-brightgreen)

> 🚀 **loom** is a terminal-based agentic coding CLI. Give it a natural-language
> task and it reads/edits files, runs shell commands, searches your project,
> and - via OpenRouter - can even search the web, iterating until the job is done.

```ansi
[1;96m██╗      ██████╗  ██████╗ ███╗   ███╗[0m
[1;94m██║     ██╔═══██╗██╔═══██╗████╗ ████║[0m
[1;95m██║     ██║   ██║██║   ██║██╔████╔██║[0m
[1;95m██║     ██║   ██║██║   ██║██║╚██╔╝██║[0m
[1;93m███████╗╚██████╔╝╚██████╔╝██║ ╚═╝ ██║[0m
[1;92m╚══════╝ ╚═════╝  ╚═════╝ ╚═╝     ╚═╝[0m
[1;91m ✦ a terminal agentic coding assistant[0m
```

---

## ✨ Features

- 🌈 **Colorful UI** - rainbow-gradient ASCII banner + animated braille spinner.
- 🌐 **Multi-provider** - Anthropic, OpenRouter, NVIDIA, Groq, switchable live in chat.
- 🧠 **Live model picker** - browse 300+ models with context sizes; filter by vendor.
- 🔧 **Tool-use agent** - reads/writes/edits files, runs shell, globs, greps.
- 🌍 **Web tools** - `web_search` + `fetch_url` for research-augmented coding.
- 👀 **`/serve`** - preview static sites over HTTP, opened in your browser.
- 💬 **Modern REPL** - colored prompt, `/` autocomplete, bottom toolbar.
- 🛡 **Safe by default** - confirmation prompts + a hard destructive-command denylist.
- 💾 **Session history** - local SQLite persistence with `--resume`.

---

## 📦 Install (dev)

```bash
pip install -e ".[dev]"
```

Requires Python 3.11+.

---

## 🔑 Setup

loom supports **Anthropic**, **OpenRouter**, **NVIDIA**, and **Groq**. Set the
key for whichever provider(s) you use:

```bash
export ANTHROPIC_API_KEY=sk-...        # Anthropic
export OPENROUTER_API_KEY=sk-or-...    # OpenRouter
export NVIDIA_API_KEY=nvapi-...        # NVIDIA
export GROQ_API_KEY=gsk_...            # Groq
```

Or set a default provider + keys in `~/.loom/config.toml` (or a project `.env`):

```toml
provider = "groq"                 # anthropic | openrouter | nvidia | groq
model = "llama-3.3-70b-versatile"
permission_mode = "confirm"       # confirm | yolo | deny
```

> 💡 Keys are resolved in this order: env var > project `.env` > `~/.loom/.env` >
> `config.toml`. Paste a key directly in chat and it's kept for the session
> (or saved to `.env` with `y`).

---

## 🎨 The colorful banner & animation

On startup `loom chat` prints the **rainbow-gradient LOOM banner** (shown
above) using a GitHub-compatible ```` ```ansi ```` block. Before each agent turn
a small **braille spinner** (`⠋ thinking…`) animates to show the agent is
working. Both gracefully fall back to plain text when output isn't a color
terminal (piped logs, CI).

---

## 🛠 Usage

```bash
loom "read main.py and tell me what it does"
loom --provider groq "refactor utils.py to use pathlib"
loom --provider openrouter --model anthropic/claude-3.5-sonnet "explain this repo"
loom --provider nvidia "add a test for utils"
loom --yolo "refactor utils.py to use pathlib"
loom --resume <session_id> "continue where we left off"
loom models --provider groq       # list all available models
loom sessions                     # list past sessions
loom chat --provider groq         # interactive multi-turn chat
```

### 💬 Interactive chat - commands

`loom chat` is a modern REPL: colored prompt, `/` command autocomplete, and a
bottom toolbar. Commands (type `/` to see them, or `/commands`):

| Command      | What it does |
|--------------|--------------|
| `/commands`  | 📜 list all commands |
| `/clear`     | 🧹 drop conversation history |
| `/models`    | 🧠 list models for the **active provider** (live from `/models` endpoint) - filter by typing a vendor (e.g. `openai`, `qwen`) |
| `/provider`  | 🌐 switch provider live (groq / openrouter / nvidia / anthropic) - paste a key in chat if missing |
| `/serve`     | 🌍 serve a folder over HTTP and open it in your browser (`/serve portfolio`) |
| `/help`      | ❓ show help |
| `/exit`      | 🚪 quit (Ctrl-C / Ctrl-D also) |

**Live provider + model switching.** While chatting you can:

```
> /provider
  1. anthropic  2. openrouter  3. nvidia  4. groq *
> 2
> /models            # now shows OpenRouter's 300+ models with ctx sizes
> claude             # filter to anthropic/claude-* models
> 3                  # pick one
```

No key for the chosen provider? loom prompts you to **paste it right there** -
used for the session, or saved to `.env` with `y`.

> ⚠️ Note: OpenRouter is a *router* - its model list includes models from many
> vendors (`openai/...`, `anthropic/...`, `qwen/...`). Each is shown with its
> upstream vendor in brackets. To see a vendor's own models only, run
> `/provider` and pick that vendor.

---

## 🧰 Tools the agent can use

| Tool         | Kind      | Description |
|--------------|-----------|-------------|
| 📄 `read_file`  | read-only | read a file's contents |
| ✏️ `write_file` | write     | create/overwrite a file |
| 🔧 `edit_file`  | write     | replace an exact string in a file |
| 💻 `bash`       | shell     | run a shell command; server commands (`http.server`, `uvicorn`, ...) run in the background so the chat stays responsive |
| 🔍 `glob`       | read-only | find files by glob pattern |
| 📚 `grep`       | read-only | search file contents (ripgrep, with Python fallback) |
| 🌐 `web_search` | read-only | search the web (DuckDuckGo, no API key) |
| 📰 `fetch_url`  | read-only | download & read a web page (HTML stripped to text) |

Read-only tools (file reads, search, web) run without a prompt. Write/shell
tools prompt for confirmation `[y/N/always]` unless `--yolo`.

---

## 📦 Pack / Dependencies

Defined in `pyproject.toml` (Python >= 3.11):

**Runtime libraries:**

| 📚 Library | 🏷 Version | 📝 Role |
|-----------|-----------|---------|
| `langgraph` | >=0.2.0 | 🕸 agent loop / graph orchestration |
| `langchain-core` | >=0.3.0 | 🧩 model + message abstractions |
| `langchain-anthropic` | >=0.2.0 | 🤖 Anthropic (Claude) client |
| `langchain-openai` | >=0.2.0 | 🔑 OpenAI-compatible client (Groq/NVIDIA/OpenRouter) |
| `typer` | >=0.12.0 | ⌨️ CLI framework |
| `rich` | >=13.0.0 | 🎨 terminal rendering |
| `anthropic` | >=0.40.0 | 🧠 Anthropic SDK |
| `prompt-toolkit` | >=3.0.0 | 💬 interactive input box |

**Dev libraries:**

| 📚 Library | 🏷 Version | 📝 Role |
|-----------|-----------|---------|
| `pytest` | >=8.0.0 | 🧪 tests |

Install everything (incl. dev): `pip install -e ".[dev]"`. The `loom` console
script is registered automatically via `[project.scripts]`.

---

## 🛡 Safety

Before any write or shell action, loom prompts for confirmation (unless
`--yolo`). A hard **denylist** blocks obviously destructive commands
(e.g. `rm -rf /`, fork bombs) regardless of mode.

---

## 🌐 Provider reference

| Provider    | Base URL                              | Default model                  |
|-------------|---------------------------------------|--------------------------------|
| anthropic   | (native SDK)                          | claude-sonnet-4-6              |
| openrouter  | https://openrouter.ai/api/v1          | anthropic/claude-3.5-sonnet    |
| nvidia      | https://integrate.api.nvidia.com/v1   | meta/llama-3.1-70b-instruct    |
| groq        | https://api.groq.com/openai/v1        | llama-3.3-70b-versatile        |

---

## 🏗 Architecture

```
loom/
  cli.py          typer entry point (chat, models, sessions, one-shot)
  agent/          LangGraph loop, prompts, streaming
  tools/          file / shell / search / web tools + executor
  session/        SQLite persistence + project tree
  ui/             rich rendering, colorful logo, permission prompts
  config.py       multi-provider config loading
  provider.py     chat-model builder + live model listing
```

---

## ✨ What loom is best for

- 🖥 **Local, keyboard-driven coding help** - refactors, explanations, tests, and
  bug-hunts across your own repo without leaving the terminal.
- 🔁 **Multi-model experimentation** - flip between Groq (fast/cheap), OpenRouter
  (huge model catalog, 300+ including GPT / Claude / Gemini / Qwen), NVIDIA,
  and Anthropic in the same session to compare answers.
- 🔎 **Research-augmented tasks** - combine repo edits with `web_search` +
  `fetch_url` to pull in current docs or APIs while coding.
- 👀 **Quick previews** - `/serve` spins up a local web server for static sites
  (portfolios, docs) and opens them in your browser.
- ⚙️ **Scriptable automation** - one-shot `loom "..."` calls and `--resume` make
  it easy to drop into shell scripts or CI-adjacent workflows.

---

## ⚠️ Reminders / Info

- 🔐 **Rotate your keys.** API keys were pasted into chat history during
  development - treat them as exposed and regenerate them in your provider
  dashboards.
- 🎨 **Colors render on GitHub.** The banner uses a ```` ```ansi ```` block, so
  it shows in color on GitHub and in any truecolor terminal (`cat README.md`).
- 🚫 **Denylist always wins.** Even in `--yolo`, destructive commands are blocked.
- 💾 **Sessions are local.** Chat history is stored in a local SQLite DB
  (`~/.loom/...`); nothing is sent anywhere except to your chosen LLM provider.
- 🧪 Run the tests with `pytest`.

---

## 🧪 Tests

```bash
pytest
```
