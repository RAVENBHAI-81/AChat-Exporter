#!/usr/bin/env bash
# ================================================================
#   AChat Exporter — Installer
#   Supports: Termux (Android), Linux, macOS
#
#   Usage:
#     curl -fsSL https://raw.githubusercontent.com/RAVENBHAI-81/AChat-Exporter/main/install.sh | bash
#   or:
#     bash install.sh
# ================================================================

set -e

VERSION="1.0.0"
REPO="RAVENBHAI-81/AChat-Exporter"
RAW_URL="https://raw.githubusercontent.com/${REPO}/main/achat.py"
RELEASE_URL="https://github.com/${REPO}/releases/latest/download/achat.py"

# ── Colors ───────────────────────────────────────────────────────
R="\033[0m"; BOLD="\033[1m"; DIM="\033[2m"
RED="\033[91m"; GRN="\033[92m"; YLW="\033[93m"
BLU="\033[94m"; MAG="\033[95m"; CYN="\033[96m"; WHT="\033[97m"

say()  { echo -e "  ${CYN}·${R} $*"; }
ok()   { echo -e "  ${GRN}${BOLD}✔${R}  $*"; }
warn() { echo -e "  ${YLW}⚠${R}  $*"; }
die()  { echo -e "  ${RED}✗${R}  $*"; exit 1; }
br()   { echo; }

# ── Banner ───────────────────────────────────────────────────────
echo
echo -e "  ${CYN}${BOLD}╔══════════════════════════════════════════════════════════╗${R}"
echo -e "  ${CYN}${BOLD}║${R}   ${WHT}${BOLD}AChat Exporter${R}  ${DIM}v${VERSION}${R}  —  ${MAG}by Raven RX${R}                    ${CYN}${BOLD}║${R}"
echo -e "  ${CYN}${BOLD}║${R}   ${DIM}Installer for Termux / Linux / macOS${R}                ${CYN}${BOLD}║${R}"
echo -e "  ${CYN}${BOLD}╚══════════════════════════════════════════════════════════╝${R}"
br

# ── Detect environment ───────────────────────────────────────────
IS_TERMUX=false
IS_MACOS=false
IS_LINUX=false
INSTALL_DIR=""

if [ -n "$PREFIX" ] && echo "$PREFIX" | grep -q "com.termux"; then
    IS_TERMUX=true
    INSTALL_DIR="$PREFIX/bin"
elif [ "$(uname -s)" = "Darwin" ]; then
    IS_MACOS=true
    INSTALL_DIR="$HOME/.local/bin"
else
    IS_LINUX=true
    INSTALL_DIR="$HOME/.local/bin"
fi

say "Detected environment:"
$IS_TERMUX && say "  ${CYN}Android (Termux)${R}"
$IS_MACOS  && say "  ${CYN}macOS${R}"
$IS_LINUX  && say "  ${CYN}Linux${R}"
br

# ── Check Python ─────────────────────────────────────────────────
say "Checking Python 3..."
if ! command -v python3 &>/dev/null; then
    br
    warn "Python 3 not found."
    if $IS_TERMUX; then
        say "Install it with:  ${CYN}pkg install python${R}"
    elif $IS_MACOS; then
        say "Install it with:  ${CYN}brew install python3${R}"
    else
        say "Install it with:  ${CYN}sudo apt install python3${R}  or your package manager"
    fi
    die "Please install Python 3 and run this installer again."
fi
PY_VER=$(python3 --version 2>&1)
ok "$PY_VER"

# ── Optional: cloudscraper ────────────────────────────────────────
br
say "Checking optional dependency: cloudscraper (for Claude export)..."
if python3 -c "import cloudscraper" 2>/dev/null; then
    ok "cloudscraper already installed"
else
    warn "cloudscraper not installed — Claude exports will be unavailable."
    say "You can install it anytime with:"
    if $IS_TERMUX; then
        say "  ${CYN}pip install cloudscraper${R}"
    else
        say "  ${CYN}pip install cloudscraper --break-system-packages${R}"
    fi
fi

# ── Create install directory ──────────────────────────────────────
br
say "Install directory: ${WHT}${INSTALL_DIR}${R}"
mkdir -p "$INSTALL_DIR"

# ── Download achat.py ─────────────────────────────────────────────
br
say "Downloading achat.py from GitHub..."

DEST="${INSTALL_DIR}/achat"
TMP="${DEST}.tmp"

# Try release asset first, fall back to raw main
if command -v curl &>/dev/null; then
    if curl -fsSL --max-time 30 -o "$TMP" "$RELEASE_URL" 2>/dev/null; then
        ok "Downloaded from release"
    elif curl -fsSL --max-time 30 -o "$TMP" "$RAW_URL" 2>/dev/null; then
        ok "Downloaded from main branch"
    else
        die "Download failed. Check your internet connection."
    fi
elif command -v wget &>/dev/null; then
    if wget -q --timeout=30 -O "$TMP" "$RELEASE_URL" 2>/dev/null; then
        ok "Downloaded from release"
    elif wget -q --timeout=30 -O "$TMP" "$RAW_URL" 2>/dev/null; then
        ok "Downloaded from main branch"
    else
        die "Download failed. Check your internet connection."
    fi
else
    die "Neither curl nor wget found. Install one and try again."
fi

# ── Validate the download ─────────────────────────────────────────
if ! python3 -c "import ast; ast.parse(open('$TMP').read())" 2>/dev/null; then
    rm -f "$TMP"
    die "Downloaded file is not valid Python. Download may be corrupt."
fi

mv "$TMP" "$DEST"
chmod +x "$DEST"
ok "Installed → ${WHT}${DEST}${R}"

# ── Create AChat data folder ──────────────────────────────────────
br
ACHAT_DIR="$HOME/AChat"
say "Creating data folder: ${WHT}${ACHAT_DIR}${R}"
mkdir -p "$ACHAT_DIR/exports/deepseek"
mkdir -p "$ACHAT_DIR/exports/grok"
mkdir -p "$ACHAT_DIR/exports/chatgpt"
mkdir -p "$ACHAT_DIR/exports/claude"
mkdir -p "$ACHAT_DIR/search_index"
ok "Data folder ready"

# ── PATH check ────────────────────────────────────────────────────
br
if echo "$PATH" | grep -q "$INSTALL_DIR"; then
    ok "${INSTALL_DIR} is already in PATH"
else
    warn "${INSTALL_DIR} is not in your PATH"
    br
    say "Add it by running the following (and add it to your shell rc file):"
    br
    if $IS_TERMUX; then
        say "  ${CYN}echo 'export PATH=\"\$PATH:${INSTALL_DIR}\"' >> ~/.bashrc && source ~/.bashrc${R}"
    else
        SHELL_RC="$HOME/.bashrc"
        [ -f "$HOME/.zshrc" ] && SHELL_RC="$HOME/.zshrc"
        say "  ${CYN}echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ${SHELL_RC} && source ${SHELL_RC}${R}"
    fi
fi

# ── Done! ─────────────────────────────────────────────────────────
br
echo -e "  ${CYN}${BOLD}──────────────────────────────────────────────────────────${R}"
br
echo -e "  ${GRN}${BOLD}🎉  AChat Exporter v${VERSION} installed!${R}"
br
say "Run it with:  ${CYN}${BOLD}achat${R}"
say "Or:           ${CYN}${BOLD}achat <share_url>${R}"
br
say "${DIM}GitHub: github.com/${REPO}${R}"
say "${DIM}by Raven RX — Founder of RX Network Security Labs${R}"
br
echo -e "  ${CYN}${BOLD}──────────────────────────────────────────────────────────${R}"
br
