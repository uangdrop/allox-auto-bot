#!/usr/bin/env python3
"""
Allox Auto Bot
==============
Auto-login via Web3 wallet signature, auto-chat to an AI endpoint, and farm
points. After every 24h cycle it sends a Telegram report (optional).

Project layout
---------------
  allox-auto-bot/
  ├── bot.py              ← this file (entry point)
  ├── telegram.py         ← optional Telegram reporter
  ├── accounts.txt        ← one private key per line (you create this)
  ├── proxy.txt           ← one proxy per line (optional)
  ├── .env                ← Telegram config (optional, see .env.example)
  └── requirements.txt

Run
---
  pip install -r requirements.txt
  python bot.py
"""

import os
import re
import sys
import time
import json
import random
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple

import pytz
import requests
from colorama import init, Fore, Style
from eth_account import Account
from eth_account.messages import encode_defunct

# Optional RSS parser; we fall back to stdlib XML if not installed
try:
    import feedparser  # type: ignore
    HAS_FEEDPARSER = True
except ImportError:
    HAS_FEEDPARSER = False

# Local: Telegram reporter (gracefully no-op if not configured)
try:
    import telegram
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False

init(autoreset=True)

# ── Load .env if present (tiny inline parser, no python-dotenv dep) ────────
def _load_dotenv(path: str = ".env") -> None:
    if not os.path.exists(path):
        return
    try:
        with open(path, "r", encoding="utf-8") as f:
            for raw in f:
                line = raw.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k, v = k.strip(), v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
    except Exception:
        pass


def _csv_env(name: str, default: List[str]) -> List[str]:
    """Read a comma-separated env var; fall back to `default` if empty."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return list(default)
    items = [s.strip() for s in raw.split(",") if s.strip()]
    return items if items else list(default)


def _pipe_env(name: str, default: List[str]) -> List[str]:
    """Read a pipe-separated env var; fall back to `default` if empty."""
    raw = os.getenv(name, "").strip()
    if not raw:
        return list(default)
    items = [s.strip() for s in raw.split("|") if s.strip()]
    return items if items else list(default)


_load_dotenv()

# ════════════════════════════════════════════════════════════════════════════
#  Config — edit API endpoints here if the platform differs
# ════════════════════════════════════════════════════════════════════════════
API_BASE      = os.getenv("ALLOX_API_BASE", "https://api.allox.ai/v1").rstrip("/")
NONCE_URL     = f"{API_BASE}/auth/nonce"
LOGIN_URL     = f"{API_BASE}/auth/verify"
CHAT_URL      = f"{API_BASE}/chat"
# Multiple RSS sources — tried in random order each cycle. If one feed is
# down, slow, or rate-limited, we move on to the next. Add your own feeds
# here (RSS 2.0 or Atom). If feedparser is not installed, only the first
# one is used (with stdlib XML fallback).
RSS_FEEDS = _csv_env("RSS_FEEDS", [
    "https://cointelegraph.com/rss",
    "https://www.coindesk.com/arc/outboundfeeds/rss/",
    "https://decrypt.co/feed",
    "https://news.bitcoin.com/feed/",
])
PROMPT_TEMPLATES = _pipe_env("PROMPT_TEMPLATES", [
    "Can you explain this crypto news: {title}?",
    "What are your thoughts on this event: {title}?",
    "Summarize the impact of this headline: {title}",
    "Is this bullish or bearish for the market: {title}?",
    "Provide a brief analysis on this news: {title}",
])
MAX_CHATS     = 20
CYCLE_SLEEP   = 24 * 60 * 60            # 24 hours
TZ_WIB        = pytz.timezone("Asia/Jakarta")
USER_AGENT    = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                 "AppleWebKit/537.36 (KHTML, like Gecko) "
                 "Chrome/124.0 Safari/537.36")
ACCOUNTS_FILE = "accounts.txt"
PROXY_FILE    = "proxy.txt"
STATE_FILE    = ".allox_state.json"

FALLBACK_PROMPTS: List[str] = [
    "What's driving today's crypto market?",
    "Explain Bitcoin halving in simple terms.",
    "How does Ethereum staking work?",
    "Compare Layer 1 vs Layer 2 scalability.",
    "What are the main risks in DeFi?",
    "How do zero-knowledge proofs improve privacy?",
    "What is tokenomics and why does it matter?",
    "Explain how cross-chain bridges work.",
    "What role do oracles play in DeFi?",
    "How do I evaluate a new crypto project?",
    "What is MEV and how does it affect traders?",
    "Explain the difference between custodial and non-custodial wallets.",
    "How do stablecoins maintain their peg?",
    "What are the security risks of cross-chain bridges?",
    "What is on-chain analytics used for?",
]


# ════════════════════════════════════════════════════════════════════════════
#  Logging (colorama + WIB timestamps)
# ════════════════════════════════════════════════════════════════════════════
def now_wib() -> datetime:
    return datetime.now(TZ_WIB)


def ts() -> str:
    return now_wib().strftime("[%H:%M:%S]")


def _log(level: str, msg: str, color: str) -> None:
    print(f"{color}{ts()} [{level}] {msg}{Style.RESET_ALL}")


def log_info(msg: str)    -> None: _log("INFO",    msg, Fore.CYAN)
def log_success(msg: str) -> None: _log("SUCCESS", msg, Fore.GREEN)
def log_warn(msg: str)    -> None: _log("WARN",    msg, Fore.YELLOW)
def log_error(msg: str)   -> None: _log("ERROR",   msg, Fore.RED)


def banner() -> None:
    print(Fore.MAGENTA + Style.BRIGHT + r"""
