#!/bin/bash
# Daily Summary — sends end-of-day CRM summary from Airtable to the bot owner.
#
# Reads configuration from .env in the same directory as this script.
# Required .env variables:
#   USER_WHATSAPP_JID          — full JID (e.g. "972501234567@s.whatsapp.net")
#   AIRTABLE_BASE_ID           — base ID (appXXX)
#   TABLE_LEADS_ID             — table ID for leads
#   TABLE_TASKS_ID             — table ID for tasks
#   TABLE_TRANSACTIONS_ID      — table ID for transactions (optional)
#   CLAUDE_BIN                 — path to claude CLI (default: "claude")
#   BOT_HTTP_PORT              — bot's HTTP port (default: 7654)
set -u

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# ---------- load .env ----------
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.env"
    set +a
fi

: "${USER_WHATSAPP_JID:?missing USER_WHATSAPP_JID in .env}"
: "${AIRTABLE_BASE_ID:?missing AIRTABLE_BASE_ID in .env}"
: "${TABLE_LEADS_ID:?missing TABLE_LEADS_ID in .env}"
: "${TABLE_TASKS_ID:?missing TABLE_TASKS_ID in .env}"
: "${TABLE_TRANSACTIONS_ID:=}"  # optional
: "${CLAUDE_BIN:=claude}"
: "${BOT_HTTP_PORT:=7654}"

# ---------- paths ----------
LOG="$SCRIPT_DIR/daily-summary.log"
LAST_RUN_FILE="$SCRIPT_DIR/.last-summary-run"
MSG_FILE="/tmp/daily-summary-msg-$$.txt"
BOT_BASE="http://127.0.0.1:${BOT_HTTP_PORT}"
BOT_SEND="$BOT_BASE/group/send"
TODAY=$(date +%Y-%m-%d)

AUTO_MODE=false
[ "${1:-}" = "--auto" ] && AUTO_MODE=true

echo "" >> "$LOG"
echo "===== [$(date)] Starting daily summary (auto=$AUTO_MODE) =====" >> "$LOG"

if [ "$AUTO_MODE" = "true" ] && [ -f "$LAST_RUN_FILE" ]; then
    LAST_RUN=$(cat "$LAST_RUN_FILE" 2>/dev/null || echo "")
    if [ "$LAST_RUN" = "$TODAY" ]; then
        echo "[$(date)] Already sent today — skipping" >> "$LOG"
        exit 0
    fi
fi

# Wait for bot HTTP
echo "[$(date)] Waiting for bot HTTP (up to 60s)..." >> "$LOG"
for i in $(seq 1 30); do
    if curl -s -m 2 "$BOT_BASE/" -o /dev/null 2>/dev/null; then
        echo "[$(date)] Bot reachable after ${i}*2s" >> "$LOG"
        break
    fi
    sleep 2
done

# ---------- build prompt (Airtable MCP) ----------
# Build the transactions section conditionally
if [ -n "$TABLE_TRANSACTIONS_ID" ]; then
    TX_SECTION="2. טבלת \"עסקאות\" (tableId: ${TABLE_TRANSACTIONS_ID}):
   - ספור עסקאות ש\"תאריך סגירה\" שלהן הוא היום
   - סכם \"סכום עסקה\" של עסקאות שנסגרו היום (הכנסות יום)
   - סכם \"סכום עסקה\" של כל העסקאות החודש (הכנסות חודש)
"
    TX_OUTPUT="💰 סגירות היום: N
💵 הכנסות היום: ₪X,XXX
💵 הכנסות חודש: ₪X,XXX
"
else
    TX_SECTION=""
    TX_OUTPUT=""
fi

PROMPT="משוך לי נתונים מ-Airtable (baseId: ${AIRTABLE_BASE_ID}) לסיכום היום.

**השתמש ב-Airtable MCP בלבד** (mcp__claude_ai_Airtable). פעולות נדרשות:

1. טבלת \"לידים\" (tableId: ${TABLE_LEADS_ID}):
   - ספור רשומות ש\"תאריך כניסת ליד\" שלהן הוא היום (אזור זמן Asia/Jerusalem)
   - ספור רשומות ש\"תאריך כניסת ליד\" שלהן הוא בחודש הנוכחי
   - ספור פולואפים פתוחים — \"סטטוס\" = \"פולואפ\" או \"תאריך פולואפ\" <= היום ועדיין לא נסגרו

${TX_SECTION}

3. טבלת \"משימות\" (tableId: ${TABLE_TASKS_ID}):
   - \"הושלמו היום\" — \"סטטוס\" = \"סגור\" ו-\"תאריך סגירה\" = היום
   - \"פתוחות\" — \"סטטוס\" = \"פתוח\" או \"בטיפול\"

החזר אך ורק את ההודעה הבאה — בלי טקסט נוסף, בלי הסברים, בלי backticks, בלי הקדמות. רק הטקסט הסופי שיישלח לוואטסאפ.

הפורמט המדויק:
📅 DD.MM.YYYY
🆕 לידים חדשים היום: N
📈 סה״כ לידים חודשי: N
⏳ פולואפים פתוחים: N
${TX_OUTPUT}
✅ הושלמו היום:
   • משימה 1
   • משימה 2

📋 עדיין פתוחות:
   • משימה 3
   • משימה 4

🗓️ רוצה שאשבץ את המשימות הפתוחות ליומן?

חוקים על תוכן הסיכום:
- אם אין משימות שהושלמו היום, כתוב: \"✅ לא הושלמו משימות היום\"
- אם אין משימות פתוחות, כתוב: \"📋 אין משימות פתוחות 🎯\" ודלג על שורת \"🗓️ רוצה שאשבץ\"
- אם אין עסקאות היום, \"💰 סגירות היום: 0\" ו-\"💵 הכנסות היום: ₪0\"
- המספרים בפורמט ₪ עם פסיק לאלפים (לדוגמה ₪12,800)"

"$CLAUDE_BIN" -p --permission-mode bypassPermissions "$PROMPT" > "$MSG_FILE" 2>> "$LOG"
CLAUDE_EXIT=$?

if [ $CLAUDE_EXIT -ne 0 ] || [ ! -s "$MSG_FILE" ]; then
    echo "[$(date)] ERROR: Claude CLI failed (exit=$CLAUDE_EXIT) or empty" >> "$LOG"
    exit 1
fi

echo "[$(date)] Message:" >> "$LOG"
cat "$MSG_FILE" >> "$LOG"
echo "" >> "$LOG"

JSON=$(/usr/bin/jq -n --arg jid "$USER_WHATSAPP_JID" --rawfile text "$MSG_FILE" '{jid: $jid, text: $text}')

HTTP_CODE=$(curl -s -o "/tmp/daily-summary-resp-$$.txt" -w "%{http_code}" \
    -X POST "$BOT_SEND" \
    -H 'Content-Type: application/json' \
    -d "$JSON" --max-time 30)
BODY=$(cat "/tmp/daily-summary-resp-$$.txt")
echo "[$(date)] HTTP $HTTP_CODE body=$BODY" >> "$LOG"

rm -f "$MSG_FILE" "/tmp/daily-summary-resp-$$.txt"

if [ "$HTTP_CODE" = "200" ] && echo "$BODY" | grep -q '"ok":true'; then
    echo "$TODAY" > "$LAST_RUN_FILE"
    echo "[$(date)] ✅ Daily summary sent" >> "$LOG"
    exit 0
fi

echo "[$(date)] ❌ Send failed" >> "$LOG"
osascript -e 'display notification "סיכום יומי לא נשלח" with title "🚨 WhatsApp Bot"' 2>/dev/null || true
exit 1
