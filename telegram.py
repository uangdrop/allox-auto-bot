#!/usr/bin/env python3
"""
Allox Auto Bot — Telegram Reporter (optional)
=============================================
Sends a daily cycle report to a Telegram chat. Activated only when both
TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID are set in .env. Otherwise the
module is a no-op (bot.py imports it but skip_sending() returns True).

Two backends are supported:

  1. Telegram Bot API (default, recommended)
     - Cheap, no flood-wait risk
     - The bot must be added to the target chat and sent `/start`
     - Set TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID

  2. Telethon userbot (advanced)
     - No /start needed, can post to any chat
     - Higher risk of rate-limit / account restriction
     - Set TELEGRAM_API_ID, TELEGRAM_API_HASH, TELEGRAM_SESSION,
       TELEGRAM_CHAT_ID

The choice is automatic: if API_ID+HASH+SESSION are present we use Telethon,
otherwise Bot API.
"""

import os
import time
from typing import Dict, Any, Optional

# ── Config (overridable via .env) ─────────────────────────────────────────
BOT_TOKEN   = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
API_ID      = os.getenv("TELEGRAM_API_ID", "").strip()
API_HASH    = os.getenv("TELEGRAM_API_HASH", "").strip()
SESSION     = os.getenv("TELEGRAM_SESSION", "").strip()      # path or name
CHAT_ID     = os.getenv("TELEGRAM_CHAT_ID", "").strip()
PARSE_MODE  = os.getenv("TELEGRAM_PARSE_MODE", "HTML").strip()  # HTML | Markdown


# ── Format the report ─────────────────────────────────────────────────────
def format_report(stats: Dict[str, Any]) -> str:
    """
    Build the report text. `stats` shape:
      {
        "cycle": int,
        "cycle_started_at": str,    # "2026-07-12 19:00:00 WIB"
        "cycle_finished_at": str,
        "total_accounts": int,
        "success_count": int,
        "failures": [                # list of (wallet_short, reason)
            ("0xFCAd...377c", "invalid private key length"),
            ...
        ],
      }
    """
    cycle   = stats.get("cycle", "?")
    started = stats.get("cycle_started_at", "?")
    ended   = stats.get("cycle_finished_at", "?")
    total   = stats.get("total_accounts", 0)
    success = stats.get("success_count", 0)
    fail    = max(total - success, 0)

    lines: list[str] = []
    lines.append(f"📊 <b>Allox Auto Bot — Cycle #{cycle} Report</b>")
    lines.append(f"🕐 {started} → {ended}")
    lines.append("")

    # ── Spec table ────────────────────────────────────────────────────
    lines.append("<pre>")
    lines.append("─" * 43)
    lines.append("| Akun sukses  | " + _pad(str(success), 27) + " |")
    lines.append("| Akun gagal   | " + _pad(str(fail), 27) + " |")
    lines.append("─" * 43)
    lines.append("</pre>")

    # ── Reasons + solutions (only if failures) ────────────────────────
    failures = stats.get("failures", []) or []
    if failures:
        lines.append("")
        lines.append("⚠️ <b>Detail Kegagalan</b>")
        for wallet, reason in failures:
            reason_l = (reason or "unknown")[:80]
            lines.append(f"  • <code>{wallet}</code> — {reason_l}")

        lines.append("")
        lines.append("🛠 <b>Solusi Umum</b>")
        unique = _unique_reasons(failures)
        for r in unique:
            lines.append(f"  • {_reason_solution(r)}")
    else:
        lines.append("")
        lines.append("✅ Semua akun sukses di cycle ini.")

    return "\n".join(lines)


def _pad(s: str, n: int) -> str:
    return s + " " * max(n - len(s), 0)


def _unique_reasons(failures):
    """Reduce duplicate reasons to a unique set for the solution list."""
    seen = []
    for _, reason in failures:
        key = (reason or "").split(":")[0].strip().lower()[:40]
        if key and key not in [k[0] for k in seen]:
            seen.append((key, reason))
    return [r for _, r in seen]


_REASON_HINTS = {
    "invalid private key length": "Cek format key di accounts.txt — harus 64 hex char (0x prefix opsional).",
    "private key contains non-hex": "Hapus karakter non-hex dari private key.",
    "invalid private key":         "Key ditolak eth-account. Generate ulang wallet & ganti key di accounts.txt.",
    "non-json nonce response":     "Server balikin HTML/error page. Cek koneksi/proxy, atau tunggu beberapa menit.",
    "no nonce in response":        "API schema berubah. Update endpoint atau field di bot.py (request_nonce).",
    "failed to fetch nonce":       "Cek koneksi internet / proxy. Bisa juga server Allox lagi down — coba lagi nanti.",
    "non-json login response":     "Login API return non-JSON. Cek proxy / API endpoint.",
    "no token in response":        "API schema berubah. Update login() untuk parse field token yang benar.",
    "failed to login":             "Login ditolak server. Periksa signature format, atau signature message text di bot.py.",
    "failed to sign login":        "eth-account gagal sign. Pastikan library terupdate: pip install -U eth-account.",
    "proxy error":                 "Proxy mati/diblokir. Ganti proxy di proxy.txt atau jalan tanpa proxy.",
    "ssl error":                   "Proxy HTTPS bermasalah. Coba ganti proxy atau disable proxy.",
    "request failed":              "Koneksi/timeout terus. Cek internet, proxy, atau status server Allox.",
    "unhandled exception":         "Bug tak terduga. Lihat log lengkap di console dan laporkan issue di GitHub.",
}


