# 12 — פריסה מקומית על Windows

המטרה: להפעיל את הבוט על PC עם Windows. הוא יישאר רץ כל זמן שה-PC דלוק.

## אזהרה חשובה לתת לה

```
⚠️ במסלול הזה — המחשב שלך חייב להיות דלוק 24/7 כדי שהבוט יעבוד.

זה אומר:
- אם את סוגרת/מכבה את המחשב — הבוט מפסיק לעבוד
- אם את בחו"ל — הבוט לא יענה
- חשבון החשמל יעלה (זניח, כ-20-40₪ לחודש)

אם זה לא מתאים — עבור למסלול ענן (Railway). $5 לחודש, תמיד פעיל.

ממשיכים עם Windows או עוברים?
```

## דרישות מקדימות

### Node.js

1. הורידי מ-https://nodejs.org/ (גרסה 20 LTS)
2. הרץ את ה-installer (הבא, הבא, סיום)
3. פתח PowerShell חדש ובדקי:
   ```powershell
   node --version
   ```

### Python 3

1. הורידי מ-https://www.python.org/downloads/ (גרסה 3.11+)
2. **חשוב:** בעת ההתקנה — סמני "Add Python to PATH"
3. בדוק:
   ```powershell
   python --version
   ```

### Git (אופציונלי, אבל מומלץ)

- https://git-scm.com/download/win

## שלבי הפריסה

### שלב 1: יצירת מבנה התיקייה

ב-PowerShell:

```powershell
mkdir $HOME\whatsapp-bot
cd $HOME\whatsapp-bot
```

זה ייצור תיקייה ב-`C:\Users\[שם]\whatsapp-bot`.

### שלב 2: העתקת קבצי הבוט מה-kit

```powershell
# בהנחה שה-kit ב-Downloads
copy [DOWNLOADS_PATH]\talbs-bot-kit\scripts\bot\* $HOME\whatsapp-bot\
copy [DOWNLOADS_PATH]\talbs-bot-kit\scripts\invoice\*.py $HOME\whatsapp-bot\
```

### שלב 3: התקנת dependencies

```powershell
cd $HOME\whatsapp-bot
npm install
```

### שלב 4: יצירת config.json ו-.env

כפי שיצרת בשלב 3 של ה-SKILL.

```powershell
ls $HOME\whatsapp-bot\
# צריך לראות: green-api-bot.js, package.json, config.json, .env
```

### שלב 5: בדיקת הרצה ראשונית

```powershell
cd $HOME\whatsapp-bot
node green-api-bot.js
```

אם רואים `🟢 starting poll loop` — הבוט עובד. Ctrl+C לעצירה.

### שלב 6: יצירת Task Scheduler לאוטו-start

Task Scheduler הוא ה-equivalent של launchd ב-Windows.

#### דרך PowerShell (מומלץ):

```powershell
$NodePath = (Get-Command node).Source
$BotPath = "$HOME\whatsapp-bot\green-api-bot.js"
$WorkDir = "$HOME\whatsapp-bot"

# יצירת Action
$Action = New-ScheduledTaskAction -Execute $NodePath -Argument "`"$BotPath`"" -WorkingDirectory $WorkDir

# יצירת Trigger — מיד בכניסה למשתמש + restart במקרה כשל
$Trigger = New-ScheduledTaskTrigger -AtLogon

# Settings: keep running, restart on failure
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 365)

# רישום ה-task
Register-ScheduledTask `
    -TaskName "WhatsAppBot" `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Description "Personal WhatsApp Bot — runs at user logon"

