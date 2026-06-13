#!/bin/bash
# Health check for green-api-bot.
# Runs every hour (via launchd/Task Scheduler/cron). If bot is unresponsive,
# restarts it. If it can't recover, sends push notification.
#
# Reads configuration from .env in the same directory as this script.
# Required .env variables:
#   USER_WHATSAPP_JID      — full JID for self-notification
#   NTFY_TOPIC             — ntfy.sh topic for push notifications
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

: "${USER_WHATSAPP_JID:?missing USER_WHATSAPP_JID in .env}"
: "${NTFY_TOPIC:?missing NTFY_TOPIC in .env}"
: "${BOT_HTTP_PORT:=7654}"

# ---------- paths ----------
LOG="$SCRIPT_DIR/health-check.log"
BOT_LOG="$SCRIPT_DIR/green-api-bot.log"
BOT_BASE="http://127.0.0.1:${BOT_HTTP_PORT}"
BOT_SEND="$BOT_BASE/group/send"
NTFY_URL="https://ntfy.sh/${NTFY_TOPIC}"

# ---------- thresholds (in seconds/minutes) ----------
STUCK_REPLY_THRESHOLD_MIN=5
STUCK_INBOUND_RECENCY_MIN=10
POLL_STALE_SEC=120  # if no successful poll in 2min, bot is sick

echo "" >> "$LOG"
echo "[$(date)] === health check ===" >> "$LOG"

push_ntfy() {
    local title="$1" body="$2"
    curl -s --max-time 10 \
        -H "Title: ${title}" \
        -H "Priority: high" \
        -H "Tags: warning,robot" \
        -d "${body}" \
        "$NTFY_URL" -o /dev/null 2>/dev/null
}

is_responsive() {
    local state_json
    state_json=$(curl -s -m 5 "$BOT_BASE/state" 2>/dev/null)
    [ -z "$state_json" ] && return 0

    local now_ms last_in last_out gap_min recency_min poll_stale
    now_ms=$(($(date +%s) * 1000))
    last_in=$(echo "$state_json" | /usr/bin/jq -r '[.feed[]? | select(.dir=="in") | .t] | last // 0')
    last_out=$(echo "$state_json" | /usr/bin/jq -r '[.feed[]? | select(.dir=="out") | .t] | last // 0')
    poll_stale=$(echo "$state_json" | /usr/bin/jq -r '.lastPollAgoSec // 0')

    # Polling alive?
    if [ "$poll_stale" -gt "$POLL_STALE_SEC" ]; then
        echo "[$(date)]   ❌ polling stale (${poll_stale}s)" >> "$LOG"
        return 1
    fi

    # Any recent inbound stuck without reply?
    [ "$last_in" = "0" ] && return 0
    recency_min=$(( (now_ms - last_in) / 60000 ))
    [ "$recency_min" -gt "$STUCK_INBOUND_RECENCY_MIN" ] && return 0

    if [ "$last_out" -lt "$last_in" ]; then
        gap_min=$(( (now_ms - last_in) / 60000 ))
        if [ "$gap_min" -ge "$STUCK_REPLY_THRESHOLD_MIN" ]; then
            echo "[$(date)]   ❌ stuck: inbound ${gap_min}m ago without reply" >> "$LOG"
            return 1
        fi
    fi
    return 0
}

is_healthy() {
    pgrep -f "green-api-bot.js" > /dev/null 2>&1 || { echo "[$(date)]   ❌ process not running" >> "$LOG"; return 1; }
    curl -s -m 5 "$BOT_BASE/" -o /dev/null 2>/dev/null || { echo "[$(date)]   ❌ HTTP ${BOT_HTTP_PORT} unreachable" >> "$LOG"; return 1; }
    is_responsive || return 1
    return 0
}

if is_healthy; then
    echo "[$(date)] ✅ healthy" >> "$LOG"
    exit 0
fi

echo "[$(date)] ❌ UNHEALTHY — restarting" >> "$LOG"
pkill -f "green-api-bot.js" 2>/dev/null
sleep 5

for i in $(seq 1 30); do
    sleep 3
    if is_healthy; then
        RECOVERY_TIME=$((i*3))
        echo "[$(date)] ✅ recovered after ${RECOVERY_TIME}s" >> "$LOG"
        TEXT="🔧 הבוט אותחל אוטומטית ב-$(date '+%H:%M') ופעיל מחדש ✅"
        JSON=$(/usr/bin/jq -n --arg jid "$USER_WHATSAPP_JID" --arg text "$TEXT" '{jid: $jid, text: $text}')
        curl -s -X POST "$BOT_SEND" -H 'Content-Type: application/json' -d "$JSON" --max-time 30 -o /dev/null 2>/dev/null
        exit 0
    fi
done

echo "[$(date)] 🚨 FAILED to recover after 90s" >> "$LOG"
osascript -e 'display notification "הבוט WhatsApp נכשל בריסטרט אוטומטי. צריך התערבות ידנית." with title "🚨 WhatsApp Bot"' 2>/dev/null || true
push_ntfy "🚨 WhatsApp Bot נפל" "הבוט נכשל בריסטרט אוטומטי ב-$(date '+%H:%M'). צריך התערבות ידנית."
exit 1
