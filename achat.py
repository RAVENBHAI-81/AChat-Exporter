#!/usr/bin/env python3
# ================================================================
#   AChat Exporter
#   Export AI chats from DeepSeek, Grok, ChatGPT & Claude
#
#   Version : 1.0.0
#   Author  : Raven RX — Founder of RX Network Security Labs
#   GitHub  : github.com/RAVENBHAI-81/AChat-Exporter
#   License : MIT
# ================================================================

import os, sys, json, re, time, shutil, subprocess, argparse, hashlib, difflib
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from collections import Counter

# ── Version ──────────────────────────────────────────────────────
VERSION      = "1.0.0"
GITHUB_REPO  = "RAVENBHAI-81/AChat-Exporter"
GITHUB_API   = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
GITHUB_RAW   = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/achat.py"

# ── Platform detection ───────────────────────────────────────────
IS_WINDOWS = sys.platform.startswith("win")
IS_ANDROID = "com.termux" in os.environ.get("PREFIX", "") or \
             "com.termux" in os.environ.get("HOME", "")

if not IS_WINDOWS:
    import tty, termios

# ── Optional: cloudscraper (Claude only) ─────────────────────────
try:
    import cloudscraper as _cloudscraper
    HAS_CLOUDSCRAPER = True
except ImportError:
    HAS_CLOUDSCRAPER = False

# ════════════════════════════════════════════════════════════════
#   ANSI COLORS
# ════════════════════════════════════════════════════════════════
USE_COLOR = not IS_WINDOWS or os.environ.get("TERM") == "xterm"

R    = "\033[0m"  if USE_COLOR else ""
BOLD = "\033[1m"  if USE_COLOR else ""
DIM  = "\033[2m"  if USE_COLOR else ""
RED  = "\033[91m" if USE_COLOR else ""
GRN  = "\033[92m" if USE_COLOR else ""
YLW  = "\033[93m" if USE_COLOR else ""
BLU  = "\033[94m" if USE_COLOR else ""
MAG  = "\033[95m" if USE_COLOR else ""
CYN  = "\033[96m" if USE_COLOR else ""
WHT  = "\033[97m" if USE_COLOR else ""

# ════════════════════════════════════════════════════════════════
#   PATHS  (cross-platform)
# ════════════════════════════════════════════════════════════════
HOME = os.path.expanduser("~")

if IS_WINDOWS:
    ACHAT_DIR = os.path.join(os.environ.get("USERPROFILE", HOME), "AChat")
else:
    ACHAT_DIR = os.path.join(HOME, "AChat")

CONFIG_FILE   = os.path.join(ACHAT_DIR, "config.json")
HISTORY_FILE  = os.path.join(ACHAT_DIR, "history.json")
CACHE_FILE    = os.path.join(ACHAT_DIR, "cache.json")
EXPORTS_DIR   = os.path.join(ACHAT_DIR, "exports")
SEARCH_DIR    = os.path.join(ACHAT_DIR, "search_index")

PLATFORM_DIRS = {
    "deepseek": os.path.join(EXPORTS_DIR, "deepseek"),
    "grok"    : os.path.join(EXPORTS_DIR, "grok"),
    "chatgpt" : os.path.join(EXPORTS_DIR, "chatgpt"),
    "claude"  : os.path.join(EXPORTS_DIR, "claude"),
}

DEFAULT_CONFIG = {
    "user_name"        : "You",
    "ai_name"          : "AI",
    "default_format"   : "markdown",
    "include_thinking" : True,
    "include_timestamp": False,
    "include_metadata" : False,
    "copy_clipboard"   : False,
}

# ════════════════════════════════════════════════════════════════
#   CONFIG / HISTORY / CACHE
# ════════════════════════════════════════════════════════════════
def setup_dirs():
    for d in [ACHAT_DIR, EXPORTS_DIR, SEARCH_DIR] + list(PLATFORM_DIRS.values()):
        os.makedirs(d, exist_ok=True)

def load_config():
    setup_dirs()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE) as f:
                return {**DEFAULT_CONFIG, **json.load(f)}
        except Exception:
            pass
    return dict(DEFAULT_CONFIG)

def save_config(cfg):
    with open(CONFIG_FILE, "w") as f:
        json.dump(cfg, f, indent=2)

