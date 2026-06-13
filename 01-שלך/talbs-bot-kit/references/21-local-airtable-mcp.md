# 21 — התקנת Airtable MCP מקומי (קריטי ליציבות הבוט)

המטרה: לוודא שהבוט יכול לכתוב ולקרוא Airtable גם כשחיבור claude.ai של המשתתף "נופל".

## למה זה חשוב

הבוט מבוסס על Claude CLI (`claude -p`). כש-Claude צריך לעדכן Airtable, הוא משתמש ב-"MCP server" — צינור שמחבר אותו לשירותים חיצוניים.

**ברירת המחדל של Claude:** להשתמש ב-Airtable MCP שמתארח ב-claude.ai. הבעיה: ה-session של claude.ai לא יציב לאורך זמן בסביבות תזמון אוטומטי, וגם בצ'אט הוא נופל לפעמים. כשהוא נופל — הבוט מחזיר "Airtable MCP לא זמין" במקום לעדכן.

**הפתרון:** להתקין Airtable MCP server **שרץ מקומית על המחשב של המשתתף**, עם ה-PAT שלו. הוא לא תלוי בשום session חיצוני.

## דרישות מקדימות

המשתתף כבר השלים:

- ✅ קטגוריה 4 (CRM) — יש לו `AIRTABLE_PAT` ב-.env
- ✅ Claude Code מותקן (הוא משתמש בו עכשיו)

## ההתקנה — פקודה אחת

```bash
# קריאת ה-PAT מ-.env
PAT=$(grep "^AIRTABLE_PAT=" ~/whatsapp-bot/.env | cut -d= -f2)

# הוספת ה-MCP server לכלל המערכת (scope: user)
claude mcp add airtable --scope user --env "AIRTABLE_API_KEY=$PAT" -- npx -y airtable-mcp-server
```

**איפה זה נשמר:** קובץ ההגדרות של Claude — `~/.claude.json`.

## בדיקה שזה עובד

```bash
claude mcp list | grep airtable
```

תוצאה צפויה:

```
airtable: npx -y airtable-mcp-server - ✓ Connected
```

אם רואה `✗ Failed to connect` או שגיאת אימות — לוודא שה-PAT ב-.env לא כולל תגובות בסוף (`  # comment`) — `airtable-mcp-server` לוקח את כל הערך כפי שהוא, כולל רווחים.

## בדיקת end-to-end

אחרי ההתקנה, לוודא שהבוט עצמו יכול לעדכן Airtable דרך ה-MCP החדש:

```bash
echo "תכניס משימת בדיקה לטבלת 'משימות פתוחות' (tableId הוא [TABLE_TASKS_ID]) ב-base [AIRTABLE_BASE_ID]. השדות: 'משימה'='בדיקה - התקנת MCP', 'סטטוס'='פתוח'. אחרי שהוספת, אמור את ה-recordId שנוצר." | claude -p --permission-mode bypassPermissions
```

החליפי `[TABLE_TASKS_ID]` ו-`[AIRTABLE_BASE_ID]` בערכים מ-.env. אם רואה recordId חוזר — הכל עובד.

לאחר מכן — לבקש מהמשתתפת למחוק את משימת הבדיקה דרך ה-UI של Airtable, או דרך פקודה דומה.

## טיפים

- **אם ההתקנה לא עוברת** — לוודא ש-`npx` מותקן: `which npx`. אם לא — `brew install node` (במק) או דרך nvm.
- **הפעם הראשונה** — `npx -y airtable-mcp-server` יוריד את החבילה (~5MB). יתקין רק פעם אחת. השאר הוא רק טעינה מהירה.
- **עדכון ה-PAT** — אם המשתתפת מחליפה PAT (למשל פג תוקף), צריך להריץ:
  ```bash
  claude mcp remove airtable --scope user
  claude mcp add airtable --scope user --env "AIRTABLE_API_KEY=$NEW_PAT" -- npx -y airtable-mcp-server
  ```
- **למה לא להפעיל גם ב-Windows** — `claude mcp add` עובד אותו דבר. הפקודה זהה. רק `grep` ו-`cut` הם Unix; ב-PowerShell יהיה:
  ```powershell
  $PAT = (Select-String "^AIRTABLE_PAT=" $env:USERPROFILE\whatsapp-bot\.env).Line.Split("=")[1]
  claude mcp add airtable --scope user --env "AIRTABLE_API_KEY=$PAT" -- npx -y airtable-mcp-server
  ```

## רקע (למי שרוצה להבין יותר לעומק)

המקור: github.com/domdomegg/airtable-mcp-server (פתוח ומיינטיין מטעם הקהילה — חופשי, ללא עלות).
הוא רץ כתהליך לוקאלי כש-Claude צריך אותו, מתחבר ל-Airtable דרך ה-PAT, ומחזיר את התוצאה ל-Claude. ה-PAT אף פעם לא יוצא מהמחשב של המשתתף.
