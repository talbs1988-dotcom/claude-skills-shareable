#!/usr/bin/env python3
"""Daily summary — pull CRM stats from Airtable, send to WhatsApp.

No MCP, no Claude CLI. Pure HTTP. Safe to run from launchd.

Usage:
  python3 daily_summary.py
  python3 daily_summary.py --auto      # skip if already sent today
  python3 daily_summary.py --dry-run   # build message, print it, don't send
"""
from __future__ import annotations

import datetime as dt
import sys
from pathlib import Path
from typing import Any

from _airtable import (
    fmt_currency_ils,
    list_records,
    month_range_iso,
    today_iso,
)
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
LOG_PATH = _HERE / "daily-summary.log"
MARKER_PATH = _HERE.parent / ".last-summary-run"

DEFAULT_BOT_BASE = "http://127.0.0.1:7654"
DEFAULT_TZ = "Asia/Jerusalem"


def _get_field(rec: dict[str, Any], name: str, default: Any = None) -> Any:
    return rec.get("fields", {}).get(name, default)


def count_leads_today(token, base_id, table_id, date_field, today_str):
    formula = f"IS_SAME({{{date_field}}}, '{today_str}', 'day')"
    return len(list_records(token, base_id, table_id,
                            filter_formula=formula, fields=[date_field]))


def count_leads_month(token, base_id, table_id, date_field, month_start, month_end):
    formula = (f"AND(IS_AFTER({{{date_field}}}, '{month_start}'), "
               f"IS_BEFORE({{{date_field}}}, '{month_end}'))")
    # IS_AFTER is strict — we want >= month_start, so use prev day to be safe.
    # Easier: use the date arithmetic Airtable understands.
    formula = (f"AND("
               f"DATETIME_DIFF({{{date_field}}}, '{month_start}', 'days') >= 0,"
               f"DATETIME_DIFF({{{date_field}}}, '{month_end}', 'days') < 0)")
    return len(list_records(token, base_id, table_id,
                            filter_formula=formula, fields=[date_field]))


TERMINAL_STATUSES = ["נסגר", "לא נסגר", "לא רלוונטי", "לא הגיע לפגישה", "ליד כפול"]


def count_open_followups(token, base_id, table_id,
                         status_field, followup_date_field, today_str):
    """Open follow-ups = status='פולואפ' OR (follow-up date passed AND not terminal)."""
    terminal_check = ", ".join(f"{{{status_field}}} != '{s}'" for s in TERMINAL_STATUSES)
    formula = (
        f"AND("
        f"OR({{{status_field}}} = 'פולואפ', {{{status_field}}} = 'פולואפ עתידי', "
        f"AND(NOT(BLANK({{{followup_date_field}}})), "
        f"DATETIME_DIFF({{{followup_date_field}}}, '{today_str}', 'days') <= 0)),"
        f"AND({terminal_check})"
        f")"
    )
    return len(list_records(token, base_id, table_id,
                            filter_formula=formula,
                            fields=[status_field, followup_date_field]))


def deals_today(token, base_id, table_id, date_field, amount_field, today_str):
    formula = f"IS_SAME({{{date_field}}}, '{today_str}', 'day')"
    recs = list_records(token, base_id, table_id, filter_formula=formula,
                        fields=[date_field, amount_field])
    total = sum(float(_get_field(r, amount_field, 0) or 0) for r in recs)
    return len(recs), total


def deals_month(token, base_id, table_id, date_field, amount_field,
                month_start, month_end):
    formula = (f"AND("
               f"DATETIME_DIFF({{{date_field}}}, '{month_start}', 'days') >= 0,"
               f"DATETIME_DIFF({{{date_field}}}, '{month_end}', 'days') < 0)")
    recs = list_records(token, base_id, table_id, filter_formula=formula,
                        fields=[date_field, amount_field])
    total = sum(float(_get_field(r, amount_field, 0) or 0) for r in recs)
    return total


def tasks_completed_today(token, base_id, table_id,
                          status_field, date_field, title_field, today_str):
    formula = (f"AND({{{status_field}}} = 'סגור', "
               f"IS_SAME({{{date_field}}}, '{today_str}', 'day'))")
    recs = list_records(token, base_id, table_id, filter_formula=formula,
                        fields=[status_field, date_field, title_field])
    return [_get_field(r, title_field, "(ללא שם)") for r in recs]


def tasks_open(token, base_id, table_id, status_field, title_field):
    formula = f"OR({{{status_field}}} = 'פתוח', {{{status_field}}} = 'בטיפול')"
    recs = list_records(token, base_id, table_id, filter_formula=formula,
                        fields=[status_field, title_field])
    return [_get_field(r, title_field, "(ללא שם)") for r in recs]


def build_message(stats: dict[str, Any]) -> str:
    today = stats["today_display"]
    parts = [
        f"📅 {today}",
        f"🆕 לידים חדשים היום: {stats['leads_today']}",
        f"📈 סה״כ לידים חודשי: {stats['leads_month']}",
        f"⏳ פולואפים פתוחים: {stats['followups_open']}",
        f"💰 סגירות היום: {stats['deals_count_today']}",
        f"💵 הכנסות היום: {fmt_currency_ils(stats['deals_sum_today'])}",
        f"💵 הכנסות חודש: {fmt_currency_ils(stats['deals_sum_month'])}",
        "",
    ]
    completed = stats["tasks_completed"]
    if completed:
        parts.append("✅ הושלמו היום:")
        for t in completed:
            parts.append(f"   • {t}")
    else:
        parts.append("✅ לא הושלמו משימות היום")
    parts.append("")
    open_tasks = stats["tasks_open"]
    if open_tasks:
        parts.append("📋 עדיין פתוחות:")
        for t in open_tasks:
            parts.append(f"   • {t}")
        parts.append("")
        parts.append("🗓️ רוצה שאשבץ את המשימות הפתוחות ליומן?")
    else:
        parts.append("📋 אין משימות פתוחות 🎯")
    return "\n".join(parts)


