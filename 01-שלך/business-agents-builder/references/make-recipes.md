# בניית אוטומציות ב-Make דרך ה-MCP

נטען רק כשבונים אוטומציה (🤖) בשלב המיקרו. המטרה: לבנות תרחיש Make שרץ לבד, עם מינימום מאמץ מבעל העסק.

## חלוקת העבודה — מה Claude בונה, מה בעל העסק עושה

**Claude בונה דרך ה-MCP:**

1. מזהה את ה-team: `connections_list({teamId})` — אם לא יודעים teamId, שואלים את בעל העסק או משתמשים בכלי הרשימה של Make.
2. בונה את ה-blueprint (מבנה התרחיש: מודולים + חיבורים ביניהם).
3. מאמת: `validate_blueprint_schema({blueprint})` — מתקן עד שתקין.
4. יוצר: `scenarios_create({teamId, scheduling, blueprint})`.

**בעל העסק עושה ("3 לחיצות"):**

1. **מאשר חיבורים רגישים** — וואטסאפ/Twilio, CRM, Google Calendar/Gmail. אלה דורשים התחברות OAuth שרק הוא יכול לאשר ב-Make UI. Claude לא יכול ליצור חיבור OAuth בשמו — רק מפנה אותו: "היכנס ל-Make, לחץ Add connection ל-{שירות}, אשר."
2. **מדליק את התרחיש** — אחרי שהחיבורים מחוברים, מפעיל את ה-scenario (toggle ON).
3. **בודק הרצה ראשונה** — מריץ פעם אחת ידנית ורואה שהתוצאה נכונה.

⚠️ תמיד הסבר את 3 הצעדים בשפה פשוטה ובלי ז'רגון. בעל העסק לא מכיר "OAuth" — אמור "תחבר את חשבון הוואטסאפ שלך, זה כמו להתחבר לאפליקציה בפעם הראשונה".

## מבנה blueprint בסיסי (שלד לחיקוי)

blueprint הוא JSON שמתאר את זרימת התרחיש. מבנה עליון טיפוסי:

```json
{
  "name": "תזכורת לפני טיפול",
  "flow": [
    {
      "id": 1,
      "module": "google-calendar:watchEvents",
      "version": 1,
      "parameters": {},
      "mapper": {},
      "metadata": {}
    },
    {
      "id": 2,
      "module": "builtin:BasicFeeder",
      "version": 1,
      "parameters": {},
      "mapper": {}
    },
    {
      "id": 3,
      "module": "whatsapp:sendMessage",
      "version": 1,
      "parameters": {},
      "mapper": {
        "to": "{{1.attendee_phone}}",
        "text": "תזכורת: יש לך טיפול מחר ב-{{1.start}}"
      }
    }
  ],
  "metadata": { "version": 1 }
}
```

(שמות המודולים המדויקים — `app-modules_list({app})` נותן את הרשימה לכל אפליקציה. אם לא בטוח — בדוק שם לפני בנייה.)

## scheduling (איך התרחיש מופעל)

- **לפי לוח זמנים:** `{ "type": "indefinitely", "interval": 900 }` (כל 15 דקות) — לבדיקות מחזוריות (A3 גבייה, A6 דוח).
- **לפי אירוע/webhook:** התרחיש מופעל מטריגר (A2 ליד נכנס, A7 זימון).
- A1/A4/A5 — לרוב polling של היומן/הסטטוס במרווח קבוע.

## מיפוי מתכון → מודולים (התחלה)

- A1 תזכורת → google-calendar (trigger) + whatsapp/twilio (action)
- A2 ליד→CRM → webhook/gravity-forms (trigger) + google-sheets/CRM (action)
- A3 גבייה → google-sheets/CRM (trigger, filter overdue) + whatsapp (action) + docs (חשבונית)
- A4 ביקורת → CRM status (trigger) + delay + whatsapp/email (action)
- A5 onboarding → CRM "new" (trigger) + סדרת delay+message
- A6 דוח → schedule (trigger) + sheets aggregate + email
- A7 תיאום → booking webhook (trigger) + calendar create + email confirm
