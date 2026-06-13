"""Shared helpers for scheduled bot automations.

Pure stdlib + `requests`. No MCP, no Claude CLI. Safe to run from launchd.
"""
from __future__ import annotations

import json
import logging
import logging.handlers
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Callable

import requests

_HERE = Path(__file__).resolve().parent
_ENV_CANDIDATES = [
    Path(os.environ["BOT_ENV_PATH"]) if os.environ.get("BOT_ENV_PATH") else None,
    _HERE / ".env",
    _HERE.parent / ".env",
    Path("/Users/talbs/אוטומציות/.env"),
]
ENV_PATH = next((p for p in _ENV_CANDIDATES if p and p.exists()), None)


def load_env() -> dict[str, str]:
    """Load .env into a dict. Does NOT mutate os.environ unless caller wants it."""
    out: dict[str, str] = {}
    if ENV_PATH is None:
        return out
    for line in ENV_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, _, v = line.partition("=")
        k = k.strip()
        v = v.strip()
        # If value isn't quoted, strip trailing '# comment'
        if v and v[0] not in ('"', "'") and "#" in v:
            # split on '  #' or ' #' to avoid breaking values that contain '#'
            for sep in ("  #", " #", "\t#"):
                if sep in v:
                    v = v.split(sep, 1)[0].rstrip()
                    break
        v = v.strip('"').strip("'")
        out[k] = v
    return out


def env_get(env: dict[str, str], key: str, default: str | None = None) -> str:
    """Get an env var, preferring the .env dict but falling back to process env."""
    if key in env and env[key]:
        return env[key]
    val = os.environ.get(key, default)
    if val is None:
        raise RuntimeError(f"Missing required env var: {key}")
    return val


def get_logger(name: str, log_path: Path) -> logging.Logger:
    """File logger with rotation. Also mirrors to stderr so launchd captures it."""
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s",
                            datefmt="%Y-%m-%d %H:%M:%S")
    fh = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=2_000_000, backupCount=3, encoding="utf-8"
    )
    fh.setFormatter(fmt)
    logger.addHandler(fh)
    sh = logging.StreamHandler(sys.stderr)
    sh.setFormatter(fmt)
    logger.addHandler(sh)
    return logger


def wait_for_bot(base_url: str, timeout_s: int = 120, log: logging.Logger | None = None) -> bool:
    """Poll the bot's HTTP server until it responds. Returns True if up."""
    deadline = time.monotonic() + timeout_s
    attempts = 0
    while time.monotonic() < deadline:
        attempts += 1
        try:
            r = requests.get(base_url + "/", timeout=2)
            if r.status_code < 500:
                if log:
                    log.info(f"Bot reachable after {attempts} attempts")
                return True
        except requests.RequestException:
            pass
        time.sleep(2)
    if log:
        log.error(f"Bot unreachable after {timeout_s}s")
    return False


def send_whatsapp(jid: str, text: str, bot_base: str,
                  log: logging.Logger | None = None) -> bool:
    """POST a message to the local bot HTTP server. Returns True if delivered."""
    payload = {"jid": jid, "text": text}
    try:
        r = requests.post(
            bot_base + "/group/send",
            json=payload,
            timeout=30,
        )
    except requests.RequestException as e:
        if log:
            log.error(f"HTTP error sending WhatsApp: {e}")
        return False
    if r.status_code != 200:
        if log:
            log.error(f"Bot returned {r.status_code}: {r.text[:300]}")
        return False
    try:
        body = r.json()
    except ValueError:
        if log:
            log.error(f"Non-JSON bot response: {r.text[:300]}")
        return False
    if body.get("ok") is True:
        if log:
            log.info("WhatsApp delivered (bot ok=true)")
        return True
    if log:
        log.error(f"Bot ok=false: {body}")
    return False


def with_retry(fn: Callable[[], Any], attempts: int = 5,
               base_delay_s: float = 30,
               log: logging.Logger | None = None,
               label: str = "operation") -> Any:
    """Retry fn() with exponential backoff. Returns fn's result on success.

    Raises the last exception if all attempts fail.
    """
    last_exc: Exception | None = None
    for i in range(1, attempts + 1):
        try:
            return fn()
        except Exception as e:
            last_exc = e
            wait = base_delay_s * (2 ** (i - 1))
            if log:
                log.warning(f"{label} attempt {i}/{attempts} failed: {e}. "
                           f"Retrying in {wait:.0f}s")
            if i < attempts:
                time.sleep(wait)
    assert last_exc is not None
    raise last_exc


def notify_failure(title: str, msg: str, log: logging.Logger | None = None) -> None:
    """Best-effort macOS notification. Never raises."""
    try:
        subprocess.run(
            ["osascript", "-e",
             f'display notification "{msg}" with title "{title}" sound name "Sosumi"'],
            check=False, timeout=5,
        )
        if log:
            log.info(f"Notification: {title} — {msg}")
    except Exception as e:
        if log:
            log.warning(f"Notification failed: {e}")


def already_sent_today(marker_path: Path, today: str, log: logging.Logger | None = None) -> bool:
    """Idempotency guard. Returns True if marker_path already records today's date."""
    if not marker_path.exists():
        return False
    try:
        last = marker_path.read_text(encoding="utf-8").strip()
    except OSError:
        return False
    if last == today:
        if log:
            log.info(f"Already sent today ({today}) — skipping")
        return True
    return False


def mark_sent_today(marker_path: Path, today: str) -> None:
    marker_path.write_text(today, encoding="utf-8")