# הפעלה מיידית
Start-ScheduledTask -TaskName "WhatsAppBot"
```

#### דרך Task Scheduler GUI (אלטרנטיבה ידידותית יותר):

1. פתח "Task Scheduler" (חפשי בתפריט Start)
2. Create Task...
3. **General tab:**
   - Name: WhatsAppBot
   - Run only when user is logged on
   - Configure for: Windows 11
4. **Triggers tab:**
   - New → At log on → OK
5. **Actions tab:**
   - New → Program/script: `C:\Program Files\nodejs\node.exe`
   - Add arguments: `"%USERPROFILE%\whatsapp-bot\green-api-bot.js"`
   - Start in: `%USERPROFILE%\whatsapp-bot`
6. **Settings tab:**
   - If the task fails, restart every: 1 minute
   - Attempt to restart up to: 999 times
   - Stop the task if it runs longer than: (unchecked)
7. OK + הזן סיסמת windows

### שלב 7: מניעת מצב Sleep למחשב

Windows יודע לכבות את עצמו אחרי זמן. צריך לוודא שלא:

1. Settings → System → Power & battery
2. **Screen and sleep:**
   - When plugged in, turn off my screen after: **Never** (או 30 דקות, אם זה מטריד)
   - When plugged in, put my device to sleep after: **Never**
3. **Power mode:** Best performance

או דרך PowerShell:

```powershell
powercfg /change standby-timeout-ac 0
powercfg /change hibernate-timeout-ac 0
```

### שלב 8: אוטומציות יומיות (אם בחר)

אם בחר אגנדת בוקר/סיכום ערב — צור Task Scheduler נוסף עם Trigger מסוג "At a specific time":

```powershell
$Trigger = New-ScheduledTaskTrigger -Daily -At "08:00"
$Action = New-ScheduledTaskAction -Execute "bash" -Argument "$HOME\whatsapp-bot\morning-agenda.sh --auto"
# ... וכו'
```

> ⚠️ Bash על Windows: צריך WSL או Git Bash. אם אין — הסקריפטים shell צריכים להיות מותאמים ל-PowerShell. **זה גורם של מורכבות.** אם המשתתף לא טכני — מומלץ ענן.

### שלב 9: וידוא ש-task רץ

```powershell
Get-ScheduledTask -TaskName "WhatsAppBot"
```

צריך לראות State = Running.

### שלב 10: בדיקת חיבור WhatsApp (QR scan)

זהה לשלבי הענן.

---

## פלט הפריסה

```
✅ מבנה תיקייה: %USERPROFILE%\whatsapp-bot\
✅ Dependencies: installed
✅ Config + .env: loaded
✅ Process: running
✅ Task Scheduler: WhatsAppBot active
✅ Sleep disabled
✅ Green API: authorized
✅ Local Airtable MCP: connected
```

> ⚠️ **שלב חיוני אחרי הפריסה — אל לדלג.** התקנת Airtable MCP מקומי. ראה `21-local-airtable-mcp.md`. ב-PowerShell:
>
> ```powershell
> $PAT = (Select-String "^AIRTABLE_PAT=" $env:USERPROFILE\whatsapp-bot\.env).Line.Split("=")[1]
> claude mcp add airtable --scope user --env "AIRTABLE_API_KEY=$PAT" -- npx -y airtable-mcp-server
> claude mcp list | Select-String airtable  # ✓ Connected
> ```

---

## טיפים

- **WSL (Windows Subsystem for Linux)** — אם הוא טכנית יותר, WSL הופך את הכל הרבה יותר פשוט. אפשר להריץ את הסקריפטים shell כמו ב-Mac.
- **Antivirus** — לפעמים חוסם את הרשת. אם הבוט לא יכול להתחבר ל-Green API — בדוק את ה-Firewall.
- **Windows Updates** — מאלצים restart. אחרי restart הבוט יעלה אוטומטית (Task Scheduler).
- **אם משהו לא עובד** — Event Viewer → Windows Logs → Application

---

## אם זה מורכב מדי

**הצע לעבור לענן.** מסלול Windows מקומי הוא הכי מורכב מהשלושה (Mac, Windows, Railway). אם המשתתף לא טכני מאוד — Railway חוסך הרבה כאב ראש.
