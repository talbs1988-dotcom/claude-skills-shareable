# 11 — פריסה מקומית על Mac

המטרה: להפעיל את הבוט על המק של המשתתף. הוא יישאר רץ כל זמן שהמק דלוק.

## אזהרה חשובה לתת לה

```
⚠️ במסלול הזה — המק שלך חייב להיות דלוק 24/7 כדי שהבוט יעבוד.

זה אומר:
- אם את סוגרת את המחשב בלילה — הבוט מפסיק לעבוד
- אם את בחו"ל — הבוט לא יענה
- חשבון החשמל יעלה קצת (זניח, כ-15-30₪ לחודש)

אם זה לא מתאים לך — עבור למסלול ענן (Railway).
זה $5 לחודש והבוט תמיד פעיל.

ממשיכים עם מק או עוברים?
```

אם בחר להמשיך עם מק — ממשיכים.

## דרישות מקדימות

```bash
# בדיקה שיש Node.js (חובה גרסה 20+)
node --version
# אם לא — התקנה דרך nvm:
curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.5/install.sh | bash
nvm install 20
```

```bash
# בדיקה שיש Python 3 (לסקריפטים של חשבונית ירוקה)
python3 --version
# אם לא — התקנה דרך Homebrew:
brew install python3
```

```bash
# בדיקה שיש jq (לעיבוד JSON ב-shell scripts)
jq --version
# אם לא:
brew install jq
```

## שלבי הפריסה

### שלב 1: יצירת מבנה התיקייה

```bash
mkdir -p ~/whatsapp-bot
cd ~/whatsapp-bot
```

### שלב 2: העתקת קבצי הבוט מה-kit

מ-`scripts/bot/`:

```bash
cp [SKILL_PATH]/scripts/bot/green-api-bot.js ~/whatsapp-bot/
cp [SKILL_PATH]/scripts/bot/package.json ~/whatsapp-bot/
```

מ-`scripts/invoice/` (אם HAS_INVOICES=true):

```bash
cp [SKILL_PATH]/scripts/invoice/*.py ~/whatsapp-bot/
```

מ-`scripts/automations/` (לפי בחירות הקטגוריה 5):

```bash
# פייתון: morning_agenda.py / daily_summary.py / _helpers.py / _gcal.py / _airtable.py
cp [SKILL_PATH]/scripts/automations/*.py ~/whatsapp-bot/
# Bash: health-check.sh (מנטר שהבוט חי)
cp [SKILL_PATH]/scripts/automations/health-check.sh ~/whatsapp-bot/
cp [SKILL_PATH]/scripts/automations/requirements.txt ~/whatsapp-bot/
chmod +x ~/whatsapp-bot/*.sh
```

### שלב 3: התקנת dependencies

```bash
cd ~/whatsapp-bot
npm install

# Python libraries for the scheduled automations (5 שניות, חינם)
pip3 install --user -r requirements.txt
```

### שלב 4: יצירת config.json ו-.env

כפי שיצרת בשלב 3 של ה-SKILL (templating).

```bash
# בדיקה שהכל קיים
ls -la ~/whatsapp-bot/
# צריך לראות: green-api-bot.js, package.json, config.json, .env
```

### שלב 5: הרצה ראשונית לבדיקה

```bash
cd ~/whatsapp-bot
node green-api-bot.js
```

אם רואים `🟢 starting poll loop` — הבוט עובד. הקישי `Ctrl+C` לעצירה.

אם רואים שגיאה כמו `missing GREEN_API_INSTANCE_ID` — `.env` לא נטען נכון. בדוק שהוא ב-`~/whatsapp-bot/.env`.

### שלב 6: יצירת LaunchAgent (אוטו-start)

צור קובץ plist שירוץ אוטומטית בעת התחלת המק:

