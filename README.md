<div align="center">

# AChat Exporter

**Export AI chats from DeepSeek, Grok, ChatGPT & Claude — from your terminal.**

[![Version](https://img.shields.io/badge/version-1.0.0-22c55e?style=flat-square)](https://github.com/RAVENBHAI-81/AChat-Exporter/releases)
[![Python](https://img.shields.io/badge/python-3.8+-3b82f6?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-a855f7?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/platform-Android%20%7C%20Linux%20%7C%20macOS%20%7C%20Windows-f97316?style=flat-square)](https://github.com/RAVENBHAI-81/AChat-Exporter)
[![RNSL](https://img.shields.io/badge/by-RX%20Network%20Security%20Labs-ef4444?style=flat-square)](https://github.com/RX-Network-Security-Labs)

<br>

*A creation of **RX Network Security Labs** — We build what has never existed.*

</div>

---

## What it does

AChat Exporter is a **zero-dependency** terminal tool that grabs any AI chat from a share URL and exports it to Markdown, HTML, plain text, or JSON — in seconds.

- 🔒 **Fully local.** Nothing is sent anywhere except to the platform's own API.
- ⚡ **Fast.** No Electron. No browser automation. Pure Python.
- 📱 **Works on Termux.** Built first for Android.
- 🎨 **Beautiful HTML.** Dark-themed, self-contained, shareable.
- 🧠 **Smart.** Duplicate detection, search index, re-export from history.

---

## Supported Platforms

| Platform | Status | Share URL format |
|---|---|---|
| 🤖 **DeepSeek** | ✅ Stable | `chat.deepseek.com/share/<id>` |
| 🐦 **Grok** | ✅ Stable | `grok.com/share/<id>` |
| 💬 **ChatGPT** | ✅ Stable | `chatgpt.com/share/<id>` |
| 🟠 **Claude** | ⚠️ Experimental | `claude.ai/share/<uuid>` |

> **Claude note:** Claude.ai uses aggressive Cloudflare protection. Claude exports require `cloudscraper` and may occasionally fail depending on your network. Try again or use a VPN if it fails.

---

## Install

### Android (Termux)

```bash
curl -fsSL https://raw.githubusercontent.com/RAVENBHAI-81/AChat-Exporter/main/install.sh | bash
```

Or manually:
```bash
pkg install python
pip install cloudscraper   # optional, for Claude exports
curl -fsSL https://raw.githubusercontent.com/RAVENBHAI-81/AChat-Exporter/main/achat.py -o $PREFIX/bin/achat
chmod +x $PREFIX/bin/achat
```

### Linux / macOS

```bash
curl -fsSL https://raw.githubusercontent.com/RAVENBHAI-81/AChat-Exporter/main/install.sh | bash
```

Or manually:
```bash
mkdir -p ~/.local/bin
curl -fsSL https://raw.githubusercontent.com/RAVENBHAI-81/AChat-Exporter/main/achat.py -o ~/.local/bin/achat
chmod +x ~/.local/bin/achat
# Make sure ~/.local/bin is in your PATH
```

### Windows

Download `install.bat` from [Releases](https://github.com/RAVENBHAI-81/AChat-Exporter/releases/latest) and run it. Requires Python 3.8+ from [python.org](https://python.org).

---

## Usage

### Interactive TUI

```bash
achat
```

Arrow-key menu. Select a platform, paste links, pick format.

### Quick export (auto-detect platform)

```bash
achat https://chat.deepseek.com/share/abc123
achat https://grok.com/share/xyz789
achat https://chatgpt.com/share/def456
```

### Full CLI

```bash
achat -p deepseek -f html https://chat.deepseek.com/share/abc123
achat -p grok -f md -o ~/my-chats https://grok.com/share/xyz
achat -p chatgpt --no-think -f txt https://chatgpt.com/share/...
```

### Built-in tools

```bash
achat search "docker setup"       # Search all exported files
achat stats ~/AChat/exports/x.md  # Word count, top words
achat diff                        # Compare two exports
achat merge                       # Merge multiple exports
achat --update                    # Self-update to latest release
achat --version                   # Show version
```

---

## CLI Flags

| Flag | Short | Description |
|---|---|---|
| `--platform` | `-p` | Force platform: `deepseek`, `grok`, `chatgpt`, `claude` |
| `--format` | `-f` | Output format: `md`, `html`, `txt`, `json` |
| `--output` | `-o` | Custom output folder |
| `--think` | | Include thinking/reasoning blocks |
| `--no-think` | | Strip thinking blocks |
| `--update` | | Check GitHub and self-update |
| `--version` | | Show version and exit |

---

## Output Formats

| Format | Description |
|---|---|
| **Markdown** (`.md`) | Clean GitHub-compatible markdown with collapsible thinking blocks |
| **HTML** (`.html`) | Fully self-contained dark-themed page — no external dependencies |
| **Plain Text** (`.txt`) | Simple readable text with ASCII dividers |
| **JSON** (`.json`) | Raw structured data for further processing |

---

## Data Structure

All data lives in `~/AChat/`:

```
~/AChat/
├── exports/
│   ├── deepseek/    ← DeepSeek exports
│   ├── grok/        ← Grok exports
│   ├── chatgpt/     ← ChatGPT exports
│   └── claude/      ← Claude exports
├── search_index/    ← Fast keyword search index
├── history.json     ← Export history (last 200)
├── cache.json       ← Duplicate detection cache
└── config.json      ← Your preferences
```

The script itself lives at `~/.local/bin/achat` (Linux/macOS) or `%USERPROFILE%\.local\bin\achat.py` (Windows), out of sight.

---

## Self-Update

```bash
achat --update
```

Or from inside the TUI → **Check for update**. Downloads the latest `achat.py` from [Releases](https://github.com/RAVENBHAI-81/AChat-Exporter/releases/latest) and replaces itself atomically using `os.replace()`. No package manager, no root.

---

## Requirements

- Python 3.8+
- Zero pip packages for core features
- `cloudscraper` (optional) — only for Claude exports:
  ```bash
  pip install cloudscraper            # Termux
  pip install cloudscraper --break-system-packages  # Linux/macOS system Python
  ```

---

## Contributing

Pull requests are welcome! See the [issue templates](.github/ISSUE_TEMPLATE/) for bug reports, feature requests, and platform requests.

If you found a new AI chat platform that has a public share URL — especially if you've already reverse-engineered its API — [open a Platform Request](https://github.com/RAVENBHAI-81/AChat-Exporter/issues/new?template=platform_request.md) or submit a PR.

---

## License

MIT © 2026 **Raven RX — Founder of RX Network Security Labs**

---

<div align="center">

**RX Network Security Labs**

*Build what has never existed.*

[GitHub](https://github.com/RX-Network-Security-Labs) · [Telegram](https://t.me/rxnetworksecuritylabs) · [Discord](https://discord.gg/nWt82zV3s4)

</div>
