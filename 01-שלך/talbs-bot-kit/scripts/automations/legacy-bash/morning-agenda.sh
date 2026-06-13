#!/bin/bash
# Morning Agenda — daily automation that pulls today's calendar events
# and sends them as a WhatsApp message to the bot owner.
#
# Reads configuration from .env in the same directory as this script.
# Required .env variables:
#   USER_NAME              — display name (e.g. "שרה")
#   USER_WHATSAPP_JID      — full JID (e.g. "972501234567@s.whatsapp.net")
#   CLAUDE_BIN             — path to claude CLI binary (default: "claude")
#   BOT_HTTP_PORT          — bot's HTTP port (default: 7654)
set -u

SCRIPT_DIR="$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# ---------- load .env ----------
if [ -f "$SCRIPT_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$SCRIPT_DIR/.env"
    set +a
fi

: "${USER_NAME:?missing USER_NAME in .env}"
: "${USER_WHATSAPP_JID:?missing USER_WHATSAPP_JID in .env}"
: "${CLAUDE_BIN:=claude}"
: "${BOT_HTTP_PORT:=7654}"

# ---------- paths ----------
LOG="$SCRIPT_DIR/morning-agenda.log"
LAST_RUN_FILE="$SCRIPT_DIR/.last-agenda-run"
MSG_FILE="/tmp/morning-agenda-msg-$$.txt"
BOT_LOG="$SCRIPT_DIR/green-api-bot.log"
BOT_BASE="http://127.0.0.1:${BOT_HTTP_PORT}"
BOT_SEND="$BOT_BASE/group/send"
TODAY=$(date +%Y-%m-%d)

# ---------- auto mode (skip if already ran today) ----------
AUTO_MODE=false
[ "${1:-}" = "--auto" ] && AUTO_MODE=true

echo "" >> "$LOG"
echo "===== [$(date)] Starting morning agenda (auto=$AUTO_MODE) =====" >> "$LOG"

if [ "$AUTO_MODE" = "true" ] && [ -f "$LAST_RUN_FILE" ]; then
    LAST_RUN=$(cat "$LAST_RUN_FILE" 2>/dev/null || echo "")
    if [ "$LAST_RUN" = "$TODAY" ]; then
        echo "[$(date)] Already sent today ($TODAY) — skipping" >> "$LOG"
        exit 0
    fi
fi

# ---------- wait for bot HTTP ----------
echo "[$(date)] Waiting for bot to be reachable (up to 120s)..." >> "$LOG"
BOT_READY=false
for i in $(seq 1 60); do
    if curl -s -m 2 "$BOT_BASE/" -o /dev/null 2>/dev/null; then
        BOT_READY=true
        echo "[$(date)] Bot HTTP reachable after ${i}*2s" >> "$LOG"
        break
    fi
    sleep 2
done
if [ "$BOT_READY" != "true" ]; then
    echo "[$(date)] ERROR: bot HTTP unreachable after 120s — aborting" >> "$LOG"
    exit 1
fi

sleep 15

# ---------- build prompt (uses Google Calendar MCP) ----------
PROMPT="משוך את כל הפגישות שלי להיום (היום הנוכחי באזור זמן Asia/Jerusalem) **דרך Google Calendar MCP בלבד** (mcp__claude_ai_Google_Calendar). אסור להשתמש באפליקציית Calendar של ה-Mac, אסור osascript, אסור לקרוא מ-~/Library/Calendars. רק MCP.

החזר אך ורק את ההודעה הבאה — בלי טקסט נוסף, בלי הסברים, בלי backticks, בלי כותרות, בלי הקדמות. רק הטקסט הסופי שיישלח לוואטסאפ.

אם יש פגישות היום, הפורמט המדויק (כל פגישה בשורה נפרדת עם ✅ בהתחלה, ממוינות לפי שעה):
היי ${USER_NAME} בוקר טוב 😊
סדר היום שלך הוא:
✅ HH:MM - כותרת הפגישה
✅ HH:MM - כותרת הפגישה

האם יש לך משימה בשבילי להיום?

יום מקסים ${USER_NAME}, תני בראש!

תזכורת: כל יום הוא יום לעשות מעשים טובים 🔥

אם אין פגישות היום, הפורמט:
היי ${USER_NAME} בוקר טוב 😊
אין לך פגישות היום, יום פנוי 🎉

האם יש לך משימה בשבילי להיום?

יום מקסים ${USER_NAME}, תני בראש!

תזכורת: כל יום הוא יום לעשות מעשים טובים 🔥"

"$CLAUDE_BIN" -p --permission-mode bypassPermissions "$PROMPT" > "$MSG_FILE" 2>> "$LOG"
CLAUDE_EXIT=$?

if [ $CLAUDE_EXIT -ne 0 ] || [ ! -s "$MSG_FILE" ]; then
    echo "[$(date)] ERROR: Claude CLI failed (exit=$CLAUDE_EXIT) or empty output" >> "$LOG"
    exit 1
fi

echo "[$(date)] Message generated:" >> "$LOG"
cat "$MSG_FILE" >> "$LOG"
echo "" >> "$LOG"

JSON=$(/usr/bin/jq -n --arg jid "$USER_WHATSAPP_JID" --rawfile text "$MSG_FILE" '{jid: $jid, text: $text}')

verify_delivered() {
    local since_line=$1
    local timeout=$2
    for j in $(seq 1 "$timeout"); do
        sleep 1
        if tail -n +"$since_line" "$BOT_LOG" 2>/dev/null | grep -qF "📤 /group/send"; then
            return 0
        fi
    done
    return 1
}

restart_bot() {
    echo "[$(date)] 🔧 restarting bot" >> "$LOG"
    pkill -f "green-api-bot.js" 2>/dev/null
    sleep 5
    # launchd KeepAlive (Mac) / Task Scheduler (Windows) / Railway (cloud) will respawn
    for k in $(seq 1 20); do
        sleep 2
        if curl -s -m 2 "$BOT_BASE/" -o /dev/null 2>/dev/null; then
            echo "[$(date)] ✅ bot back up after $((k*2))s" >> "$LOG"
            sleep 5
            return 0
        fi
    done
    echo "[$(date)] ❌ bot failed to recover" >> "$LOG"
    return 1
}

SUCCESS=false
for cycle in 1 2 3; do
    LINE_BEFORE=$(wc -l < "$BOT_LOG" 2>/dev/null || echo 0)
    LINE_BEFORE=$((LINE_BEFORE + 1))

    HTTP_CODE=$(curl -s -o "/tmp/morning-agenda-resp-$$.txt" -w "%{http_code}" \
        -X POST "$BOT_SEND" \
        -H 'Content-Type: application/json' \
        -d "$JSON" --max-time 30)
    BODY=$(cat "/tmp/morning-agenda-resp-$$.txt")
    echo "[$(date)] cycle $cycle: HTTP $HTTP_CODE body=$BODY" >> "$LOG"

    if [ "$HTTP_CODE" = "200" ] && echo "$BODY" | grep -q '"ok":true'; then
        if verify_delivered "$LINE_BEFORE" 12; then
            echo "[$(date)] ✅ delivery verified" >> "$LOG"
            SUCCESS=true
            break
        else
            echo "[$(date)] ⚠️ HTTP 200 but log not updated — Green API likely queued it" >> "$LOG"
            SUCCESS=true
            break
        fi
    fi

    [ $cycle -lt 3 ] && restart_bot
done

# Cleanup temp files
rm -f "$MSG_FILE" "/tmp/morning-agenda-resp-$$.txt"

if [ "$SUCCESS" != "true" ]; then
    echo "[$(date)] ❌ delivery failed after 3 cycles" >> "$LOG"
    # macOS notification (silently fails on other OS)
    osascript -e 'display notification "הודעת הבוקר לא נמסרה אחרי 3 ניסיונות" with title "🚨 WhatsApp Bot"' 2>/dev/null || true
    exit 1
fi

echo "$TODAY" > "$LAST_RUN_FILE"
echo "[$(date)] ✅ Done (saved last-run=$TODAY)" >> "$LOG"