```bash
USER_NAME=$(whoami)
NODE_PATH=$(which node)

cat > ~/Library/LaunchAgents/com.${USER_NAME}.green-api-bot.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.${USER_NAME}.green-api-bot</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/caffeinate</string>
        <string>-ims</string>
        <string>${NODE_PATH}</string>
        <string>/Users/${USER_NAME}/whatsapp-bot/green-api-bot.js</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/Users/${USER_NAME}/whatsapp-bot</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/${USER_NAME}/whatsapp-bot/green-api-bot.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/${USER_NAME}/whatsapp-bot/green-api-bot.log</string>
    <key>EnvironmentVariables</key>
    <dict>
        <key>PATH</key>
        <string>/usr/local/bin:/usr/bin:/bin:/opt/homebrew/bin</string>
        <key>PORT</key>
        <string>7654</string>
    </dict>
</dict>
</plist>
EOF
```

טעני אותו:

```bash
launchctl load ~/Library/LaunchAgents/com.${USER_NAME}.green-api-bot.plist
```

ה-`caffeinate -ims` מונע מהמק להירדם והבוט יישאר רץ.

### שלב 7: הגדרת אוטומציות יומיות (אם בחר)

אם בחר אגנדת בוקר בקטגוריה 5:

```bash
# יוצרת LaunchAgent לתזמון
cat > ~/Library/LaunchAgents/com.${USER_NAME}.morning-agenda.plist << EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.${USER_NAME}.morning-agenda</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/Users/${USER_NAME}/whatsapp-bot/morning_agenda.py</string>
        <string>--auto</string>
    </array>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>[MORNING_AGENDA_HOUR_NUMBER]</integer>
        <key>Minute</key>
        <integer>[MORNING_AGENDA_HOUR_MINUTE]</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/Users/${USER_NAME}/whatsapp-bot/morning-agenda.log</string>
</dict>
</plist>
EOF

launchctl load ~/Library/LaunchAgents/com.${USER_NAME}.morning-agenda.plist
```

החליפי `[MORNING_AGENDA_HOUR_NUMBER]` ל-8 (אם השעה 08:00) ו-`[MORNING_AGENDA_HOUR_MINUTE]` ל-0.

עשי דבר דומה לסיכום ערב (`daily-summary`) ולhealth check אם רוצים.

### שלב 8: וידוא ש-launchd רץ

```bash
launchctl list | grep ${USER_NAME}
```

צריך לראות את כל ה-launchd jobs שיצרת.

### שלב 9: בדיקת חיבור WhatsApp (QR scan)

זהה לשלב 4 ב-`10-deploy-railway.md`.

### שלב 10: התקנת Airtable MCP מקומי (קריטי ליציבות הבוט)

⚠️ **שלב חיוני — אל לדלג עליו.** בלעדיו הבוט יחוויה בעיות תקופתיות עם Airtable.

עקוב אחרי ההוראות ב-`21-local-airtable-mcp.md`. זה פקודה אחת:

```bash
PAT=$(grep "^AIRTABLE_PAT=" ~/whatsapp-bot/.env | cut -d= -f2)
claude mcp add airtable --scope user --env "AIRTABLE_API_KEY=$PAT" -- npx -y airtable-mcp-server
claude mcp list | grep airtable  # ✓ Connected
```

---

## פלט הפריסה

```
✅ מבנה תיקייה: ~/whatsapp-bot/
✅ Dependencies: installed
✅ Config + .env: loaded
✅ Process: running (PID: XXXX)
✅ LaunchAgents: loaded
✅ Green API: authorized
✅ Local Airtable MCP: connected
```

עוברים לשלב 5 (אימות): `20-verification.md`.

---

## טיפים

- **caffeinate** מונע מהמק להירדם. אם הוא עדיין רוצה לחסוך חשמל — אפשר לאפשר sleep למסך בלבד (System Preferences → Energy Saver → "Turn display off after").
- **Mac דלוק 24/7 — סביר?** רוב המקים יכולים להיות דלוקים שנים. הסיכון העיקרי: עודף חום, בעיות אוורור.
- **אם המק מתאתחל אחרי עדכון** — launchd יעלה את הבוט אוטומטית כי `KeepAlive` ו-`RunAtLoad` מוגדרים.
- **אם משהו לא עובד** — `tail -f ~/whatsapp-bot/green-api-bot.log` יראה לוגים בזמן אמת.