def main() -> int:
    args = sys.argv[1:]
    auto = "--auto" in args
    dry = "--dry-run" in args

    log = get_logger("daily-summary", LOG_PATH)
    log.info(f"=== Starting daily summary (auto={auto} dry={dry}) ===")

    env = load_env()
    tz = env.get("BOT_TIMEZONE", DEFAULT_TZ)
    today_str = today_iso(tz)
    today_display = dt.date.fromisoformat(today_str).strftime("%d.%m.%Y")

    if auto and already_sent_today(MARKER_PATH, today_str, log):
        return 0

    try:
        # Accept either AIRTABLE_PAT (Tal's existing convention) or AIRTABLE_API_KEY (skill default)
        token = env.get("AIRTABLE_PAT") or env_get(env, "AIRTABLE_API_KEY")
        base_id = env_get(env, "AIRTABLE_BASE_ID")
        leads_table = env.get("AIRTABLE_LEADS_TABLE", "tblJtOZMKRGnnx4or")
        deals_table = env.get("AIRTABLE_DEALS_TABLE", "tbld7FZCBm2JvSUyn")
        tasks_table = env.get("AIRTABLE_TASKS_TABLE", "tblbM772kokDbyE7q")
        lead_date_field = env.get("AIRTABLE_LEAD_DATE_FIELD", "תאריך כניסת ליד")
        lead_status_field = env.get("AIRTABLE_LEAD_STATUS_FIELD", "סטטוס")
        lead_followup_field = env.get("AIRTABLE_LEAD_FOLLOWUP_DATE_FIELD", "תאריך פולואפ")
        deal_date_field = env.get("AIRTABLE_DEAL_DATE_FIELD", "תאריך סגירה")
        deal_amount_field = env.get("AIRTABLE_DEAL_AMOUNT_FIELD", "סכום עסקה")
        task_status_field = env.get("AIRTABLE_TASK_STATUS_FIELD", "סטטוס")
        task_date_field = env.get("AIRTABLE_TASK_DATE_FIELD", "תאריך סגירה")
        task_title_field = env.get("AIRTABLE_TASK_TITLE_FIELD", "משימה")
        jid = env_get(env, "USER_WHATSAPP_JID")
        bot_base = env.get("BOT_HTTP_BASE", DEFAULT_BOT_BASE)
    except RuntimeError as e:
        log.error(f"Missing config: {e}")
        notify_failure("🚨 בוט WhatsApp",
                       f"חסר במשתני הסביבה: {e}", log)
        return 2

    month_start, month_end = month_range_iso(tz)

    try:
        def fetch():
            return {
                "leads_today": count_leads_today(
                    token, base_id, leads_table, lead_date_field, today_str),
                "leads_month": count_leads_month(
                    token, base_id, leads_table, lead_date_field,
                    month_start, month_end),
                "followups_open": count_open_followups(
                    token, base_id, leads_table,
                    lead_status_field, lead_followup_field, today_str),
                "deals_today": deals_today(
                    token, base_id, deals_table, deal_date_field,
                    deal_amount_field, today_str),
                "deals_sum_month": deals_month(
                    token, base_id, deals_table, deal_date_field,
                    deal_amount_field, month_start, month_end),
                "tasks_completed": tasks_completed_today(
                    token, base_id, tasks_table,
                    task_status_field, task_date_field, task_title_field,
                    today_str),
                "tasks_open": tasks_open(
                    token, base_id, tasks_table,
                    task_status_field, task_title_field),
            }
        raw = with_retry(fetch, attempts=4, base_delay_s=15, log=log,
                         label="airtable_fetch_all")
    except Exception as e:
        log.error(f"Airtable fetch failed: {e}")
        notify_failure("🚨 בוט WhatsApp",
                       "הסיכום היומי לא הצליח למשוך מ-Airtable", log)
        return 3

    deals_count_today, deals_sum_today = raw["deals_today"]
    stats = {
        "today_display": today_display,
        "leads_today": raw["leads_today"],
        "leads_month": raw["leads_month"],
        "followups_open": raw["followups_open"],
        "deals_count_today": deals_count_today,
        "deals_sum_today": deals_sum_today,
        "deals_sum_month": raw["deals_sum_month"],
        "tasks_completed": raw["tasks_completed"],
        "tasks_open": raw["tasks_open"],
    }

    msg = build_message(stats)
    log.info(f"Message:\n{msg}")

    if dry:
        print(msg)
        return 0

    if not wait_for_bot(bot_base, timeout_s=60, log=log):
        notify_failure("🚨 בוט WhatsApp", "הבוט המקומי לא מגיב", log)
        return 4

    try:
        with_retry(
            lambda: _send_or_raise(jid, msg, bot_base, log),
            attempts=3, base_delay_s=20, log=log, label="send_whatsapp",
        )
    except Exception as e:
        log.error(f"Send failed: {e}")
        notify_failure("🚨 בוט WhatsApp",
                       "סיכום יומי לא נשלח אחרי 3 ניסיונות", log)
        return 5

    mark_sent_today(MARKER_PATH, today_str)
    log.info(f"✅ Sent. Marker={today_str}")
    return 0


def _send_or_raise(jid: str, msg: str, bot_base: str, log) -> bool:
    if not send_whatsapp(jid, msg, bot_base, log):
        raise RuntimeError("send_whatsapp returned False")
    return True


if __name__ == "__main__":
    sys.exit(main())