def load_history():
    if os.path.exists(HISTORY_FILE):
        try:
            with open(HISTORY_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_history(hist):
    with open(HISTORY_FILE, "w") as f:
        json.dump(hist[-200:], f, indent=2)

def add_history(platform, title, fmt, path, msg_count, share_id):
    hist = load_history()
    hist.append({
        "platform"   : platform,
        "title"      : title,
        "format"     : fmt,
        "path"       : path,
        "messages"   : msg_count,
        "share_id"   : share_id,
        "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    save_history(hist)

def load_cache():
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {}

def save_cache(cache):
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f, indent=2)

def cache_add(share_id, path):
    cache = load_cache()
    cache[share_id] = {"path": path, "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    save_cache(cache)

def cache_check(share_id):
    return load_cache().get(share_id)

# ════════════════════════════════════════════════════════════════
#   SEARCH INDEX
# ════════════════════════════════════════════════════════════════
def index_file(path, platform, title, share_id):
    """Build/update search index entry for an exported file."""
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
        words = re.findall(r'\b\w{3,}\b', content.lower())
        freq  = Counter(words)
        idx   = {
            "path"       : path,
            "platform"   : platform,
            "title"      : title,
            "share_id"   : share_id,
            "word_count" : len(words),
            "top_words"  : dict(freq.most_common(50)),
            "indexed_at" : datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        ifile = os.path.join(SEARCH_DIR, hashlib.md5(path.encode()).hexdigest() + ".json")
        with open(ifile, "w") as f:
            json.dump(idx, f)
    except Exception:
        pass

def search_exports(query):
    """Search all indexed exports for a keyword. Returns list of matches."""
    terms   = [t.lower() for t in query.strip().split() if t]
    if not terms:
        return []
    results = []
    for fname in os.listdir(SEARCH_DIR):
        if not fname.endswith(".json"):
            continue
        try:
            with open(os.path.join(SEARCH_DIR, fname)) as f:
                idx = json.load(f)
        except Exception:
            continue
        if not os.path.exists(idx.get("path", "")):
            continue
        score = 0
        for t in terms:
            score += idx.get("top_words", {}).get(t, 0)
            if t in idx.get("title", "").lower():
                score += 10
        if score == 0:
            # deep search in actual file
            try:
                with open(idx["path"], encoding="utf-8", errors="ignore") as f:
                    content = f.read().lower()
                if all(t in content for t in terms):
                    score = 1
                    # find context lines
                    lines = content.splitlines()
                    snippets = []
                    for i, line in enumerate(lines):
                        if any(t in line for t in terms):
                            snippets.append(line.strip()[:100])
                            if len(snippets) >= 3:
                                break
                    idx["_snippets"] = snippets
            except Exception:
                continue
        if score > 0:
            idx["_score"] = score
            results.append(idx)
    results.sort(key=lambda x: x.get("_score", 0), reverse=True)
    return results

# ════════════════════════════════════════════════════════════════
#   RAW KEY INPUT
# ════════════════════════════════════════════════════════════════
def read_key():
    if IS_WINDOWS:
        import msvcrt
        ch = msvcrt.getwch()
        if ch in ('\x00', '\xe0'):
            ch2 = msvcrt.getwch()
            return {'H':'UP','P':'DOWN','K':'LEFT','M':'RIGHT'}.get(ch2,'UNK')
        if ch == '\x03': raise KeyboardInterrupt
        if ch in ('\r','\n'): return '\r'
        if ch in ('\x7f','\x08'): return 'BACKSPACE'
        return ch
    else:
        fd  = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == '\x1b':
                ch2 = sys.stdin.read(1)
                if ch2 == '[':
                    ch3 = sys.stdin.read(1)
                    return {'A':'UP','B':'DOWN','C':'RIGHT','D':'LEFT'}.get(ch3,'UNK')
                return 'ESC'
            if ch in ('\x7f','\x08'): return 'BACKSPACE'
            if ch == '\x03': raise KeyboardInterrupt
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)

# ════════════════════════════════════════════════════════════════
#   UI PRIMITIVES
# ════════════════════════════════════════════════════════════════
def clear():
    os.system("cls" if IS_WINDOWS else "clear")

def div():
    print(f"  {DIM}{'─'*50}{R}")

def blank():
    print()

def section(title):
    blank()
    pad = max(0, 46 - len(title))
    print(f"  {BLU}{BOLD}── {title} {'─'*pad}{R}")
    blank()

def info(msg):    print(f"  {CYN}·{R} {msg}")
def success(msg): print(f"  {GRN}{BOLD}✔{R}  {msg}")
def warn(msg):    print(f"  {YLW}⚠{R}  {msg}")
def error(msg):   print(f"  {RED}✗{R}  {msg}")

def ask(prompt, default=""):
    suf = f" {DIM}[{default}]{R}" if default else ""
    val = input(f"  {CYN}>{R} {prompt}{suf}: ").strip()
    return val or default

def ask_yn(prompt, default=False):
    hint = f"{GRN}Y{R}/n" if default else f"y/{RED}N{R}"
    val  = input(f"  {CYN}?{R} {prompt} ({hint}): ").strip().lower()
    return True if val in ('y','yes') else False if val in ('n','no') else default

def print_banner():
    clear()
    W = 64
    def row(content=""):
        plain = re.sub(r'\033\[[^m]*m', '', content)
        pad   = max(0, W - 2 - len(plain))
        print(f"  {CYN}{BOLD}║{R}{content}{' '*pad}{CYN}{BOLD}║{R}")
    print()
    print(f"  {CYN}{BOLD}╔{'═'*W}╗{R}")
    row()
    row(f"    {WHT}{BOLD}    _    ____ _           _   {R}  {CYN}Exporter{R}")
    row(f"    {CYN}{BOLD}   / \\  / ___| |__   __ _| |__{R}")
    row(f"    {CYN}{BOLD}  / _ \\| |   | '_ \\ / _` | __|{R}")
    row(f"    {CYN}{BOLD} / ___ \\ |___| | | | (_| | |_ {R}")
    row(f"    {CYN}{BOLD}/_/   \\_\\____|_| |_|\\__,_|\\__|{R}")
    row()
    row(f"    {GRN}v {VERSION}{R}  {DIM}·{R}  {MAG}by Raven RX{R}  {DIM}·{R}  {DIM}Founder of RX Network Security Labs{R}")
    row()
    print(f"  {CYN}{BOLD}╚{'═'*W}╝{R}")
    print()

# ════════════════════════════════════════════════════════════════
#   ARROW-KEY MENU
# ════════════════════════════════════════════════════════════════
def _is_soon(val):
    return isinstance(val, str) and val.startswith("__soon")

def arrow_menu(options, title=None):
    items = [(o, o) if isinstance(o, str) else o for o in options]

    if IS_WINDOWS:
        selectable = [(i, lbl, val) for i, (lbl, val) in enumerate(items) if not _is_soon(val)]
        if title: print(f"\n  {BLU}{BOLD}{title}{R}\n")
        for idx, (i, lbl, val) in enumerate(selectable, 1):
            print(f"  {CYN}{idx}{R}) {lbl}")
        blank()
        while True:
            try:
                n = int(input(f"  {CYN}>{R} Choose (1-{len(selectable)}): ").strip())
                if 1 <= n <= len(selectable):
                    return selectable[n-1][2]
            except (ValueError, IndexError):
                pass
            error("Invalid choice.")
        return

    sel = 0
    while sel < len(items) and _is_soon(items[sel][1]):
        sel += 1

    def render(s):
        lines = []
        if title:
            lines.append(f"  {BLU}{BOLD}{title}{R}")
            lines.append("")
        for i, (label, val) in enumerate(items):
            soon = _is_soon(val)
            if i == s:
                arrow = f"{CYN}{BOLD}❯{R}"
                lbl   = f"{DIM}{label}{R}" if soon else f"{CYN}{BOLD}{label}{R}"
            else:
                arrow = " "
                lbl   = f"{DIM}  {label}{R}"
            lines.append(f"  {arrow} {lbl}")
        return lines

    lines = render(sel)
    print("\n".join(lines))
    n = len(lines)

    while True:
        k = read_key()
        if k == 'UP':
            nxt = (sel - 1) % len(items)
            while _is_soon(items[nxt][1]): nxt = (nxt - 1) % len(items)
            sel = nxt
        elif k == 'DOWN':
            nxt = (sel + 1) % len(items)
            while _is_soon(items[nxt][1]): nxt = (nxt + 1) % len(items)
            sel = nxt
        elif k in ('\r','\n',' '):
            label, val = items[sel]
            if _is_soon(val): continue
            sys.stdout.write(f"\033[{n}A\033[J")
            print(f"  {GRN}{BOLD}✔{R}  {label}\n")
            return val
        elif k in ('q','Q','ESC','\x03'):
            sys.stdout.write(f"\033[{n}A\033[J")
            raise KeyboardInterrupt

        sys.stdout.write(f"\033[{n}A\033[J")
        lines = render(sel)
        print("\n".join(lines))
        n = len(lines)

# ════════════════════════════════════════════════════════════════
#   CHECKBOX MENU
# ════════════════════════════════════════════════════════════════
def checkbox_menu(options, title=None):
    state = {key: default for _, key, default in options}

    if IS_WINDOWS:
        if title: print(f"\n  {BLU}{BOLD}{title}{R}\n")
        for label, key, _ in options:
            state[key] = ask_yn(label, default=state[key])
        blank()
        return state

    sel = 0

    def render(s):
        lines = []
        if title:
            lines.append(f"  {BLU}{BOLD}{title}{R}")
            lines.append(f"  {DIM}Space to toggle  ·  Enter to confirm{R}")
            lines.append("")
        for i, (label, key, _) in enumerate(options):
            box = f"{GRN}✓{R}" if state[key] else f"{DIM}·{R}"
            if i == s:
                lines.append(f"  {CYN}{BOLD}❯{R} [{box}] {CYN}{BOLD}{label}{R}")
            else:
                lines.append(f"    [{box}] {DIM}{label}{R}")
        return lines

    lines = render(sel)
    print("\n".join(lines))
    n = len(lines)

    while True:
        k = read_key()
        if k == 'UP':   sel = (sel - 1) % len(options)
        elif k == 'DOWN': sel = (sel + 1) % len(options)
        elif k == ' ':  state[options[sel][1]] = not state[options[sel][1]]
        elif k in ('\r','\n'):
            sys.stdout.write(f"\033[{n}A\033[J")
            for label, key, _ in options:
                mark = f"{GRN}✓{R}" if state[key] else f"{DIM}·{R}"
                print(f"    [{mark}] {DIM}{label}{R}")
            blank()
            return state
        elif k in ('q','Q','ESC'):
            sys.stdout.write(f"\033[{n}A\033[J")
            raise KeyboardInterrupt

        sys.stdout.write(f"\033[{n}A\033[J")
        lines = render(sel)
        print("\n".join(lines))
        n = len(lines)

# ════════════════════════════════════════════════════════════════
#   SHARED HELPERS
# ════════════════════════════════════════════════════════════════
def step(icon, platform, current, total, label):
    blank()
    badge = f"{DIM}Step {current}/{total}{R}"
    plat  = f"{CYN}{icon}  {platform}{R}"
    pad   = max(0, 28 - len(label) - len(platform))
    print(f"  {BLU}{BOLD}── {plat}  {badge}  ·  {WHT}{label} {'─'*pad}{R}")
    blank()

def copy_clipboard(text):
    candidates = [
        ["termux-clipboard-set"],
        ["xclip", "-selection", "clipboard"],
        ["xsel", "--clipboard", "--input"],
        ["pbcopy"],
        ["clip.exe"],
    ]
    for cmd in candidates:
        if shutil.which(cmd[0]):
            try:
                p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                p.communicate(input=text.encode())
                return p.returncode == 0
            except Exception:
                continue
    return False

def safe_filename(title, share_id):
    safe = re.sub(r'[^\w\s-]', '', title)[:38].strip().replace(' ', '_') or share_id[:16]
    ts   = datetime.now().strftime("%Y%m%d_%H%M")
    return f"{safe}_{ts}"

def fmt_ext(fmt):
    return {"markdown":"md","text":"txt","html":"html","json":"json"}.get(fmt, "md")

def fetch_url(url, headers, retries=3, delay=2.5, label="Fetching"):
    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    for attempt in range(1, retries + 1):
        lbl = label + (f" {DIM}(retry {attempt}/{retries}){R}" if attempt > 1 else "")
        for i in range(25):
            print(f"\r  {CYN}{frames[i%len(frames)]}{R} {lbl}   ", end="", flush=True)
            time.sleep(0.05)
        req = Request(url, headers=headers)
        try:
            with urlopen(req, timeout=28) as resp:
                raw = resp.read()
            print(f"\r{' '*70}\r", end="")
            return raw
        except HTTPError as e:
            print(f"\r{' '*70}\r", end="")
            if attempt == retries: raise
            warn(f"HTTP {e.code} — retrying in {delay}s...")
            time.sleep(delay)
        except URLError as e:
            print(f"\r{' '*70}\r", end="")
            if attempt == retries: raise
            warn(f"Network error — retrying in {delay}s...")
            time.sleep(delay)

def format_ts(ts):
    try:    return datetime.fromtimestamp(float(ts)).strftime("%Y-%m-%d %H:%M")
    except: return ""

def parse_iso(ts_str):
    try:
        dt = datetime.strptime(str(ts_str)[:19], "%Y-%m-%dT%H:%M:%S")
        return dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        return ""

# ════════════════════════════════════════════════════════════════
#   AUTO PLATFORM DETECTION
# ════════════════════════════════════════════════════════════════
PLATFORM_PATTERNS = {
    "deepseek": [r"chat\.deepseek\.com/share/", r"deepseek\.com/share/"],
    "grok"    : [r"grok\.com/share/"],
    "chatgpt" : [r"chatgpt\.com/share/", r"chat\.openai\.com/share/"],
    "claude"  : [r"claude\.ai/share/"],
}

def detect_platform(url):
    """Auto-detect platform from URL. Returns platform key or None."""
    for platform, patterns in PLATFORM_PATTERNS.items():
        for pat in patterns:
            if re.search(pat, url, re.IGNORECASE):
                return platform
    return None

# ════════════════════════════════════════════════════════════════
#   THINKING BLOCK RENDERERS
# ════════════════════════════════════════════════════════════════
def render_thinking_md(raw):
    def rep(m):
        inner = m.group(1).strip()
        return f"\n<details>\n<summary>💭 Thinking</summary>\n\n{inner}\n\n</details>\n"
    return re.sub(r"__THINK__\n(.*?)\n__/THINK__", rep, raw, flags=re.DOTALL)

def render_thinking_txt(raw):
    def rep(m):
        inner = m.group(1).strip()
        ind   = "\n".join(f"    {l}" for l in inner.splitlines())
        return f"\n┌── Thinking ──────────────────────────\n{ind}\n└──────────────────────────────────────\n"
    return re.sub(r"__THINK__\n(.*?)\n__/THINK__", rep, raw, flags=re.DOTALL)

def render_thinking_html(raw):
    def rep(m):
        inner = m.group(1).strip()
        safe  = inner.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")
        return f'<details class="thinking"><summary>💭 Thinking process</summary><pre>{safe}</pre></details>'
    return re.sub(r"__THINK__\n(.*?)\n__/THINK__", rep, raw, flags=re.DOTALL)

def strip_thinking(raw):
    return re.sub(r"__THINK__\n.*?\n__/THINK__", "", raw, flags=re.DOTALL).strip()

# ════════════════════════════════════════════════════════════════
#   HTML EXPORT BUILDER
# ════════════════════════════════════════════════════════════════
def _esc(s):
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;").replace('"','&quot;')

def _md_to_html(text):
    text = re.sub(r"```(\w+)?\n(.*?)```",
        lambda m: f'<pre><code class="lang-{m.group(1) or ""}">{_esc(m.group(2))}</code></pre>',
        text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", lambda m: f"<code>{_esc(m.group(1))}</code>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*",     r"<em>\1</em>",         text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2" target="_blank">\1</a>', text)
    for i in range(6, 0, -1):
        text = re.sub(r"(?m)^#{%d}\s(.+)$" % i,
                      lambda m, i=i: f"<h{i}>{m.group(1)}</h{i}>", text)
    parts = re.split(r"\n{2,}", text)
    out   = []
    for p in parts:
        p = p.strip()
        if not p: continue
        if p.startswith(("<h","<pre","<hr","<details","<ul","<ol","<blockquote")):
            out.append(p)
        else:
            out.append(f"<p>{p.replace(chr(10),'<br>')}</p>")
    return "\n".join(out)

HTML_PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400&display=swap');
:root{{--bg:#0d1117;--bg2:#161b27;--bg3:#1e2535;--bdr:#2a3347;
--u-bg:rgba(59,130,246,.08);--u-acc:#3b82f6;
--a-bg:rgba(34,197,94,.06);--a-acc:#22c55e;
--th:#1e1a2e;--th-acc:#a78bfa;
--tx:#e2e8f0;--tx-d:#64748b;--tx-m:#94a3b8;--code:#0d1117;--lnk:#60a5fa;}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{background:var(--bg);color:var(--tx);font-family:'Inter',sans-serif;font-size:15px;line-height:1.75;min-height:100vh}}
header{{background:var(--bg2);border-bottom:1px solid var(--bdr);padding:16px 24px;display:flex;align-items:center;gap:12px;position:sticky;top:0;z-index:10;backdrop-filter:blur(8px)}}
.logo{{width:34px;height:34px;background:linear-gradient(135deg,#3b82f6,#22c55e);border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:17px;flex-shrink:0}}
header h1{{font-size:15px;font-weight:600;flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.badges{{display:flex;gap:6px;flex-shrink:0}}
.badge{{font-size:11px;color:var(--tx-d);background:var(--bg3);border:1px solid var(--bdr);border-radius:20px;padding:2px 10px;white-space:nowrap}}
.badge.p{{color:{pc};border-color:{pc}33}}
.wrap{{max-width:800px;margin:0 auto;padding:28px 16px 80px}}
.msg{{display:flex;gap:13px;margin-bottom:22px;animation:fu .2s ease both}}
@keyframes fu{{from{{opacity:0;transform:translateY(5px)}}to{{opacity:1;transform:translateY(0)}}}}
.av{{width:34px;height:34px;border-radius:9px;display:flex;align-items:center;justify-content:center;font-size:15px;flex-shrink:0;margin-top:2px}}
.av.u{{background:var(--u-bg);border:1px solid var(--u-acc)}}
.av.a{{background:var(--a-bg);border:1px solid var(--a-acc)}}
.bw{{flex:1;min-width:0}}
.bh{{display:flex;align-items:baseline;gap:9px;margin-bottom:5px}}
.nm{{font-size:13px;font-weight:600}}
.nm.u{{color:var(--u-acc)}}.nm.a{{color:var(--a-acc)}}
.ts{{font-size:11px;color:var(--tx-d)}}
.bb{{background:var(--bg2);border:1px solid var(--bdr);border-radius:4px 13px 13px 13px;padding:13px 17px}}
.msg.u .bb{{border-color:rgba(59,130,246,.2);background:var(--u-bg);border-radius:13px 4px 13px 13px}}
.bb p{{margin-bottom:.7em}}.bb p:last-child{{margin-bottom:0}}
.bb h1,.bb h2,.bb h3{{margin:.85em 0 .35em;font-size:1em;font-weight:600}}
.bb a{{color:var(--lnk)}}
.bb code{{font-family:'JetBrains Mono',monospace;font-size:13px;background:var(--code);border:1px solid var(--bdr);border-radius:4px;padding:1px 5px}}
.bb pre{{background:var(--code);border:1px solid var(--bdr);border-radius:8px;padding:13px 15px;overflow-x:auto;margin:.7em 0}}
.bb pre code{{background:none;border:none;padding:0;font-size:13px;color:#c9d1d9}}
details.tk{{margin:9px 0;border:1px solid rgba(167,139,250,.25);border-radius:8px;background:var(--th);overflow:hidden}}
details.tk summary{{padding:8px 13px;cursor:pointer;font-size:13px;color:var(--th-acc);font-weight:500;user-select:none;list-style:none;display:flex;align-items:center;gap:6px}}
details.tk summary::before{{content:'▶';font-size:9px;transition:transform .2s}}
details[open].tk summary::before{{transform:rotate(90deg)}}
details.tk pre{{margin:0;padding:11px 15px;border-top:1px solid rgba(167,139,250,.15);font-size:12.5px;color:var(--tx-m);white-space:pre-wrap;word-break:break-word;background:transparent;border-radius:0}}
.meta{{margin-top:5px;font-size:11px;color:var(--tx-d);display:flex;gap:8px;flex-wrap:wrap}}
.meta span{{background:var(--bg3);border:1px solid var(--bdr);border-radius:4px;padding:1px 7px}}
.copy-btn{{position:fixed;bottom:24px;right:24px;background:var(--bg2);border:1px solid var(--bdr);color:var(--tx-m);border-radius:10px;padding:8px 16px;cursor:pointer;font-size:13px;font-family:'Inter',sans-serif;transition:all .2s}}
.copy-btn:hover{{background:var(--bg3);color:var(--tx)}}
footer{{text-align:center;padding:22px;font-size:12px;color:var(--tx-d);border-top:1px solid var(--bdr)}}
</style>
</head>
<body>
<header>
  <div class="logo">{pi}</div>
  <h1>{title}</h1>
  <div class="badges">
    <span class="badge p">{pn}</span>
    <span class="badge">{mc} messages</span>
    <span class="badge">{date}</span>
  </div>
</header>
<div class="wrap">{body}</div>
<button class="copy-btn" onclick="navigator.clipboard.writeText(document.body.innerText).then(()=>{{this.textContent='✔ Copied!';setTimeout(()=>this.textContent='📋 Copy text',2000)}})">📋 Copy text</button>
<footer>AChat Exporter v{ver} · by Raven RX · Founder of RX Network Security Labs</footer>
<script>
document.querySelectorAll('pre code').forEach(el=>{{
  const lang=el.className.replace('lang-','');
  if(lang){{const tag=document.createElement('div');tag.style='font-size:10px;color:#64748b;padding:4px 15px 0;font-family:monospace';tag.textContent=lang;el.parentNode.insertBefore(tag,el);}}
}});
</script>
</body></html>"""

def build_html(platform, icon, color, title, messages,
               user_name, ai_name, inc_think, inc_ts, inc_meta):
    parts = []
    count = 0
    for msg in messages:
        role = (msg.get("role") or "").upper()
        raw  = msg.get("_content", "")
        if not raw: continue
        count += 1
        raw  = render_thinking_html(raw) if inc_think else strip_thinking(raw)
        raw  = raw.replace('class="thinking"', 'class="tk"')
        body = _md_to_html(raw)
        is_u = role == "USER"
        rc   = "u" if is_u else "a"
        name = user_name if is_u else ai_name
        av   = "🧑" if is_u else "🤖"
        ts_h = f'<span class="ts">{_esc(msg.get("_ts",""))}</span>' if inc_ts and msg.get("_ts") else ""
        meta_h = ""
        if inc_meta:
            bits = []
            if msg.get("_model"):  bits.append(f"<span>{_esc(msg['_model'])}</span>")
            if msg.get("_tokens"): bits.append(f"<span>{msg['_tokens']} tokens</span>")
            if bits: meta_h = '<div class="meta">' + "".join(bits) + '</div>'
        parts.append(
            f'<div class="msg {rc}">'
            f'<div class="av {rc}">{av}</div>'
            f'<div class="bw">'
            f'<div class="bh"><span class="nm {rc}">{_esc(name)}</span>{ts_h}</div>'
            f'<div class="bb">{body}</div>{meta_h}'
            f'</div></div>'
        )
    html = HTML_PAGE.format(
        title=_esc(title), pi=icon, pn=platform.title(), pc=color,
        mc=count, body="\n".join(parts),
        ver=VERSION, date=datetime.now().strftime("%Y-%m-%d")
    )
    return html, count

def build_markdown(title, messages, user_name, ai_name, inc_think, inc_ts, inc_meta):
    lines = [f"# {title}\n"]
    count = 0
    for msg in messages:
        role = (msg.get("role") or "").upper()
        raw  = msg.get("_content", "")
        if not raw: continue
        count += 1
        raw  = render_thinking_md(raw) if inc_think else strip_thinking(raw)
        name = user_name if role == "USER" else ai_name
        hdr  = f"### {name}"
        if inc_ts and msg.get("_ts"):
            hdr += f"  _{msg['_ts']}_"
        lines.append(f"{hdr}\n\n{raw}\n")
        if inc_meta:
            meta = []
            if msg.get("_model"):  meta.append(f"Model: `{msg['_model']}`")
            if msg.get("_tokens"): meta.append(f"Tokens: {msg['_tokens']}")
            if meta: lines.append("> " + " | ".join(meta) + "\n")
    return "\n".join(lines).strip() + "\n", count

def build_text(title, messages, user_name, ai_name, inc_think, inc_ts, inc_meta):
    sep   = "─" * 60
    lines = [title, "═" * len(title), ""]
    count = 0
    for msg in messages:
        role = (msg.get("role") or "").upper()
        raw  = msg.get("_content", "")
        if not raw: continue
        count += 1
        raw  = render_thinking_txt(raw) if inc_think else strip_thinking(raw)
        name = user_name if role == "USER" else ai_name
        hdr  = f"[{name}]"
        if inc_ts and msg.get("_ts"):
            hdr += f"  ({msg['_ts']})"
        lines += [hdr, raw]
        if inc_meta:
            meta = []
            if msg.get("_model"):  meta.append(f"Model: {msg['_model']}")
            if msg.get("_tokens"): meta.append(f"Tokens: {msg['_tokens']}")
            if meta: lines.append("(" + " | ".join(meta) + ")")
        lines.append(sep)
    return "\n".join(lines).strip() + "\n", count

# ════════════════════════════════════════════════════════════════
#   EXPORT PREVIEW
# ════════════════════════════════════════════════════════════════
def show_preview(title, messages, user_name, ai_name):
    section(f"Preview — {title[:40]}")
    info(f"Total messages: {WHT}{len(messages)}{R}")
    blank()
    preview = messages[:3]
    for msg in preview:
        role = (msg.get("role") or "").upper()
        name = user_name if role == "USER" else ai_name
        nc   = CYN if role == "USER" else GRN
        raw  = strip_thinking(msg.get("_content", ""))
        snippet = raw[:120].replace('\n', ' ').strip()
        if len(raw) > 120: snippet += "..."
        print(f"  {nc}{BOLD}[{name}]{R}  {DIM}{snippet}{R}")
        blank()
    if len(messages) > 3:
        info(f"... and {len(messages) - 3} more messages")
    blank()

# ════════════════════════════════════════════════════════════════
#   PLATFORM: DEEPSEEK
# ════════════════════════════════════════════════════════════════
DS_API = "https://chat.deepseek.com/api/v0/share/content?share_id={}"
DS_HDR = {
    "User-Agent": "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36",
    "Accept"    : "application/json",
    "Referer"   : "https://chat.deepseek.com/",
    "Origin"    : "https://chat.deepseek.com",
}

def ds_extract_id(text):
    text = text.strip()
    m = re.search(r"/share/([a-zA-Z0-9_-]+)", text)
    if m: return m.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]+", text): return text
    raise ValueError("Invalid DeepSeek share URL/ID")

def ds_fetch(share_id):
    raw  = fetch_url(DS_API.format(share_id), DS_HDR, label="Fetching DeepSeek chat")
    data = json.loads(raw)
    biz  = data["data"]["biz_data"]
    msgs = []
    for m in (biz.get("messages") or []):
        role  = (m.get("role") or "").upper()
        frags = m.get("fragments") or []
        parts = []
        for f in frags:
            ft = (f.get("type") or "").upper()
            c  = (f.get("content") or "").strip()
            if not c: continue
            if role == "USER"      and ft == "REQUEST" : parts.append(c)
            elif role == "ASSISTANT":
                if   ft == "RESPONSE": parts.append(c)
                elif ft == "THINK"   : parts.append(f"__THINK__\n{c}\n__/THINK__")
        content = "\n\n".join(parts).strip()
        if content:
            msgs.append({
                "role":     role,
                "_content": content,
                "_ts":      format_ts(m.get("inserted_at", 0)),
                "_model":   m.get("model", ""),
                "_tokens":  m.get("accumulated_token_usage", ""),
            })
    return biz.get("title", "DeepSeek Chat"), msgs

# ════════════════════════════════════════════════════════════════
#   PLATFORM: GROK
# ════════════════════════════════════════════════════════════════
GK_HDR = {
    "User-Agent"     : "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36",
    "Accept"         : "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}

def gk_extract_id(text):
    text = text.strip()
    m = re.search(r"grok\.com/share/([^/?#\s]+)", text)
    if m: return m.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_=%-]+", text): return text
    raise ValueError("Invalid Grok share URL/ID")

def gk_fetch(share_id):
    url  = f"https://grok.com/rest/app-chat/share_links_data/{share_id}"
    raw  = fetch_url(url, GK_HDR, label="Fetching Grok chat")
    data = json.loads(raw)
    title = (data.get("conversation") or {}).get("title") or "Grok Chat"
    msgs = []
    for item in (data.get("responses") or []):
        if item.get("isControl"): continue
        sender = (item.get("sender") or "").lower()
        if sender == "human":       role = "USER"
        elif sender == "assistant": role = "ASSISTANT"
        else: continue
        content = (item.get("message") or "").strip()
        if not content: continue
        msgs.append({
            "role":     role,
            "_content": content,
            "_ts":      parse_iso(item.get("createTime", "")),
            "_model":   item.get("model") or "",
            "_tokens":  "",
        })
    if not msgs:
        raise ValueError("No messages extracted from Grok share")
    return title, msgs

# ════════════════════════════════════════════════════════════════
#   PLATFORM: CHATGPT
# ════════════════════════════════════════════════════════════════
GPT_HDR = {
    "User-Agent"     : "Mozilla/5.0 (Linux; Android 11) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36",
    "Accept"         : "text/html,application/xhtml+xml,*/*;q=0.9",
    "Accept-Language": "en-US,en;q=0.9",
}
GPT_SKIP = (
    'original custom instructions no longer available',
    'custom instructions no longer available',
)

def gpt_extract_id(text):
    text = text.strip()
    m = re.search(r"chatgpt\.com/share/([^/?#\s]+)", text)
    if m: return m.group(1)
    m = re.search(r"chat\.openai\.com/share/([^/?#\s]+)", text)
    if m: return m.group(1)
    if re.fullmatch(r"[a-zA-Z0-9_-]+", text): return text
    raise ValueError("Invalid ChatGPT share URL/ID")

def _gk(k, arr):
    return arr[int(k[1:])] if (isinstance(k, str) and k.startswith('_') and k[1:].isdigit()) else k

def _gv(v, arr):
    return arr[v] if isinstance(v, int) and 0 <= v < len(arr) else v

def _gx(d, arr):
    return {_gk(k, arr): _gv(v, arr) for k, v in d.items()} if isinstance(d, dict) else d

def gpt_fetch(share_id):
    url = f"https://chatgpt.com/share/{share_id}"
    raw = fetch_url(url, GPT_HDR, label="Fetching ChatGPT chat").decode("utf-8", "replace")
    m   = re.search(r'streamController\.enqueue\("(.*?)"\)', raw, re.DOTALL)
    if not m:
        raise ValueError("Could not find React Flight data in ChatGPT page")
    try:
        rj = m.group(1)
        rj = rj.replace('\\"', '"').replace('\\\\', '\\').replace('\\n', '\n').replace('\\t', '\t')
        rj = re.sub(r'\\u([0-9a-fA-F]{4})', lambda x: chr(int(x.group(1), 16)), rj)
        arr = json.loads(rj)
    except Exception as e:
        raise ValueError(f"Failed to parse React Flight JSON: {e}")
    if not isinstance(arr, list) or len(arr) < 30:
        raise ValueError("Unexpected React Flight array structure")

    def find(name):
        try:    return arr.index(name)
        except: return -1

    ti   = find('pageTitle')
    lc_i = find('linear_conversation')
    title = arr[ti + 1] if ti >= 0 and ti + 1 < len(arr) and isinstance(arr[ti+1], str) else "ChatGPT Chat"
    lc    = arr[lc_i + 1] if lc_i >= 0 and lc_i + 1 < len(arr) else []
    if not isinstance(lc, list):
        raise ValueError("linear_conversation not found")

    msgs = []
    for ni in lc:
        if not isinstance(ni, int) or ni >= len(arr): continue
        node = _gx(arr[ni], arr)
        mr   = node.get('message')
        if not isinstance(mr, dict): continue
        msg  = _gx(mr, arr)
        auth = _gx(msg.get('author'), arr) if isinstance(msg.get('author'), dict) else {}
        role = auth.get('role', '')
        role = arr[role] if isinstance(role, int) and role < len(arr) else role
        if (role or '').lower() not in ('user', 'assistant'): continue
        cont  = _gx(msg.get('content'), arr) if isinstance(msg.get('content'), dict) else {}
        pval  = cont.get('parts')
        pval  = arr[pval] if isinstance(pval, int) and pval < len(arr) else pval
        texts = []
        if isinstance(pval, list):
            for p in pval:
                pv = arr[p] if isinstance(p, int) and p < len(arr) else p
                if isinstance(pv, str) and pv.strip(): texts.append(pv.strip())
        content = "\n\n".join(texts).strip()
        if not content: continue
        if any(content.lower().strip() == s for s in GPT_SKIP): continue
        ts_r  = msg.get('create_time')
        ts_r  = arr[ts_r] if isinstance(ts_r, int) and ts_r < len(arr) else ts_r
        meta  = _gx(msg.get('metadata'), arr) if isinstance(msg.get('metadata'), dict) else {}
        model = meta.get('model_slug', '')
        model = arr[model] if isinstance(model, int) and model < len(arr) else model
        msgs.append({
            "role":     role.upper(),
            "_content": content,
            "_ts":      format_ts(ts_r) if ts_r else "",
            "_model":   model or "",
            "_tokens":  "",
        })
    if not msgs:
        raise ValueError("No messages found in ChatGPT share page")
    return title, msgs

# ════════════════════════════════════════════════════════════════
#   PLATFORM: CLAUDE
# ════════════════════════════════════════════════════════════════
CL_API      = "https://claude.ai/api/chat_snapshots/{}"
CL_UI_BLOCK = re.compile(
    r"```\s*\nThis block is not supported on your current device yet\.\s*\n```",
    re.IGNORECASE
)

def cl_check_dep():
    clear()
    print_banner()
    section("Claude Export — Heads Up! ⚠")
    print(f"  {YLW}{BOLD}Claude export is experimental.{R}")
    blank()
    info(f"Claude.ai uses aggressive {YLW}Cloudflare{R} protection.")
    info("Requests may fail even after 5 retries depending on")
    info("your network or IP. Try again later or use a VPN.")
    blank()
    if not HAS_CLOUDSCRAPER:
        print(f"  {RED}{BOLD}✗  cloudscraper is not installed!{R}")
        blank()
        info("Install it first:")
        print(f"  {CYN}pip install cloudscraper --break-system-packages{R}")
        blank()
        input(f"  {DIM}Press Enter to go back...{R}")
        return False
    info(f"cloudscraper  {GRN}installed ✓{R}")
    blank()
    div()
    blank()
    return ask_yn("Continue anyway?", default=False)

def cl_extract_id(text):
    text = text.strip()
    m = re.search(r"claude\.ai/share/([a-f0-9-]{36})", text)
    if m: return m.group(1)
    if re.fullmatch(r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}", text):
        return text
    raise ValueError("Invalid Claude share URL/ID")

def cl_fetch(share_id):
    if not HAS_CLOUDSCRAPER:
        raise ValueError("cloudscraper not installed")
    url    = CL_API.format(share_id)
    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    retries, delay = 5, 3.0
    data   = None
    for attempt in range(1, retries + 1):
        lbl = f"Fetching Claude chat {DIM}(attempt {attempt}/{retries}){R}"
        for i in range(20):
            print(f"\r  {CYN}{frames[i%len(frames)]}{R} {lbl}   ", end="", flush=True)
            time.sleep(0.05)
        print(f"\r{' '*70}\r", end="")
        try:
            s = _cloudscraper.create_scraper()
            r = s.get(url, timeout=30)
            if r.status_code == 200 and r.text.lstrip().startswith("{"):
                data = r.json()
                break
            if attempt < retries:
                warn(f"HTTP {r.status_code} / non-JSON — retrying in {delay}s...")
                time.sleep(delay)
            else:
                raise ValueError(f"Failed after {retries} attempts (last: HTTP {r.status_code})")
        except ValueError:
            raise
        except Exception as e:
            if attempt < retries:
                warn(f"Error: {e} — retrying in {delay}s...")
                time.sleep(delay)
            else:
                raise ValueError(f"Failed after {retries} attempts: {e}")
    if data is None:
        raise ValueError("No data received from Claude")
    title    = data.get("snapshot_name") or "Claude Chat"
    raw_msgs = data.get("chat_messages") or []
    msgs     = []
    for m in raw_msgs:
        sender = (m.get("sender") or "").lower()
        if sender == "human":       role = "USER"
        elif sender == "assistant": role = "ASSISTANT"
        else: continue
        content = (m.get("text") or "").strip()
        if not content: continue
        cleaned = CL_UI_BLOCK.sub("", content).strip()
        if not cleaned: continue
        msgs.append({
            "role":     role,
            "_content": cleaned,
            "_ts":      parse_iso(m.get("created_at", "")),
            "_model":   "",
            "_tokens":  "",
        })
    if not msgs:
        raise ValueError("No messages found in Claude share")
    return title, msgs

# ════════════════════════════════════════════════════════════════
#   PLATFORM REGISTRY
# ════════════════════════════════════════════════════════════════
PLATFORMS = {
    "deepseek": {"icon":"🤖", "label":"DeepSeek", "color":"#22c55e", "extract":ds_extract_id,  "fetch":ds_fetch},
    "grok"    : {"icon":"🐦", "label":"Grok",     "color":"#3b82f6", "extract":gk_extract_id,  "fetch":gk_fetch},
    "chatgpt" : {"icon":"💬", "label":"ChatGPT",  "color":"#a855f7", "extract":gpt_extract_id, "fetch":gpt_fetch},
    "claude"  : {"icon":"🟠", "label":"Claude",   "color":"#f97316", "extract":cl_extract_id,  "fetch":cl_fetch,
                 "pre_check": cl_check_dep},
}

# ════════════════════════════════════════════════════════════════
#   EXPORT ENGINE
# ════════════════════════════════════════════════════════════════
def do_export(platform_key, cfg, quick=False, fmt=None, folder=None, links=None):
    plat = PLATFORMS[platform_key]
    icon = plat["icon"]
    name = plat["label"]

    if plat.get("pre_check") and not plat["pre_check"]():
        return

    # ── Step 1: Links ──────────────────────────────────────────
    if links:
        shares = []
        for raw in links:
            try:
                sid = plat["extract"](raw)
                shares.append(sid)
            except ValueError as e:
                error(str(e))
        if not shares: return
    else:
        step(icon, name, 1, 4, "Share Links")
        info("Paste URLs or IDs — one per line.")
        info(f"Leave blank and press {CYN}Enter{R} when done.\n")
        shares = []
        while True:
            raw = input(f"  {CYN}+{R} Link {len(shares)+1}: ").strip()
            if not raw:
                if not shares: warn("Enter at least one link."); continue
                break
            try:
                sid = plat["extract"](raw)
                shares.append(sid)
                print(f"  {GRN}✓{R} Added: {DIM}{sid}{R}")
            except ValueError as e:
                error(str(e))

    # ── Step 2: Format ─────────────────────────────────────────
    if not fmt:
        step(icon, name, 2, 4, "Output Format")
        fmt = arrow_menu([
            ("📄  Markdown  (.md)",     "markdown"),
            ("📃  Plain Text (.txt)",   "text"),
            ("🌐  HTML  (dark styled)", "html"),
            ("🗂   JSON  (raw data)",   "json"),
        ])

    # ── Step 3: Options ────────────────────────────────────────
    if not quick:
        step(icon, name, 3, 4, "Options")
        opts = checkbox_menu([
            ("Include thinking / reasoning blocks", "thinking",  cfg.get("include_thinking",  True)),
            ("Include timestamps",                  "timestamp", cfg.get("include_timestamp", False)),
            ("Include model & token metadata",      "metadata",  cfg.get("include_metadata",  False)),
            ("Copy to clipboard after export",      "clipboard", cfg.get("copy_clipboard",    False)),
        ])
    else:
        opts = {
            "thinking" : cfg.get("include_thinking",  True),
            "timestamp": cfg.get("include_timestamp", False),
            "metadata" : cfg.get("include_metadata",  False),
            "clipboard": cfg.get("copy_clipboard",    False),
        }

    # ── Step 4: Save location ──────────────────────────────────
    if not folder:
        if not quick:
            step(icon, name, 4, 4, "Save Location")
            default_folder = PLATFORM_DIRS[platform_key]
            info(f"Default: {DIM}{default_folder}{R}")
            custom = ask("Custom folder (Enter for default)", "")
            folder = custom.strip() if custom.strip() else default_folder
        else:
            folder = PLATFORM_DIRS[platform_key]
    os.makedirs(folder, exist_ok=True)

    user_name = cfg.get("user_name", "You")
    ai_name   = cfg.get("ai_name",   "AI")

    blank(); div()
    results = []
    for i, share_id in enumerate(shares, 1):
        if len(shares) > 1:
            blank(); info(f"{MAG}[{i}/{len(shares)}]{R} {share_id}")

        # Duplicate check
        cached = cache_check(share_id)
        if cached:
            warn(f"Already exported: {DIM}{cached.get('path','?')}{R}  ({cached.get('exported_at','')})")
            if not ask_yn("Export again anyway?", default=False):
                results.append((share_id, None, None, None))
                continue

        try:
            title, messages = plat["fetch"](share_id)
            success(f"Fetched! ({len(messages)} messages) — {DIM}{title[:50]}{R}")
        except Exception as e:
            error(f"Failed: {e}")
            results.append((share_id, None, None, None))
            continue

        # Preview
        if not quick:
            blank()
            show_preview(title, messages, user_name, ai_name)
            if not ask_yn("Looks good? Continue?", default=True):
                results.append((share_id, None, None, None))
                continue

        fname   = safe_filename(title, share_id)
        path    = os.path.join(folder, f"{fname}.{fmt_ext(fmt)}")

        if fmt == "html":
            content, count = build_html(
                platform_key, icon, plat["color"], title, messages,
                user_name, ai_name,
                opts["thinking"], opts["timestamp"], opts["metadata"])
        elif fmt == "markdown":
            content, count = build_markdown(
                title, messages, user_name, ai_name,
                opts["thinking"], opts["timestamp"], opts["metadata"])
        elif fmt == "text":
            content, count = build_text(
                title, messages, user_name, ai_name,
                opts["thinking"], opts["timestamp"], opts["metadata"])
        else:
            content = json.dumps({"title": title, "messages": messages}, indent=2, ensure_ascii=False)
            count   = len(messages)

        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        success(f"Saved → {WHT}{path}{R}")

        cache_add(share_id, path)
        add_history(platform_key, title, fmt, path, count, share_id)
        index_file(path, platform_key, title, share_id)

        if opts["clipboard"] and len(shares) == 1:
            if copy_clipboard(content): success("Copied to clipboard!")
            else: warn("Clipboard unavailable.")

        results.append((share_id, title, path, count))

    if opts["clipboard"] and len(shares) > 1:
        warn("Clipboard skipped in batch mode.")

    div(); blank()
    ok = len([r for r in results if r[1]])
    print(f"  {GRN}{BOLD}Done! 🎉{R}  {DIM}Exported {ok} of {len(shares)} chat(s).{R}")

# ════════════════════════════════════════════════════════════════
#   TOOLS: SEARCH
# ════════════════════════════════════════════════════════════════
def tool_search():
    section("🔍  Search Exports")
    info(f"Searches all exported files in {DIM}{ACHAT_DIR}{R}")
    blank()
    query = ask("Enter keyword(s)")
    if not query: return
    blank()
    info(f"Searching for: {WHT}{query}{R}")
    blank()

    results = search_exports(query)
    if not results:
        warn("No matches found.")
        return

    print(f"  {GRN}{BOLD}Found {len(results)} match(es):{R}")
    blank()
    PLAT_COLOR = {"deepseek":GRN, "grok":BLU, "chatgpt":MAG, "claude":YLW}
    for i, r in enumerate(results[:20], 1):
        plat = r.get("platform", "?")
        pc   = PLAT_COLOR.get(plat, CYN)
        print(f"  {DIM}{i:>2}.{R}  {pc}{BOLD}{plat.title():<10}{R}  {WHT}{r.get('title','?')[:45]}{R}")
        print(f"       {DIM}{r.get('path','?')}{R}")
        for snip in r.get("_snippets", []):
            terms = [t.lower() for t in query.split()]
            hi = snip
            for t in terms:
                hi = re.sub(re.escape(t), f"{YLW}{t}{R}", hi, flags=re.IGNORECASE)
            print(f"       {DIM}↳{R} {hi}")
        blank()

# ════════════════════════════════════════════════════════════════
#   TOOLS: STATS
# ════════════════════════════════════════════════════════════════
def tool_stats():
    section("📊  Chat Stats")
    info("Enter path to an exported file:")
    blank()
    path = ask("File path")
    if not path or not os.path.exists(path):
        error("File not found.")
        return
    blank()
    try:
        with open(path, encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception as e:
        error(str(e)); return

    lines      = content.splitlines()
    words      = re.findall(r'\b\w+\b', content)
    chars      = len(content)
    # rough message count from markdown headers
    user_msgs  = len(re.findall(r'^### .+', content, re.MULTILINE))
    code_blocks= len(re.findall(r'```', content)) // 2
    top_words  = Counter(w.lower() for w in words if len(w) > 4).most_common(8)

    div()
    blank()
    print(f"  {DIM}File       {R}  {WHT}{os.path.basename(path)}{R}")
    print(f"  {DIM}Size       {R}  {WHT}{chars:,} chars  ·  {len(lines):,} lines{R}")
    print(f"  {DIM}Words      {R}  {WHT}{len(words):,}{R}")
    print(f"  {DIM}Messages   {R}  {WHT}~{user_msgs}{R}")
    print(f"  {DIM}Code blocks{R}  {WHT}{code_blocks}{R}")
    blank()
    if top_words:
        print(f"  {BLU}{BOLD}── Top words {'─'*35}{R}")
        blank()
        for word, count in top_words:
            bar = "█" * min(count, 30)
            print(f"  {DIM}{word:<18}{R}  {CYN}{bar}{R}  {DIM}{count}{R}")
        blank()

# ════════════════════════════════════════════════════════════════
#   TOOLS: DIFF
# ════════════════════════════════════════════════════════════════
def tool_diff():
    section("⚖️   Chat Diff")
    info("Compare two exported chat files.")
    blank()
    path1 = ask("First file path")
    path2 = ask("Second file path")
    if not path1 or not path2:
        return
    if not os.path.exists(path1):
        error(f"Not found: {path1}"); return
    if not os.path.exists(path2):
        error(f"Not found: {path2}"); return

    with open(path1, encoding="utf-8", errors="ignore") as f: lines1 = f.readlines()
    with open(path2, encoding="utf-8", errors="ignore") as f: lines2 = f.readlines()

    diff = list(difflib.unified_diff(
        lines1, lines2,
        fromfile=os.path.basename(path1),
        tofile=os.path.basename(path2),
        lineterm=""
    ))

    if not diff:
        blank()
        success("Files are identical! No differences found.")
        return

    added   = sum(1 for l in diff if l.startswith('+') and not l.startswith('+++'))
    removed = sum(1 for l in diff if l.startswith('-') and not l.startswith('---'))

    blank()
    info(f"Lines added:   {GRN}{added}{R}")
    info(f"Lines removed: {RED}{removed}{R}")
    blank()
    div()
    blank()

    for line in diff[:80]:
        if line.startswith('+++') or line.startswith('---'):
            print(f"  {BOLD}{line.rstrip()}{R}")
        elif line.startswith('+'):
            print(f"  {GRN}{line.rstrip()}{R}")
        elif line.startswith('-'):
            print(f"  {RED}{line.rstrip()}{R}")
        elif line.startswith('@@'):
            print(f"  {CYN}{line.rstrip()}{R}")
        else:
            print(f"  {DIM}{line.rstrip()}{R}")

    if len(diff) > 80:
        blank()
        info(f"... {len(diff) - 80} more lines. Save full diff to file?")
        if ask_yn("Save diff?", default=False):
            out = path1 + ".diff"
            with open(out, "w", encoding="utf-8") as f:
                f.writelines(diff)
            success(f"Saved → {out}")

# ════════════════════════════════════════════════════════════════
#   TOOLS: MERGE
# ════════════════════════════════════════════════════════════════
def tool_merge():
    section("🔀  Merge Exports")
    info("Merge multiple exported files into one.")
    info(f"Leave blank and press {CYN}Enter{R} when done.\n")

    paths = []
    while True:
        p = ask(f"File {len(paths)+1} path", "")
        if not p:
            if len(paths) < 2: warn("Add at least 2 files."); continue
            break
        if not os.path.exists(p):
            error("File not found."); continue
        paths.append(p)
        print(f"  {GRN}✓{R} Added: {DIM}{os.path.basename(p)}{R}")

    blank()

    # Read all files and detect format
    contents = []
    for p in paths:
        with open(p, encoding="utf-8", errors="ignore") as f:
            contents.append((os.path.basename(p), f.read()))

    # Smart merge: sort by file modification time, then stitch with dividers
    paths_sorted = sorted(paths, key=lambda p: os.path.getmtime(p))
    merged_parts = []
    for p in paths_sorted:
        name = os.path.basename(p)
        with open(p, encoding="utf-8", errors="ignore") as f:
            text = f.read().strip()
        merged_parts.append(f"\n\n<!-- Source: {name} -->\n\n{text}")

    merged = "\n\n" + ("─" * 60 + "\n").join(merged_parts)

    # Find common keywords across files for auto-title
    all_words = []
    for _, c in contents:
        all_words += re.findall(r'\b\w{4,}\b', c.lower())
    common = [w for w, _ in Counter(all_words).most_common(3)]
    suggested_title = "_".join(common) if common else "merged_chat"

    blank()
    out_name = ask("Output filename (no extension)", suggested_title)
    out_path = os.path.join(ACHAT_DIR, "exports", f"{out_name}.md")

    with open(out_path, "w", encoding="utf-8") as f:
        f.write(f"# Merged: {out_name}\n")
        f.write(f"*Merged {len(paths)} files on {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n")
        f.write(merged)

    blank()
    success(f"Merged {len(paths)} files → {WHT}{out_path}{R}")

# ════════════════════════════════════════════════════════════════
#   HISTORY VIEWER  +  RE-EXPORT
# ════════════════════════════════════════════════════════════════
def view_history(cfg):
    section("Export History")
    hist = load_history()
    if not hist:
        info("No exports yet. Go export something! 🚀")
        return
    hist_rev = list(reversed(hist))
    PAGE, start = 10, 0
    PLAT_COLOR = {"deepseek":GRN, "grok":BLU, "chatgpt":MAG, "claude":YLW}

    while True:
        page  = hist_rev[start:start+PAGE]
        total = len(hist_rev)
        blank()
        print(f"  {DIM}Showing {start+1}–{min(start+len(page),total)} of {total}{R}")
        blank()
        for i, h in enumerate(page):
            idx   = start + i + 1
            plat  = h.get("platform","?")
            pc    = PLAT_COLOR.get(plat, CYN)
            title = h.get("title","?")[:40]
            exists = os.path.exists(h.get("path",""))
            ex_mark = "" if exists else f" {RED}[file missing]{R}"
            print(f"  {DIM}{idx:>3}.{R}  {pc}{BOLD}{plat.title():<10}{R}  {WHT}{title:<40}{R}{ex_mark}")
            print(f"       {DIM}{h.get('exported_at','?')}  ·  {h.get('format','?')}  ·  {h.get('messages','?')} msgs{R}")
            print(f"       {DIM}{h.get('path','?')}{R}")
            blank()

        nav = []
        if start + PAGE < total: nav.append(("↓  Next page", "next"))
        if start > 0:            nav.append(("↑  Prev page", "prev"))
        nav.append(("🔁  Re-export a chat", "reexport"))
        nav.append(("←  Back",              "back"))
        choice = arrow_menu(nav)
        if   choice == "next":     start += PAGE
        elif choice == "prev":     start -= PAGE
        elif choice == "reexport": _reexport(hist_rev, cfg)
        else: break

def _reexport(hist_rev, cfg):
    blank()
    try:
        n = int(ask("Enter number of chat to re-export")) - 1
        h = hist_rev[n]
    except Exception:
        error("Invalid number."); return

    sid = h.get("share_id")
    plat = h.get("platform")
    if not sid or plat not in PLATFORMS:
        error("Cannot re-export this entry (missing data)."); return

    blank()
    info(f"Re-exporting: {WHT}{h.get('title','?')}{R}")
    info(f"Platform: {WHT}{plat.title()}{R}")
    blank()

    fmt = arrow_menu([
        ("📄  Markdown  (.md)",     "markdown"),
        ("📃  Plain Text (.txt)",   "text"),
        ("🌐  HTML  (dark styled)", "html"),
        ("🗂   JSON  (raw data)",   "json"),
    ])
    do_export(plat, cfg, quick=True, fmt=fmt, links=[sid])

# ════════════════════════════════════════════════════════════════
#   ABOUT
# ════════════════════════════════════════════════════════════════
def show_about():
    clear()
    print_banner()
    section("About  RX Network Security Labs")
    print(f"  {CYN}{BOLD}RX Network Security Labs (RNSL){R}")
    blank()
    info("A creation lab. Not a company. Not a startup.")
    info("A lab where tools and systems are built from raw")
    info("necessity — by builders who refused to wait for")
    info("someone else to do it.")
    blank()
    div()
    blank()
    print(f"  {DIM}Founded {R}  {WHT}16 June 2026{R}")
    print(f"  {DIM}Mission {R}  {WHT}Build what has never existed.{R}")
    print(f"  {DIM}Status  {R}  {GRN}ACTIVE{R}")
    blank()
    div()
    blank()
    print(f"  {DIM}GitHub  {R}  {CYN}github.com/RX-Network-Security-Labs{R}")
    print(f"  {DIM}Web     {R}  {CYN}rx-network-security-labs.github.io/website{R}")
    print(f"  {DIM}Telegram{R}  {CYN}t.me/rxnetworksecuritylabs{R}")
    print(f"  {DIM}Discord {R}  {CYN}discord.gg/nWt82zV3s4{R}")
    blank()
    div()
    blank()
    info(f"AChat Exporter  {DIM}v{VERSION}{R}  —  {MAG}by Raven RX{R}")
    info("Founder of RX Network Security Labs")
    blank()
    input(f"  {DIM}Press Enter to return to menu...{R}")

# ════════════════════════════════════════════════════════════════
#   SETTINGS
# ════════════════════════════════════════════════════════════════
def settings_menu(cfg):
    while True:
        section("Settings")
        info(f"User name    : {WHT}{cfg.get('user_name','You')}{R}")
        info(f"AI name      : {WHT}{cfg.get('ai_name','AI')}{R}")
        info(f"Default fmt  : {WHT}{cfg.get('default_format','markdown')}{R}")
        info(f"Data folder  : {DIM}{ACHAT_DIR}{R}")
        blank()
        choice = arrow_menu([
            ("✏   Change user / AI names",      "names"),
            ("📁  Change default export format", "fmt"),
            ("🗑   Clear export history",        "clear_hist"),
            ("🗑   Clear duplicate cache",       "clear_cache"),
            ("←   Back",                        "back"),
        ])
        if choice == "names":
            blank()
            cfg["user_name"] = ask("Your name", cfg.get("user_name","You"))
            cfg["ai_name"]   = ask("AI name",   cfg.get("ai_name","AI"))
            save_config(cfg); success("Saved!")
        elif choice == "fmt":
            blank()
            cfg["default_format"] = arrow_menu([
                ("Markdown","markdown"),("Plain Text","text"),
                ("HTML","html"),("JSON","json"),
            ])
            save_config(cfg); success("Saved!")
        elif choice == "clear_hist":
            blank()
            if ask_yn("Clear ALL export history?", default=False):
                save_history([]); success("History cleared.")
        elif choice == "clear_cache":
            blank()
            if ask_yn("Clear duplicate detection cache?", default=False):
                save_cache({}); success("Cache cleared.")
        elif choice == "back":
            break

# ════════════════════════════════════════════════════════════════
#   SELF-UPDATE
# ════════════════════════════════════════════════════════════════
def check_update(auto_apply=False):
    section("🔄  Update Checker")
    info(f"Current version: {WHT}v{VERSION}{R}")
    blank()

    frames = ["⠋","⠙","⠹","⠸","⠼","⠴","⠦","⠧","⠇","⠏"]
    for i in range(15):
        print(f"\r  {CYN}{frames[i%len(frames)]}{R} Checking GitHub...   ", end="", flush=True)
        time.sleep(0.05)
    print(f"\r{' '*50}\r", end="")

    try:
        req  = Request(GITHUB_API, headers={"User-Agent": "AChat-Exporter"})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
        latest = data.get("tag_name", "").lstrip("v")
        dl_url = None
        for asset in data.get("assets", []):
            if asset.get("name") == "achat.py":
                dl_url = asset.get("browser_download_url")
                break
    except Exception as e:
        error(f"Could not reach GitHub: {e}")
        return

    if not latest:
        warn("Could not determine latest version.")
        return

    def ver_tuple(v):
        try: return tuple(int(x) for x in re.sub(r'[^0-9.]','',v).split('.'))
        except: return (0,)

    if ver_tuple(latest) <= ver_tuple(VERSION):
        success(f"You're up to date! (v{VERSION})")
        return

    blank()
    print(f"  {YLW}{BOLD}🆕 New version available!{R}")
    blank()
    info(f"Current : {RED}v{VERSION}{R}")
    info(f"Latest  : {GRN}v{latest}{R}")
    blank()

    if not dl_url:
        warn("No downloadable achat.py found in latest release.")
        info(f"Download manually: github.com/{GITHUB_REPO}/releases/latest")
        return

    if not auto_apply:
        if not ask_yn("Download and update now?", default=False):
            info(f"Download manually: github.com/{GITHUB_REPO}/releases/latest")
            return

    blank()
    for i in range(20):
        print(f"\r  {CYN}{frames[i%len(frames)]}{R} Downloading v{latest}...   ", end="", flush=True)
        time.sleep(0.05)
    print(f"\r{' '*60}\r", end="")

    try:
        req = Request(dl_url, headers={"User-Agent": "AChat-Exporter"})
        with urlopen(req, timeout=30) as resp:
            new_content = resp.read()

        self_path = os.path.realpath(sys.argv[0])
        tmp_path  = self_path + ".tmp"
        with open(tmp_path, "wb") as f:
            f.write(new_content)
        os.replace(tmp_path, self_path)
        # preserve executable bit
        os.chmod(self_path, 0o755)
        success(f"Updated to v{latest}! Restart achat to apply.")
    except Exception as e:
        error(f"Update failed: {e}")

# ════════════════════════════════════════════════════════════════
#   CLI PARSER
# ════════════════════════════════════════════════════════════════
def parse_args():
    p = argparse.ArgumentParser(
        prog="achat",
        description="AChat Exporter — Export AI chats from DeepSeek, Grok, ChatGPT & Claude",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Examples:
  achat                                     # Interactive TUI
  achat https://chat.deepseek.com/share/abc # Auto-detect + default settings
  achat -p grok -f html <url>               # Grok → HTML
  achat -p chatgpt -f md -o ~/chats <url>   # ChatGPT → Markdown → custom folder
  achat search "docker setup"               # Search exports
  achat stats ~/AChat/exports/deepseek/x.md # File stats
  achat --update                            # Check & apply update
        """
    )
    p.add_argument("args",        nargs="*",      help="URL/ID or subcommand (search, stats, diff, merge)")
    p.add_argument("-p","--platform", choices=list(PLATFORMS.keys()), help="Force platform (skip auto-detect)")
    p.add_argument("-f","--format",   choices=["md","markdown","txt","text","html","json"], help="Output format")
    p.add_argument("-o","--output",   metavar="DIR",  help="Output folder")
    p.add_argument("--think",         action="store_true", help="Include thinking blocks")
    p.add_argument("--no-think",      action="store_true", help="Exclude thinking blocks")
    p.add_argument("--update",        action="store_true", help="Check for updates")
    p.add_argument("--version",       action="store_true", help="Show version")
    return p, p.parse_args()

# ════════════════════════════════════════════════════════════════
#   MAIN
# ════════════════════════════════════════════════════════════════
def main():
    setup_dirs()
    p, args = parse_args()

    # ── --version ─────────────────────────────────────────────
    if args.version:
        print(f"AChat Exporter v{VERSION}")
        print(f"by Raven RX — Founder of RX Network Security Labs")
        print(f"github.com/{GITHUB_REPO}")
        sys.exit(0)

    cfg = load_config()

    # ── --update ──────────────────────────────────────────────
    if args.update:
        print_banner()
        check_update(auto_apply=True)
        blank()
        input(f"  {DIM}Press Enter to exit...{R}")
        sys.exit(0)

    # ── Subcommands: search / stats / diff / merge ────────────
    if args.args:
        subcmd = args.args[0].lower()

        if subcmd == "search":
            print_banner()
            query = " ".join(args.args[1:])
            if query:
                results = search_exports(query)
                if not results:
                    warn(f"No matches for '{query}'.")
                else:
                    PLAT_COLOR = {"deepseek":GRN,"grok":BLU,"chatgpt":MAG,"claude":YLW}
                    blank()
                    print(f"  {GRN}{BOLD}Found {len(results)} match(es) for '{query}':{R}")
                    blank()
                    for i, r in enumerate(results[:20], 1):
                        pc = PLAT_COLOR.get(r.get("platform",""), CYN)
                        print(f"  {DIM}{i:>2}.{R}  {pc}{r.get('platform','?').title():<10}{R}  {WHT}{r.get('title','?')[:45]}{R}")
                        print(f"       {DIM}{r.get('path','?')}{R}")
                        blank()
            else:
                tool_search()
            sys.exit(0)

        if subcmd == "stats":
            print_banner()
            if len(args.args) > 1:
                path = args.args[1]
                if os.path.exists(path):
                    # inline stats
                    with open(path, encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                    words = re.findall(r'\b\w+\b', content)
                    lines = content.splitlines()
                    blank()
                    print(f"  {WHT}{os.path.basename(path)}{R}")
                    div()
                    print(f"  Words: {len(words):,}  ·  Lines: {len(lines):,}  ·  Chars: {len(content):,}")
                    blank()
                else:
                    error(f"File not found: {path}")
            else:
                tool_stats()
            sys.exit(0)

        if subcmd == "diff":
            print_banner()
            tool_diff()
            sys.exit(0)

        if subcmd == "merge":
            print_banner()
            tool_merge()
            sys.exit(0)

        # ── Quick/Full CLI export ──────────────────────────────
        urls = args.args

        # Normalize format
        fmt_map = {"md":"markdown","txt":"text"}
        fmt = fmt_map.get(args.format, args.format) if args.format else cfg.get("default_format","markdown")

        # Handle --think / --no-think
        if args.think:    cfg["include_thinking"] = True
        if args.no_think: cfg["include_thinking"] = False

        # Auto-detect platform or use -p
        platform_key = args.platform
        if not platform_key:
            for url in urls:
                platform_key = detect_platform(url)
                if platform_key: break

        if not platform_key:
            print_banner()
            error("Could not auto-detect platform. Use -p to specify.")
            blank()
            info("Supported: deepseek, grok, chatgpt, claude")
            sys.exit(1)

        print_banner()
        do_export(platform_key, cfg,
                  quick=True,
                  fmt=fmt,
                  folder=args.output,
                  links=urls)
        sys.exit(0)

    # ════════════════════════════════════════════════════════════
    #   INTERACTIVE TUI
    # ════════════════════════════════════════════════════════════
    print_banner()

    while True:
        section("Select Platform")
        choice = arrow_menu([
            ("🤖  DeepSeek",        "deepseek"),
            ("🐦  Grok",            "grok"),
            ("💬  ChatGPT",         "chatgpt"),
            ("🟠  Claude",          "claude"),
            ("─" * 25,             "__soon_sep"),
            ("🛠   Tools",          "tools"),
            ("📋  Export History",  "history"),
            ("🔄  Check for update","update"),
            ("⚙   Settings",       "settings"),
            ("ℹ   About RNSL",      "about"),
            ("←   Exit",           "exit"),
        ])

        if choice in PLATFORMS:
            try:
                do_export(choice, cfg)
            except KeyboardInterrupt:
                blank(); warn("Export cancelled.")

        elif choice == "tools":
            try:
                section("🛠   Tools")
                tool_choice = arrow_menu([
                    ("🔍  Search exports",       "search"),
                    ("📊  Chat stats",           "stats"),
                    ("⚖️   Diff two exports",    "diff"),
                    ("🔀  Merge exports",        "merge"),
                    ("←   Back",                "back"),
                ])
                if tool_choice == "search": tool_search()
                elif tool_choice == "stats": tool_stats()
                elif tool_choice == "diff":  tool_diff()
                elif tool_choice == "merge": tool_merge()
            except KeyboardInterrupt:
                blank()

        elif choice == "history":
            view_history(cfg)

        elif choice == "update":
            check_update()

        elif choice == "settings":
            settings_menu(cfg)

        elif choice == "about":
            show_about()
            print_banner()
            continue

        elif choice == "exit":
            blank()
            print(f"  {MAG}Bye! 👋  — Raven RX{R}\n")
            sys.exit(0)

        blank()
        input(f"  {DIM}Press Enter to return to menu...{R}")
        print_banner()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print(f"\n\n  {RED}{BOLD}Interrupted. Bye! 👋{R}\n")
        sys.exit(0)
