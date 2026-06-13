#!/usr/bin/env python3
"""Morning agenda — fetch today's Google Calendar events, send to WhatsApp.

No MCP, no Claude CLI. Pure HTTP. Safe to run from launchd.

Usage:
  python3 morning_agenda.py            # always run
  python3 morning_agenda.py --auto     # skip if already sent today
  python3 morning_agenda.py --dry-run  # build message, print it, don't send
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

from _airtable import today_iso
from _gcal import fetch_ical, format_morning_agenda, list_events_today
from _helpers import (
    already_sent_today,
    env_get,
    get_logger,
    load_env,
    mark_sent_today,
    notify_failure,
    send_whatsapp,
    wait_for_bot,
    with_retry,
)

_HERE = Path(__file__).resolve().parent
LOG_PATH = _HERE / "morning-agenda.log"
MARKER_PATH = _HERE.parent / ".last-agenda-run"  # keep same path as bash script

DEFAULT_BOT_BASE = "http://127.0.0.1:7654"
DEFAULT_TZ = "Asia/Jerusalem"
DEFAULT_USER_NAME = "טל"


def main() -> int:
    args = sys.argv[1:]
    auto = "--auto" in args
    dry = "--dry-run" in args

    log = get_logger("morning-agenda", LOG_PATH)
    log.info(f"=== Starting morning agenda (auto={auto} dry={dry}) ===")

    env = load_env()
    today = today_iso(env.get("BOT_TIMEZONE", DEFAULT_TZ))

    if auto and already_sent_today(MARKER_PATH, today, log):
        return 0

    try:
        ical_url = env_get(env, "GOOGLE_CALENDAR_ICAL_URL")
        tz = env.get("BOT_TIMEZONE", DEFAULT_TZ)
        user_name = env.get("USER_NAME", DEFAULT_USER_NAME)
        jid = env_get(env, "USER_WHATSAPP_JID")
        bot_base = env.get("BOT_HTTP_BASE", DEFAULT_BOT_BASE)
    except RuntimeError as e:
        log.error(f"Missing config: {e}")
        notify_failure("🚨 בוט WhatsApp",
                       f"חסר במשתני הסביבה: {e}", log)
        return 2

    try:
        ics_text = with_retry(
            lambda: fetch_ical(ical_url),
            attempts=4, base_delay_s=15, log=log, label="fetch_ical",
        )
        events = list_events_today(ics_text, tz)
    except Exception as e:
        log.error(f"Google Calendar fetch failed after retries: {e}")
        notify_failure("🚨 בוט WhatsApp",
                       "הסקריפט נכשל למשוך אגנדה מ-Google Calendar", log)
        return 3

    msg = format_morning_agenda(user_name, events)
    log.info(f"Events found: {len(events)}")
    log.info(f"Message:\n{msg}")

    if dry:
        print(msg)
        return 0

    if not wait_for_bot(bot_base, timeout_s=120, log=log):
        notify_failure("🚨 בוט WhatsApp",
                       "הבוט המקומי לא מגיב", log)
        return 4

    try:
        ok = with_retry(
            lambda: _send_or_raise(jid, msg, bot_base, log),
            attempts=3, base_delay_s=20, log=log, label="send_whatsapp",
        )
    except Exception as e:
        log.error(f"Send failed after retries: {e}")
        notify_failure("🚨 בוט WhatsApp",
                       "אגנדת הבוקר לא נשלחה אחרי 3 ניסיונות", log)
        return 5

    if ok:
        mark_sent_today(MARKER_PATH, today)
        log.info(f"✅ Sent. Marker={today}")
        return 0
    return 6


def _send_or_raise(jid: str, msg: str, bot_base: str, log) -> bool:
    if not send_whatsapp(jid, msg, bot_base, log):
        raise RuntimeError("send_whatsapp returned False")
    return True


if __name__ == "__main__":
    sys.exit(main())
