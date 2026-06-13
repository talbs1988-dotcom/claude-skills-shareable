"""Airtable REST client — pure HTTP, no SDK.

Auth: Personal Access Token (PAT) — same as we used in the .env already.
"""
from __future__ import annotations

import datetime as dt
import urllib.parse
from typing import Any
from zoneinfo import ZoneInfo

import requests

API_BASE = "https://api.airtable.com/v0"


def _headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}",
            "Content-Type": "application/json"}


def list_records(token: str, base_id: str, table_id: str,
                 filter_formula: str | None = None,
                 fields: list[str] | None = None,
                 max_records: int = 1000) -> list[dict[str, Any]]:
    """Page through records. Returns the full list."""
    url = f"{API_BASE}/{base_id}/{table_id}"
    out: list[dict[str, Any]] = []
    offset: str | None = None
    while True:
        params: dict[str, Any] = {"pageSize": 100}
        if filter_formula:
            params["filterByFormula"] = filter_formula
        if fields:
            for f in fields:
                params.setdefault("fields[]", []).append(f)
        if offset:
            params["offset"] = offset
        r = requests.get(url, headers=_headers(token), params=params, timeout=20)
        r.raise_for_status()
        body = r.json()
        out.extend(body.get("records", []))
        if len(out) >= max_records:
            break
        offset = body.get("offset")
        if not offset:
            break
    return out


def today_iso(tz: str = "Asia/Jerusalem") -> str:
    """Today as YYYY-MM-DD in the given timezone."""
    return dt.datetime.now(ZoneInfo(tz)).date().isoformat()


def month_range_iso(tz: str = "Asia/Jerusalem") -> tuple[str, str]:
    """First and (exclusive) last day of current month as YYYY-MM-DD."""
    now = dt.datetime.now(ZoneInfo(tz)).date()
    first = now.replace(day=1)
    if first.month == 12:
        next_first = first.replace(year=first.year + 1, month=1)
    else:
        next_first = first.replace(month=first.month + 1)
    return first.isoformat(), next_first.isoformat()


def fmt_currency_ils(amount: float) -> str:
    """1234.5 → ₪1,234"""
    return f"₪{int(round(amount)):,}"
