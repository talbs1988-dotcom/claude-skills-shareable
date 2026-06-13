"""
יצירת הצעת מחיר בחשבונית ירוקה.

שימוש (מ-CLI או מ-Claude):
  python3 greeninvoice_quote.py \
    --client-name "יעל כהן" \
    --client-id "123456789" \
    --client-phone "0501234567" \
    --client-email "yael@example.com" \
    --description "ליווי 3 חודשים" \
    --amount 12800 \
    --vat added

ערכי vat:
  added    = הסכום שצוין לא כולל מע"מ, צריך להוסיף
  included = הסכום כולל מע"מ
  exempt   = פטור ממע"מ

מחזיר JSON על stdout עם: number, id, url, total
"""
import argparse
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path

# Resolve .env path: priority is (1) explicit env var, (2) script-local .env, (3) parent dir
import os as _os
_HERE = Path(__file__).resolve().parent
_ENV_CANDIDATES = [
    Path(_os.environ["BOT_ENV_PATH"]) if _os.environ.get("BOT_ENV_PATH") else None,
    _HERE / ".env",
    _HERE.parent / ".env",
    _HERE.parent.parent / ".env",
]
ENV = next((p for p in _ENV_CANDIDATES if p and p.exists()), _HERE / ".env")
BASE_URL = "https://api.greeninvoice.co.il/api/v1"


def load_keys():
    keys = {}
    for line in ENV.read_text().splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            keys[k.strip()] = v.strip()
    return keys.get("GREENINVOICE_API_KEY"), keys.get("GREENINVOICE_API_SECRET")


def call(url, data=None, token=None, method=None):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method=method or ("POST" if body else "GET"))
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def get_token():
    key, secret = load_keys()
    if not key or not secret:
        raise RuntimeError("לא נמצאו מפתחות API ב-.env")
    status, resp = call(f"{BASE_URL}/account/token", {"id": key, "secret": secret})
    if status != 200 or "token" not in resp:
        raise RuntimeError(f"כשל בהתחברות ({status}): {resp}")
    return resp["token"]


def create_quote(args, token):
    # מיפוי vat → vatType ברמת הפריט (Green Invoice):
    # 0 = ללא מע"מ (פטור), 1 = כולל מע"מ, 2 = לא כולל (מע"מ מתווסף)
    vat_map = {"added": 2, "included": 1, "exempt": 0}
    vat_type = vat_map.get(args.vat, 2)

    emails = [args.client_email] if args.client_email else []
    phones = [args.client_phone] if args.client_phone else []

    client = {"name": args.client_name, "emails": emails, "phone": args.client_phone or ""}
    if args.client_id:
        client["taxId"] = args.client_id

    payload = {
        "type": 10,  # 10 = הצעת מחיר
        "description": args.description[:100],
        "lang": "he",
        "currency": "ILS",
        "vatType": 1 if args.vat == "included" else (0 if args.vat == "exempt" else 1),
        "client": client,
        "income": [
            {
                "description": args.description,
                "quantity": 1,
                "price": float(args.amount),
                "currency": "ILS",
                "vatType": vat_type,
            }
        ],
    }
    if args.remarks:
        payload["remarks"] = args.remarks

    status, resp = call(f"{BASE_URL}/documents", payload, token=token)
    return status, resp


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--client-name", required=True)
    p.add_argument("--client-id", default="", help="ת.ז. או ח.פ. של הלקוח")
    p.add_argument("--client-phone", default="")
    p.add_argument("--client-email", default="")
    p.add_argument("--description", required=True)
    p.add_argument("--amount", required=True, type=float)
    p.add_argument("--vat", default="added", choices=["added", "included", "exempt"])
    p.add_argument("--remarks", default="")
    args = p.parse_args()

    try:
        token = get_token()
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(1)

    status, resp = create_quote(args, token)
    if status not in (200, 201):
        print(json.dumps({"ok": False, "status": status, "error": resp}, ensure_ascii=False))
        sys.exit(1)

    url_obj = resp.get("url", {})
    pdf_url = ""
    if isinstance(url_obj, dict):
        pdf_url = url_obj.get("origin") or url_obj.get("he") or ""
    elif isinstance(url_obj, str):
        pdf_url = url_obj

    result = {
        "ok": True,
        "number": resp.get("number"),
        "id": resp.get("id"),
        "pdf_url": pdf_url,
        "total_amount": resp.get("amount"),
    }
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
