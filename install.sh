#!/usr/bin/env bash
set -euo pipefail

LOOM_VERSION="${LOOM_VERSION:-latest}"
LOOM_INSTALL_DIR="${LOOM_INSTALL_DIR:-$HOME/.loom}"
REPO="anomalyco/loom-CLI"

HEADER=$(cat <<'GOAT'
      ▐   ▐
    ▄███████▄
   ██  ▐ ▐  ██
   ██       ██
    ▀███████▀
     ▄▀   ▀▄
GOAT
)

warn() { printf "\033[33m! %s\033[0m\n" "$*" >&2; }
info() { printf "\033[36m* %s\033[0m\n" "$*"; }
ok()   { printf "\033[32m✓ %s\033[0m\n" "$*"; }
die()  { printf "\033[31m✗ %s\033[0m\n" "$*" >&2; exit 1; }

# --- Python check ---
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        VER=$("$cmd" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")' 2>/dev/null || true)
        if [ -n "$VER" ] && [ "$(echo "$VER" | cut -d. -f1)" -ge 3 ] && [ "$(echo "$VER" | cut -d. -f2)" -ge 11 ]; then
            PYTHON="$cmd"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    die "Python 3.11+ is required. Install it from https://python.org then re-run this script."
fi
ok "Found $PYTHON $VER"

# --- pip / pipx ---
install_loom() {
    # Prefer pipx for isolated install
    if command -v pipx &>/dev/null; then
        info "Installing via pipx..."
        pipx install "git+https://github.com/$REPO.git" 2>&1 | tail -1
        ok "loom installed via pipx"
        return
    fi

    if ! command -v pip &>/dev/null && ! "$PYTHON" -m pip &>/dev/null; then
        info "pip not found — bootstrapping..."
        curl -sS https://bootstrap.pypa.io/get-pip.py | "$PYTHON"
    fi

    PIP=("$PYTHON" -m pip)
    info "Installing via pip..."
    "${PIP[@]}" install --user "git+https://github.com/$REPO.git" 2>&1 | tail -1

    # Warn if ~/.local/bin not on PATH
    if ! echo "$PATH" | grep -q "$HOME/.local/bin"; then
        warn "Add ~/.local/bin to your PATH:"
        warn "  export PATH=\"\$HOME/.local/bin:\$PATH\""
        warn "Then add it to ~/.bashrc / ~/.zshrc"
    fi
    ok "loom installed via pip"
}

install_loom

# --- Verify ---
if ! command -v loom &>/dev/null; then
    die "loom command not found after install. Check PATH or open an issue at https://github.com/$REPO/issues"
fi
ok "loom $(loom --version 2>/dev/null || echo 'installed')"

# --- Config directory ---
mkdir -p "$LOOM_INSTALL_DIR"

# --- API key setup ---
setup_key() {
    local provider="$1" var="$2" prompt="$3"
    if [ -n "${!var:-}" ]; then
        info "$provider: using \$$var from environment"
        return
    fi
    printf "\n  %s API key (or press Enter to skip): " "$prompt" >&2
    read -r key </dev/tty || true
    if [ -n "$key" ]; then
        printf "%s=%s\n" "$var" "$key" >> "$LOOM_INSTALL_DIR/env"
        ok "$provider API key saved to $LOOM_INSTALL_DIR/env"
    fi
}

touch "$LOOM_INSTALL_DIR/env"
setup_key "Anthropic"  "ANTHROPIC_API_KEY"  "Anthropic"
setup_key "OpenRouter" "OPENROUTER_API_KEY" "OpenRouter"
setup_key "Groq"       "GROQ_API_KEY"       "Groq"
setup_key "NVIDIA"     "NVIDIA_API_KEY"     "NVIDIA"

# --- Done ---
printf "\n%s\n\n" "$HEADER"
ok "loom CLI is ready."
info "Quick start:"
info "  loom --help"
info "  loom chat"
info ""
info "Set your default provider:"
info "  export LOOM_PROVIDER=groq"
info ""
info "Need help?  https://github.com/$REPO/issues"