def _reason_solution(reason: str) -> str:
    if not reason:
        return "Cek log lengkap di console."
    low = reason.lower()
    for key, hint in _REASON_HINTS.items():
        if key in low:
            return f"<i>{reason[:60]}</i> → {hint}"
    return f"<i>{reason[:60]}</i> → Cek log console untuk detail lengkap."


# ── Send the report ───────────────────────────────────────────────────────
def send(stats: Dict[str, Any]) -> bool:
    """
    Send the report. Returns True on success, False on failure.
    Skip silently if Telegram isn't configured.

    Env values are re-read at call time so test setups and runtime reloads
    see the latest .env state.
    """
    chat_id   = os.getenv("TELEGRAM_CHAT_ID", "").strip()
    bot_token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    api_id    = os.getenv("TELEGRAM_API_ID", "").strip()
    api_hash  = os.getenv("TELEGRAM_API_HASH", "").strip()
    session   = os.getenv("TELEGRAM_SESSION", "").strip()

    if not chat_id:
        return False
    if not bot_token and not (api_id and api_hash and session):
        return False

    text = format_report(stats)
    if bot_token:
        return _send_bot_api(text, bot_token, chat_id)
    return _send_telethon(text, api_id, api_hash, session, chat_id)


# ── Backend 1: Bot API ────────────────────────────────────────────────────
def _send_bot_api(text: str, bot_token: str, chat_id: str) -> bool:
    import requests
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    parse_mode = os.getenv("TELEGRAM_PARSE_MODE", "HTML").strip()
    # Telegram caps at 4096 chars; reports are tiny but split anyway
    chunks = [text[i:i + 4000] for i in range(0, len(text), 4000)] or [text]
    for chunk in chunks:
        for attempt in range(1, 4):
            try:
                r = requests.post(url, json={
                    "chat_id":    chat_id,
                    "text":       chunk,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                }, timeout=15)
                if r.status_code == 200:
                    break
                # 429 = rate-limit, honour Retry-After
                if r.status_code == 429:
                    wait = int(r.json().get("parameters", {}).get("retry_after", 5))
                    time.sleep(wait)
                    continue
                # 400 with parse error → retry as plain text once
                if r.status_code == 400 and parse_mode:
                    r2 = requests.post(url, json={
                        "chat_id": chat_id, "text": chunk,
                        "disable_web_page_preview": True,
                    }, timeout=15)
                    if r2.status_code == 200:
                        break
                print(f"[TG] HTTP {r.status_code}: {r.text[:120]}")
                return False
            except Exception as e:
                print(f"[TG] send error: {e}")
                if attempt < 3:
                    time.sleep(2 ** attempt)
                else:
                    return False
    return True


# ── Backend 2: Telethon userbot ────────────────────────────────────────────
_telethon_client = None


def _send_telethon(text: str, api_id: str, api_hash: str,
                   session: str, chat_id: str) -> bool:
    global _telethon_client
    try:
        from telethon.sync import TelegramClient  # type: ignore
    except ImportError:
        print("[TG] telethon not installed — pip install telethon")
        return False

    parse_mode = os.getenv("TELEGRAM_PARSE_MODE", "HTML").strip().lower()
    try:
        if _telethon_client is None:
            _telethon_client = TelegramClient(session, int(api_id), api_hash)
            _telethon_client.start()
        for chunk in _chunk_text(text):
            _telethon_client.send_message(chat_id, chunk, parse_mode=parse_mode)
        return True
    except Exception as e:
        print(f"[TG] telethon send failed: {e}")
        return False


def _chunk_text(text: str, size: int = 4000):
    return [text[i:i + size] for i in range(0, len(text), size)] or [text]


# ── Manual CLI for testing ────────────────────────────────────────────────
if __name__ == "__main__":
    sample = {
        "cycle": 1,
        "cycle_started_at":  "2026-07-12 19:00:00 WIB",
        "cycle_finished_at": "2026-07-12 19:42:00 WIB",
        "total_accounts": 3,
        "success_count": 1,
        "failures": [
            ("0xFCAd...377c", "Invalid private key length: 8 hex chars (expected 64)"),
            ("0x9B12...aa91", "No nonce in response: {'error': 'rate_limited'}"),
        ],
    }
    print(format_report(sample))
    print("\n--- sending ---")
    ok = send(sample)
    print("send ok:", ok)