╔══════════════════════════════════════════════╗
║              ALLOX  AUTO  BOT               ║
║   Web3 Login · Auto-Chat · Point Farming     ║
╚══════════════════════════════════════════════╝
""" + Style.RESET_ALL)


# ════════════════════════════════════════════════════════════════════════════
#  File I/O
# ════════════════════════════════════════════════════════════════════════════
def load_lines(path: str) -> List[str]:
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return [ln.strip() for ln in f
                if ln.strip() and not ln.strip().startswith("#")]


def load_accounts() -> List[str]:
    keys = load_lines(ACCOUNTS_FILE)
    if not keys:
        log_error(f"{ACCOUNTS_FILE} not found or empty.")
        log_error("Create it with one Ethereum private key per line.")
        sys.exit(1)
    log_success(f"Loaded {len(keys)} account(s) from {ACCOUNTS_FILE}")
    return keys


def load_proxies() -> List[str]:
    proxies = load_lines(PROXY_FILE)
    if proxies:
        log_success(f"Loaded {len(proxies)} proxy from {PROXY_FILE}")
    return proxies


def mask_proxy(p: str) -> str:
    return re.sub(r"(://[^:]+:)[^@]+(@)", r"\1***\2", p)


# ════════════════════════════════════════════════════════════════════════════
#  First-run menu
# ════════════════════════════════════════════════════════════════════════════
def first_run_menu() -> bool:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                state = json.load(f)
            if state.get("use_proxy") is True:
                log_info("Mode (saved): WITH PROXY")
                return True
            if state.get("use_proxy") is False:
                log_info("Mode (saved): WITHOUT PROXY")
                return False
        except Exception:
            pass

    log_info("Select run mode:")
    print(Fore.CYAN  + "  1. Run with proxy")
    print(Fore.CYAN  + "  2. Run without proxy")
    while True:
        choice = input(Fore.YELLOW + "Choice [1/2]: " + Style.RESET_ALL).strip()
        if choice == "1":
            use = True
            break
        if choice == "2":
            use = False
            break
        log_warn("Invalid choice. Try again.")

    try:
        with open(STATE_FILE, "w") as f:
            json.dump({"use_proxy": use}, f)
    except Exception:
        pass
    log_success("Mode saved.")
    return use


# ════════════════════════════════════════════════════════════════════════════
#  HTTP helpers
# ════════════════════════════════════════════════════════════════════════════
def build_session(proxy: Optional[str] = None) -> requests.Session:
    s = requests.Session()
    s.headers.update({
        "User-Agent":  USER_AGENT,
        "Accept":      "application/json",
        "Content-Type": "application/json",
    })
    if proxy:
        s.proxies.update({"http": proxy, "https": proxy})
    return s


def safe_request(method: str, url: str, session: requests.Session,
                 max_retries: int = 3, timeout: int = 20, **kwargs
                 ) -> Optional[requests.Response]:
    last_err: Optional[Exception] = None
    for attempt in range(1, max_retries + 1):
        try:
            r = session.request(method, url, timeout=timeout, **kwargs)
            r.raise_for_status()
            return r
        except requests.exceptions.ProxyError as e:
            log_error(f"Proxy error: {e}")
            return None
        except requests.exceptions.SSLError as e:
            log_error(f"SSL error: {e}")
            return None
        except (requests.exceptions.ConnectionError,
                requests.exceptions.Timeout) as e:
            last_err = e
            log_warn(f"Network error (attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                time.sleep(2 ** attempt + random.random())
        except requests.exceptions.HTTPError as e:
            code = e.response.status_code
            log_warn(f"HTTP {code} (attempt {attempt}/{max_retries})")
            if 400 <= code < 500 and code != 429:
                return None
            last_err = e
            if attempt < max_retries:
                time.sleep(2 ** attempt + random.random())
        except Exception as e:
            log_error(f"Unexpected error: {e}")
            return None
    log_error(f"Request failed after {max_retries} attempts: {last_err}")
    return None


# ════════════════════════════════════════════════════════════════════════════
#  Web3 wallet
# ════════════════════════════════════════════════════════════════════════════
def private_key_to_address(pk: str) -> Optional[str]:
    pk = pk.strip()
    if not pk.startswith("0x"):
        pk = "0x" + pk
    hex_part = pk[2:]
    if len(hex_part) != 64:
        log_error(f"Invalid key length: {len(hex_part)} hex chars (expected 64)")
        return None
    try:
        int(hex_part, 16)
    except ValueError:
        log_error("Private key contains non-hex characters")
        return None
    try:
        return Account.from_key(pk).address
    except Exception as e:
        log_error(f"Invalid private key: {e}")
        return None


def _sign_message(encoded, pk: str):
    """Support eth-account 0.13 (private_key=) and 0.14+ (key=)."""
    try:
        return Account.sign_message(encoded, key=pk)
    except TypeError:
        return Account.sign_message(encoded, private_key=pk)


def sign_login_message(pk: str, nonce: str) -> Optional[Dict[str, str]]:
    if not pk.startswith("0x"):
        pk = "0x" + pk
    message_text = (
        "Welcome to Allox!\n\n"
        "Click to sign in. This action will not trigger a transaction.\n\n"
        f"Nonce: {nonce}"
    )
    try:
        encoded = encode_defunct(text=message_text)
        signed = _sign_message(encoded, pk)
        sig_hex = "0x" + signed.signature.hex()
        return {"message": message_text, "signature": sig_hex}
    except Exception as e:
        log_error(f"Signing failed: {e}")
        return None


# ════════════════════════════════════════════════════════════════════════════
#  API: auth + chat
# ════════════════════════════════════════════════════════════════════════════
def _extract(data: Any, *keys: str, default: Any = None) -> Any:
    if isinstance(data, dict):
        for k in keys:
            if k in data and data[k] is not None:
                return data[k]
        for v in data.values():
            found = _extract(v, *keys, default=None)
            if found is not None:
                return found
    return default


def request_nonce(session: requests.Session, address: str) -> Optional[str]:
    r = safe_request("GET", NONCE_URL, session, params={"wallet": address})
    if not r:
        return None
    try:
        data = r.json()
    except Exception:
        log_error(f"Non-JSON nonce response: {r.text[:120]}")
        return None
    nonce = _extract(data, "nonce")
    if not nonce:
        log_error(f"No nonce in response: {str(data)[:200]}")
    return nonce


def login(session: requests.Session, address: str,
          payload: Dict[str, str]) -> Optional[str]:
    body = {
        "wallet":    address,
        "message":   payload["message"],
        "signature": payload["signature"],
    }
    r = safe_request("POST", LOGIN_URL, session, json=body)
    if not r:
        return None
    try:
        data = r.json()
    except Exception:
        log_error(f"Non-JSON login response: {r.text[:120]}")
        return None
    token = _extract(data, "token", "access_token", "jwt")
    if not token:
        log_error(f"No token in response: {str(data)[:200]}")
    return token


def send_chat(session: requests.Session, token: str,
              prompt: str) -> Optional[Dict[str, Any]]:
    headers = {"Authorization": f"Bearer {token}"}
    r = safe_request("POST", CHAT_URL, session,
                     json={"message": prompt}, headers=headers, timeout=60)
    if not r:
        return None
    try:
        return r.json()
    except Exception:
        log_error(f"Non-JSON chat response: {r.text[:120]}")
        return None


# ════════════════════════════════════════════════════════════════════════════
#  RSS — multi-source, with natural-language prompt wrapping
# ════════════════════════════════════════════════════════════════════════════
def _parse_single_feed(url: str) -> List[str]:
    """
    Fetch & parse ONE RSS/Atom feed. Returns raw titles (no template wrap).
    Empty list on any failure.
    """
    headers = {"User-Agent": USER_AGENT}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        # feedparser handles RSS 2.0 + Atom + RDF cleanly
        if HAS_FEEDPARSER:
            feed = feedparser.parse(r.content)
            return [e.title.strip() for e in feed.entries
                    if hasattr(e, "title") and e.title and e.title.strip()]
        # stdlib fallback: walk the XML tree
        root = ET.fromstring(r.content)
        titles = []
        # RSS 2.0: <channel><item><title>...</title>
        for item in root.iter("item"):
            t = item.findtext("title")
            if t and t.strip():
                titles.append(t.strip())
        # Atom: <feed><entry><title>...</title>
        if not titles:
            for entry in root.iter("entry"):
                t = entry.findtext("title")
                if t and t.strip():
                    titles.append(t.strip())
        return titles
    except Exception as e:
        log_warn(f"RSS fetch failed for {url}: {type(e).__name__}")
        return []


def _wrap_as_prompt(title: str) -> str:
    """Wrap a raw headline in a random natural-language template."""
    template = random.choice(PROMPT_TEMPLATES)
    # Truncate very long titles so the prompt stays under token limits
    if len(title) > 200:
        title = title[:197] + "..."
    # Strip trailing punctuation/whitespace so templates like
    # "... {title}?" don't produce "... Bitcoin hits ATH.?" with double mark.
    title = title.rstrip(".?! \t")
    return template.format(title=title)


def fetch_rss_titles(limit: int = 100) -> List[str]:
    """
    Pull titles from multiple RSS sources, in random order, with deduplication.
    Each title is wrapped in a natural-language template to look more like
    a user query and less like a raw newswire dump.

    Stops as soon as we have `limit` prompts, or all feeds are exhausted.
    """
    feeds = list(RSS_FEEDS)
    random.shuffle(feeds)                # different order each cycle

    seen_titles: set = set()             # dedup across sources
    prompts: List[str] = []
    successful_feeds = 0

    for feed_url in feeds:
        if len(prompts) >= limit:
            break
        titles = _parse_single_feed(feed_url)
        if titles:
            successful_feeds += 1
            log_success(f"RSS: {len(titles)} titles from {feed_url}")
        for t in titles:
            if len(prompts) >= limit:
                break
            key = t.lower().strip()
            if key in seen_titles:
                continue
            seen_titles.add(key)
            prompts.append(_wrap_as_prompt(t))

    if successful_feeds == 0:
        log_warn("All RSS feeds failed — using fallback crypto prompts")
        return [_wrap_as_prompt(p) for p in FALLBACK_PROMPTS]
    if len(prompts) < limit:
        log_warn(f"Only got {len(prompts)} prompts from RSS, padding with fallback")
        for t in FALLBACK_PROMPTS:
            if len(prompts) >= limit:
                break
            prompts.append(_wrap_as_prompt(t))
    return prompts


# ════════════════════════════════════════════════════════════════════════════
#  Per-account worker
# ════════════════════════════════════════════════════════════════════════════
def run_account(pk: str, idx: int, total: int, prompts: List[str],
                use_proxy: bool, proxies: List[str]
                ) -> Tuple[bool, int, str]:
    """
    Returns (ok, final_total_points, error_reason_if_any).
    ok=True means the account logged in AND finished the chat loop
    (limit_reached counts as success; only infrastructure errors fail).
    """
    log_info(f"── Account {idx}/{total} ──")

    address = private_key_to_address(pk)
    if not address:
        return (False, 0, "Invalid private key length or format")
    log_info(f"Wallet: {address}")

    proxy = None
    if use_proxy and proxies:
        proxy = random.choice(proxies)
    session = build_session(proxy)
    if proxy:
        log_info(f"Proxy: {mask_proxy(proxy)}")

    nonce = request_nonce(session, address)
    if not nonce:
        return (False, 0, "Failed to fetch nonce (network / proxy / API error)")

    sig = sign_login_message(pk, nonce)
    if not sig:
        return (False, 0, "Failed to sign login message (eth-account error)")

    token = login(session, address, sig)
    if not token:
        return (False, 0, "Failed to login (no token in response / auth rejected)")

    short = f"{address[:6]}...{address[-4:]}"
    log_success(f"Logged in: {short}")

    total_points = 0
    early_stop = False
    for i in range(1, MAX_CHATS + 1):
        prompt = random.choice(prompts)
        resp = send_chat(session, token, prompt)
        if not resp:
            log_warn(f"Chat {i}/{MAX_CHATS} failed, continuing")
            time.sleep(2)
            continue

        if resp.get("limit_reached") or _extract(resp, "error_code") == "rate_limited":
            log_warn(f"Daily limit reached — stopping account at {i - 1}/{MAX_CHATS}")
            early_stop = True
            break

        pts = _extract(resp, "points_earned", "points", "earned", default=10)
        total_points = _extract(resp, "total_points", "total", "balance",
                                default=total_points + pts)
        remaining = MAX_CHATS - i

        log_success(f"Chat {i}/{MAX_CHATS} Sent | +{pts} Pts | "
                    f"Total: {total_points} | Limit: {remaining}")
        time.sleep(random.uniform(2.0, 5.0))

    log_info(f"Account {short} done. Final total: {total_points} pts"
             + (" (early stop: daily limit)" if early_stop else ""))
    return (True, total_points, "")


# ════════════════════════════════════════════════════════════════════════════
#  Cycle orchestrator + Telegram report
# ════════════════════════════════════════════════════════════════════════════
def sleep_with_countdown(seconds: int) -> None:
    next_run = now_wib() + timedelta(seconds=seconds)
    log_info(f"Cycle complete. Sleeping 24h — next run at "
             f"{next_run.strftime('%Y-%m-%d %H:%M:%S')} WIB")
    slept = 0
    while slept < seconds:
        chunk = min(3600, seconds - slept)
        time.sleep(chunk)
        slept += chunk
        remaining = seconds - slept
        if remaining > 0:
            h, rem = divmod(remaining, 3600)
            m = rem // 60
            log_info(f"Sleeping… {h}h {m}m remaining")


def send_cycle_report(stats: Dict[str, Any]) -> None:
    """Build the report and dispatch to telegram.py (no-op if not configured)."""
    if not HAS_TELEGRAM:
        log_warn("telegram.py not importable — skipping report")
        return

    # Always print the same text locally so the user has a copy in logs
    print()
    print(telegram.format_report(stats))
    print()

    log_info("Sending Telegram report…")
    ok = telegram.send(stats)
    if ok:
        log_success("Telegram report sent.")
    elif not os.getenv("TELEGRAM_CHAT_ID"):
        log_info("TELEGRAM_CHAT_ID not set — report printed to console only.")
    else:
        log_warn("Telegram report failed (see warnings above).")


def run_cycle(cycle: int, accounts: List[str], use_proxy: bool,
              proxies: List[str]) -> Dict[str, Any]:
    started_at  = now_wib().strftime("%Y-%m-%d %H:%M:%S WIB")
    prompts     = fetch_rss_titles(limit=200)
    random.shuffle(prompts)
    while len(prompts) < MAX_CHATS:
        prompts += FALLBACK_PROMPTS
    log_info(f"Loaded {len(prompts)} prompts for this cycle")

    success_count = 0
    failures: List[Tuple[str, str]] = []

    for i, pk in enumerate(accounts, 1):
        try:
            ok, pts, reason = run_account(pk, i, len(accounts),
                                          prompts, use_proxy, proxies)
        except KeyboardInterrupt:
            raise
        except Exception as e:
            ok, pts, reason = False, 0, f"Unhandled exception: {e}"
            log_error(f"Account {i} crashed: {e}")

        if ok:
            success_count += 1
        else:
            # Derive a short wallet id for the report even if login failed.
            # We never expose the private key in logs / reports — only the
            # derived address (when possible) or a redacted key fingerprint.
            addr = private_key_to_address(pk)
            if addr and addr.startswith("0x") and len(addr) >= 8:
                short = f"{addr[:6]}...{addr[-4:]}"
            else:
                # Redact the key itself: show first 4 + last 4 chars only
                k = pk.strip()
                short = (k[:4] + "..." + k[-4:]) if len(k) >= 10 else "<invalid-key>"
            failures.append((short, reason))

        time.sleep(random.uniform(2.0, 4.0))

    finished_at = now_wib().strftime("%Y-%m-%d %H:%M:%S WIB")
    stats = {
        "cycle": cycle,
        "cycle_started_at":  started_at,
        "cycle_finished_at": finished_at,
        "total_accounts":    len(accounts),
        "success_count":     success_count,
        "failures":          failures,
    }
    # Print a small terminal summary too
    log_info(f"Cycle #{cycle}: {success_count}/{len(accounts)} akun sukses, "
             f"{len(failures)} gagal.")
    return stats


def main() -> None:
    banner()
    try:
        accounts = load_accounts()
        proxies  = load_proxies()
        use_proxy = first_run_menu()
        if use_proxy and not proxies:
            log_warn("Proxy file is empty — falling back to no proxy")
            use_proxy = False

        # Notify user about Telegram status at startup (not at 24h mark)
        if HAS_TELEGRAM and os.getenv("TELEGRAM_CHAT_ID") and (
            os.getenv("TELEGRAM_BOT_TOKEN")
            or (os.getenv("TELEGRAM_API_ID")
                and os.getenv("TELEGRAM_API_HASH")
                and os.getenv("TELEGRAM_SESSION"))
        ):
            log_success("Telegram reporting: ENABLED (report at end of each cycle)")
        else:
            log_info("Telegram reporting: DISABLED (set TELEGRAM_* in .env to enable)")

        cycle = 1
        while True:
            log_info(f"══════ CYCLE #{cycle} ══════")
            stats = run_cycle(cycle, accounts, use_proxy, proxies)
            send_cycle_report(stats)
            sleep_with_countdown(CYCLE_SLEEP)
            cycle += 1

    except KeyboardInterrupt:
        print()
        log_warn("Stopped by user. Bye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
