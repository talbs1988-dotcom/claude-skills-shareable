"""
יצירת מסמך בחשבונית ירוקה (חשבון עסקה / חשבונית מס קבלה / קבלה).

⛔ חשבונית זיכוי (type 405) חסומה — אסור להריץ עם --doc-type 405.

שימוש:
  python3 greeninvoice_invoice.py \
    --doc-type 320 \
    --client-name "יעל כהן" \
    --client-id "123456789" \
    --client-phone "0501234567" \
    --client-email "yael@example.com" \
    --description "ליווי 3 חודשים" \
    --amount 12800 \
    --vat added \
    --payment-type 1

ערכי doc-type (חובה לציין במפורש):
  100 = חשבון עסקה (לפני תשלום, ללא payment)
  320 = חשבונית מס קבלה (קיבלת תשלום + חשבונית מס בו זמנית)
  400 = קבלה בלבד (חשבונית מס כבר יצאה לפני)
  405 = חשבונית זיכוי — 🚫 חסום, ייתן שגיאה

ערכי vat (לא רלוונטי ל-400):
  added   = הסכום לא כולל מע"מ (18% יתווסף)
  exempt  = פטור ממע"מ

ערכי payment-type (לא רלוונטי ל-100, חובה ל-320 ו-400):
  1  = מזומן
  2  = המחאה
  3  = כרטיס אשראי
  4  = העברה בנקאית
  10 = אפליקציית תשלום (bit/paybox)

אימות prefix (אצל טל):
  320 → מספר חייב להתחיל ב-6
  400 → מספר חייב להתחיל ב-8
  100 → אין prefix מוגדר (אזהרה רכה)

מחזיר JSON: ok, doc_type, number, id, pdf_url, total_amount
"""
import argparse
import json
import sys
import urllib.request
import urllib.error
from pathlib import Path
from datetime import date

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


def call(url, data=None, token=None):
    body = json.dumps(data).encode("utf-8") if data is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, data=body, headers=headers, method="POST" if body else "GET")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode("utf-8"))


def get_token():
    key, secret = load_keys()
    status, resp = call(f"{BASE_URL}/account/token", {"id": key, "secret": secret})
    if status != 200 or "token" not in resp:
        raise RuntimeError(f"כשל בהתחברות ({status}): {resp}")
    return resp["token"]


# 🚫 סוגי מסמך מותרים. type 405 (זיכוי) חסום במפורש.
ALLOWED_DOC_TYPES = {100, 320, 400}
BLOCKED_DOC_TYPES = {405}

# Prefix צפוי לפי סוג (אצל טל). אם המספר שחזר לא תואם — אזהרה.
EXPECTED_PREFIX = {
    320: "6",
    400: "8",
    # 100: לא מוגדר עדיין — נשאל את טל
}

DOC_TYPE_NAMES = {
    100: "חשבון עסקה",
    320: "חשבונית מס קבלה",
    400: "קבלה",
}


