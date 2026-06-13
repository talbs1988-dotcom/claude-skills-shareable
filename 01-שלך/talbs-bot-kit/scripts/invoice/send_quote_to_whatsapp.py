"""
שולח הצעת מחיר (PDF) ללקוח דרך וואטסאפ באמצעות Green API.

שימוש:
  python3 send_quote_to_whatsapp.py \
    --phone "0501234567" \
    --pdf-url "https://...pdf" \
    --caption "היי יעל, מצרפת הצעת מחיר..."

מחזיר JSON עם תוצאת השליחה.
"""
import argparse
import json
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

import os as _os
_HERE = Path(__file__).resolve().parent
_ENV_CANDIDATES = [
    Path(_os.environ["BOT_ENV_PATH"]) if _os.environ.get("BOT_ENV_PATH") else None,
    _HERE / ".env",
    _HERE.parent / ".env",
    _HERE.parent.parent / ".env",
]
ENV = next((p for p in _ENV_CANDIDATES if p and p.exists()), _HERE / ".env")


def load_keys():
    keys = {}
    for line in ENV.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            keys[k.strip()] = v.strip()
    return keys


def normalize_phone(raw):
    """0501234567 או 972501234567 או +972-50-123-4567 → 972501234567"""
    digits = re.sub(r"\D", "", raw)
    if digits.startswith("0"):
        digits = "972" + digits[1:]
    if not digits.startswith("972"):
        digits = "972" + digits
    return digits


def post(url, data, timeout=30):
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/json"}, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode("utf-8")}


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--phone", required=True, help="טלפון הלקוח (כל פורמט)")
    p.add_argument("--pdf-url", required=True, help="URL ל-PDF של הצעת המחיר")
    p.add_argument("--caption", default="", help="טקסט שילווה את ה-PDF")
    p.add_argument("--filename", default="הצעת מחיר.pdf")
    args = p.parse_args()

    env = load_keys()
    instance = env.get("GREEN_API_INSTANCE_ID")
    token = env.get("GREEN_API_TOKEN")
    if not instance or not token:
        print(json.dumps({"ok": False, "error": "חסרים GREEN_API_INSTANCE_ID או GREEN_API_TOKEN"}, ensure_ascii=False))
        sys.exit(1)

    phone = normalize_phone(args.phone)
    chat_id = f"{phone}@c.us"

    url = f"https://api.green-api.com/waInstance{instance}/sendFileByUrl/{token}"
    payload = {
        "chatId": chat_id,
        "urlFile": args.pdf_url,
        "fileName": args.filename,
        "caption": args.caption or " ",
    }

    status, resp = post(url, payload, timeout=60)
    if status != 200:
        print(json.dumps({"ok": False, "status": status, "error": resp}, ensure_ascii=False))
        sys.exit(1)

    print(json.dumps({"ok": True, "chat_id": chat_id, "green_api": resp}, ensure_ascii=False))


if __name__ == "__main__":
    main()
