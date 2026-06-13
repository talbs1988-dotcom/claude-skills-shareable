# 22 — התקנת Google Calendar MCP מקומי (לכתיבה ביומן מתוך הבוט)

המטרה: לאפשר לבוט ליצור/לעדכן/למחוק פגישות ביומן Google Calendar של המשתתפת — במצב שיציב, בלי תלות בחיבור claude.ai שלה.

## למה זה חשוב

הבוט קורא יומן גם דרך iCal (כפי שתיארנו ב-`05-automations.md`) — אבל iCal הוא **קריאה בלבד**. כשהמשתתפת תאמר לבוט "תוסיף לי פגישה ב-3" — דרושה כתיבה. לכתיבה צריך OAuth + MCP server שתומך בכך.

באותו זמן, ה-Calendar MCP של claude.ai לא יציב — נופל מדי פעם ומותיר את הבוט תקוע ("Google Calendar לא זמין"). הפתרון: לרוץ סרבר Calendar MCP מקומית עם OAuth של המשתתפת.

## דרישות מקדימות

המשתתפת צריכה:

- חשבון Google רגיל (Gmail)
- כ-15-20 דקות (זה השלב הארוך ביותר בהתקנת הבוט)
- Node.js מותקן (כבר התקנו לבוט)

## חלק א' — Google Cloud Console (10-15 דקות, המשתתפת)

### א.1 יצירת פרויקט

1. פתח: https://console.cloud.google.com/projectcreate
2. **Project name:** `MyBot` (או כל שם)
3. Location: No organization
4. לחץ CREATE
5. אחרי שנוצר — בחר אותו בסרגל העליון

### א.2 הפעלת Calendar API

1. פתח: https://console.cloud.google.com/apis/library/calendar-json.googleapis.com
2. ודא שהפרויקט שלך נבחר למעלה
3. לחץ **ENABLE**

### א.3 OAuth Consent Screen

1. פתח: https://console.cloud.google.com/auth/overview
2. App name: `MyBot`, User support email: המייל שלך
3. Audience type: **External**
4. Developer contact email: המייל שלך
5. לחץ **CREATE**
6. בתפריט שמאל → **Audience** → גלוס למטה ל-"Test users" → **+ Add users** → הוסף את המייל שלך → Save

### א.4 יצירת OAuth Client ID

1. בתפריט שמאל → **Clients** → **+ Create Client**
2. **Application type: Desktop app** ⚠️ חשוב!
3. Name: `MyBot Desktop`
4. **CREATE**
5. בפופאפ שיופיע — לחץ **"Download JSON"**
6. הקובץ ירד ל-Downloads עם שם `client_secret_XXXX...json`

## חלק ב' — התקנת ה-MCP (5 דקות, סקריפט)

```bash
# העברת קובץ ה-credentials למקום קבוע
mkdir -p ~/.config/google-calendar-mcp
NEWEST=$(ls -t ~/Downloads/client_secret_*.json | head -1)
cp "$NEWEST" ~/.config/google-calendar-mcp/gcp-oauth.keys.json
chmod 600 ~/.config/google-calendar-mcp/gcp-oauth.keys.json

# התקנת ה-MCP server
claude mcp add google-calendar --scope user \
  --env "GOOGLE_OAUTH_CREDENTIALS=$HOME/.config/google-calendar-mcp/gcp-oauth.keys.json" \
  -- npx -y @cocal/google-calendar-mcp

# הפעלת ה-auth flow — יפתח דפדפן לאישור
export GOOGLE_OAUTH_CREDENTIALS=~/.config/google-calendar-mcp/gcp-oauth.keys.json
npx -y @cocal/google-calendar-mcp auth
```

הסקריפט יפתח לך דפדפן. תופיע אזהרה **"Google לא אימתה את האפליקציה הזו"** — זה תקין כי האפליקציה במצב Testing. **לחץ על "המשך"** (קישור כחול קטן, לא "חזרה למצב בטוח"). אחר כך תאשר את ההרשאות ולחץ **Allow**.

כשרואים בקונסול: `Tokens saved successfully! Authentication completed!` — סיימת.

## חלק ג' — בדיקה

```bash
claude mcp list | grep google-calendar  # ✓ Connected
```

ובדיקה חיה דרך הבוט:

```bash
echo "תקרא לי את 3 הפגישות הקרובות שלי ביומן Google Calendar" | claude -p --permission-mode bypassPermissions
```

צריך לקבל רשימה אמיתית של פגישות.

## טיפים ופתרון בעיות

- **טוקנים פגי תוקף אחרי שבוע** — במצב Testing, ה-OAuth tokens פגים כל ~7 ימים. כשזה קורה — הבוט יאמר "Google Calendar needs re-authentication". פתרון: להריץ שוב `npx -y @cocal/google-calendar-mcp auth`. (במעבר ל-Production — Google דורש בדיקת אבטחה של ~3-4 שבועות. למסלול הסדנה — Testing מספיק).
- **אם הדפדפן לא נפתח** — הסקריפט מדפיס URL בקונסול. תפתח אותו ידנית.
- **אם השגיאה היא "Access denied"** — לוודא שהוספת את עצמך כ-Test user (שלב א.3).
- **קובץ ה-tokens נשמר ב-** `~/.config/google-calendar-mcp/tokens.json`. אם בעיות — מחיקה והרצה מחודשת של `auth`.

## רקע

המקור: github.com/nspady/google-calendar-mcp (קוד פתוח, חופשי).
הסרבר רץ כתהליך מקומי כש-Claude קורא לו. ה-tokens נשמרים מקומית בלבד.