def build_payload(args, total, doc_vat_type, item_vat_type, client):
    """בונה payload בהתאם לסוג המסמך."""
    payload = {
        "type": args.doc_type,
        "description": args.description[:100],
        "lang": "he",
        "currency": "ILS",
        "client": client,
    }
    if args.remarks:
        payload["remarks"] = args.remarks

    income_line = {
        "description": args.description,
        "quantity": 1,
        "price": float(args.amount),
        "currency": "ILS",
        "vatType": item_vat_type,
    }
    payment_line = {
        "type": args.payment_type,
        "price": total,
        "currency": "ILS",
        "date": str(date.today()),
    }

    if args.doc_type == 100:
        # חשבון עסקה — יש פירוט עסקה (income), אין תיעוד תשלום
        payload["vatType"] = doc_vat_type
        payload["income"] = [income_line]
    elif args.doc_type == 320:
        # חשבונית מס קבלה — גם פירוט עסקה וגם תשלום
        payload["vatType"] = doc_vat_type
        payload["income"] = [income_line]
        payload["payment"] = [payment_line]
    elif args.doc_type == 400:
        # קבלה בלבד — חשבונית המס יצאה כבר. אין מע"מ נוסף, רק רישום תשלום
        payload["vatType"] = 0  # ללא מע"מ — כבר חושב בחשבונית המקורית
        payload["income"] = [{
            "description": args.description,
            "quantity": 1,
            "price": float(args.amount),
            "currency": "ILS",
            "vatType": 0,
        }]
        payload["payment"] = [payment_line]

    return payload


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--doc-type", required=True, type=int,
                   help="סוג מסמך: 100=חשבון עסקה, 320=חשבונית מס קבלה, 400=קבלה. 405 חסום.")
    p.add_argument("--client-name", required=True)
    p.add_argument("--client-id", default="")
    p.add_argument("--client-phone", default="")
    p.add_argument("--client-email", default="")
    p.add_argument("--description", required=True)
    p.add_argument("--amount", required=True, type=float)
    p.add_argument("--vat", default="added", choices=["added", "exempt"])
    p.add_argument("--payment-type", type=int, default=None,
                   help="סוג תשלום (חובה ל-320/400): 1=מזומן, 2=המחאה, 3=אשראי, 4=העברה, 10=bit/paybox")
    p.add_argument("--remarks", default="")
    args = p.parse_args()

    # ⛔ הגנה ראשונה: דחיית חשבונית זיכוי
    if args.doc_type in BLOCKED_DOC_TYPES:
        print(json.dumps({
            "ok": False,
            "error": "חשבונית זיכוי (type 405) חסומה בבוט. עשי ידנית באתר חשבונית ירוקה. אסור לעבור חסימה זו.",
        }, ensure_ascii=False))
        sys.exit(2)

    # ⛔ הגנה שנייה: רק סוגים מותרים
    if args.doc_type not in ALLOWED_DOC_TYPES:
        print(json.dumps({
            "ok": False,
            "error": f"סוג מסמך לא נתמך: {args.doc_type}. מותר רק: 100 (חשבון עסקה), 320 (חשבונית מס קבלה), 400 (קבלה).",
        }, ensure_ascii=False))
        sys.exit(2)

    # אימות payment-type כשרלוונטי
    if args.doc_type in (320, 400) and args.payment_type is None:
        print(json.dumps({
            "ok": False,
            "error": f"חסר --payment-type עבור {DOC_TYPE_NAMES[args.doc_type]}. חובה: 1/2/3/4/10",
        }, ensure_ascii=False))
        sys.exit(2)

    try:
        token = get_token()
    except Exception as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        sys.exit(1)

    # חישוב סכום כולל מע"מ (לא רלוונטי ל-400 שאין בו מע"מ)
    vat_rate = 0.18
    if args.doc_type == 400:
        # קבלה — סכום כפי שהוא, אין חישוב מע"מ
        total = args.amount
        doc_vat_type = 0
        item_vat_type = 0
    elif args.vat == "added":
        total = round(args.amount * (1 + vat_rate), 2)
        doc_vat_type = 0
        item_vat_type = 0
    else:  # exempt
        total = args.amount
        doc_vat_type = 2
        item_vat_type = 2

    client = {"name": args.client_name, "emails": [], "phone": args.client_phone}
    if args.client_id:
        client["taxId"] = args.client_id
    if args.client_email:
        client["emails"] = [args.client_email]

    payload = build_payload(args, total, doc_vat_type, item_vat_type, client)

    status, resp = call(f"{BASE_URL}/documents", payload, token=token)
    if status not in (200, 201):
        print(json.dumps({"ok": False, "status": status, "error": resp}, ensure_ascii=False))
        sys.exit(1)

    url_obj = resp.get("url", {})
    pdf_url = url_obj.get("he") or url_obj.get("origin") or "" if isinstance(url_obj, dict) else str(url_obj)
    number = resp.get("number")

    # ✅ אימות prefix: אם המספר לא תואם לסדרה הצפויה — אזהרה (אבל לא כישלון)
    expected = EXPECTED_PREFIX.get(args.doc_type)
    prefix_warning = None
    if expected and number and not str(number).startswith(expected):
        prefix_warning = (
            f"⚠️ אזהרה: המספר {number} שחזר לא תואם לסדרה הצפויה ({DOC_TYPE_NAMES[args.doc_type]} = {expected}xxxx). "
            f"ייתכן שההגדרות ב-Green Invoice שונו, או שהבוט קרא לסוג לא נכון. בדקי בעיניים."
        )

    out = {
        "ok": True,
        "doc_type": args.doc_type,
        "doc_type_name": DOC_TYPE_NAMES[args.doc_type],
        "number": number,
        "id": resp.get("id"),
        "pdf_url": pdf_url,
        "total_amount": total,
    }
    if prefix_warning:
        out["warning"] = prefix_warning
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
