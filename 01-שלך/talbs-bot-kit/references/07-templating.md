# 07 — Templating: יצירת קבצי ההגדרה האישיים

המטרה: לקחת את כל המשתנים שאספת ב-6 הקטגוריות, לטעון את התבניות מ-`templates/`, ולהחליף את ה-placeholders.

## רשימת ה-placeholders

הקבצים בתבניות משתמשים ב-format `{{PLACEHOLDER_NAME}}`. הנה הרשימה המלאה והמקור של כל אחד:

### מקטגוריה 0 (Preflight)

| Placeholder                | מקור                | דוגמה                         |
| -------------------------- | ------------------- | ----------------------------- |
| `{{USER_NAME}}`            | שמה                 | "שרה כהן"                     |
| `{{OS}}`                   | מערכת הפעלה         | "Mac" / "Windows" / "Cloud"   |
| `{{USER_WHATSAPP_NUMBER}}` | מספר WhatsApp ללא + | "972501234567"                |
| `{{USER_WHATSAPP_JID}}`    | JID מלא             | "972501234567@s.whatsapp.net" |

### מקטגוריה 1 (Business)

| Placeholder           | מקור              |
| --------------------- | ----------------- |
| `{{BOT_NAME}}`        | שם הבוט           |
| `{{BUSINESS_DOMAIN}}` | תחום העסק         |
| `{{AUDIENCE}}`        | תיאור הקהל        |
| `{{CORE_PROMISE}}`    | ההבטחה במשפט      |
| `{{HARD_RULES_CAT1}}` | חוקים מהקטגוריה 1 |

### מקטגוריה 2 (Connections)

| Placeholder                 | מקור               |
| --------------------------- | ------------------ |
| `{{GREEN_API_INSTANCE_ID}}` | Green API instance |
| `{{GREEN_API_TOKEN}}`       | Green API token    |
| `{{ANTHROPIC_API_KEY}}`     | Claude API key     |
| `{{AIRTABLE_EMAIL}}`        | מייל Airtable      |

### מקטגוריה 3 (Invoices)

| Placeholder                   | מקור            | אם HAS_INVOICES=false |
| ----------------------------- | --------------- | --------------------- |
| `{{HAS_INVOICES}}`            | true/false      | false                 |
| `{{PREFIX_QUOTE}}`            | "5"             | ""                    |
| `{{PREFIX_ORDER}}`            | "9"             | ""                    |
| `{{PREFIX_TAX_RECEIPT}}`      | "6"             | ""                    |
| `{{PREFIX_RECEIPT}}`          | "8"             | ""                    |
| `{{GREENINVOICE_API_KEY}}`    | מ-Green Invoice | ""                    |
| `{{GREENINVOICE_API_SECRET}}` | מ-Green Invoice | ""                    |

### מקטגוריה 4 (CRM)

| Placeholder                 | מקור                          |
| --------------------------- | ----------------------------- |
| `{{AIRTABLE_BASE_ID}}`      | ה-Base ID                     |
| `{{AIRTABLE_API_KEY}}`      | Airtable token                |
| `{{TABLE_LEADS_ID}}`        | tblXXX של לידים               |
| `{{TABLE_TASKS_ID}}`        | tblXXX של משימות              |
| `{{TABLE_TRANSACTIONS_ID}}` | tblXXX של עסקאות (אם רלוונטי) |

### מקטגוריה 5 (Automations)

| Placeholder               | מקור       |
| ------------------------- | ---------- |
| `{{WANT_MORNING_AGENDA}}` | true/false |
| `{{MORNING_AGENDA_HOUR}}` | "08:00"    |
| `{{WANT_DAILY_SUMMARY}}`  | true/false |
| `{{DAILY_SUMMARY_HOUR}}`  | "20:00"    |

### מקטגוריה 6 (System Prompt)

| Placeholder               | מקור                          |
| ------------------------- | ----------------------------- |
| `{{BOT_TONE}}`            | "חברי וקליל"                  |
| `{{BOT_RESPONSE_LENGTH}}` | "בינוניות"                    |
| `{{KEY_PEOPLE_LIST}}`     | טקסט מובנה מ-KEY_PEOPLE       |
| `{{EXTRA_HARD_RULES}}`    | טקסט מובנה מ-EXTRA_HARD_RULES |

### נוספים — מחושבים אוטומטית

| Placeholder          | מקור                                                 |
| -------------------- | ---------------------------------------------------- |
| `{{NTFY_TOPIC}}`     | רנדומלי: "tal-bot-" + 8 hex chars (לכל לקוח ייחודי) |
| `{{INSTALLED_DATE}}` | תאריך היום (YYYY-MM-DD)                              |

---

## 🎉 הסקריפטים אינם דורשים sed/החלפה ידנית

ב-V1 של הקיט, הסקריפטים `green-api-bot.js` ושלושת ה-shell scripts (`morning-agenda.sh`, `daily-summary.sh`, `health-check.sh`) **קוראים את כל הפרטים האישיים מ-`.env`** בעת ההפעלה. זה אומר:

- ✅ אותו קוד עובד אצל כל לקוח
- ✅ אין צורך לבצע sed/replacement על הסקריפטים
- ✅ עדכון לקוד (בעתיד) = החלפת קבצים בלבד, .env נשאר כמו שהוא

**הקובץ היחיד שכן דורש החלפת placeholders זה `.env` עצמו** (וזה ה-`templates/env.template`).

עבור `config.json`, דרושה גם החלפה — בעיקר של ה-`systemPromptAppend`.

## תהליך ההחלפה (2 קבצים)

עבור על 2 הקבצים האלה לפי הסדר:

### 1. `.env`

קרא את `templates/env.template`, החליפי את כל ה-placeholders, וכתבי ל:

- **Mac/Linux:** `~/whatsapp-bot/.env` (או הנתיב שבחרה)
- **Windows:** `C:\Users\[שם]\whatsapp-bot\.env`
- **Railway:** לא קובץ — Environment Variables ב-Railway dashboard

### 2. `config.json` (הקובץ של הבוט עצמו, לא של הסקריפטים)

קרא את `templates/config.template.json`, החליפי את ה-placeholders.

**שני placeholders מיוחדים שדורשים בנייה:**

**`{{SYSTEM_PROMPT_APPEND}}`** — זה ה-system prompt המלא. לבנות אותו:

1. קחי את `templates/system-prompt.template.md`
2. החליפי בו את ה-placeholders
3. הכניסי את כל הטקסט כ-string ל-`systemPromptAppend` (זכרי escape של `"` ל-`\"` ושל `\n` ל-`\\n`)

**`{{WHITELIST}}`** — מערך JSON עם המספר שלו:

```json
"whitelist": ["{{USER_WHATSAPP_NUMBER}}"]
```

כתבי ל-`~/whatsapp-bot/config.json`.

### 3. Verification — אימות

לפני שמסיימים את שלב היצירה, אמת 2 דברים:

1. **שה-JSON של config.json תקין:**

   ```bash
   python3 -c "import json; json.load(open('~/whatsapp-bot/config.json')); print('OK')"
   ```

2. **שאין placeholder שלא הוחלף:**
   ```bash
   grep -E "\{\{[A-Z_]+\}\}" ~/whatsapp-bot/config.json ~/whatsapp-bot/.env
   ```
   אם יש output — יש placeholder שלא הוחלף. תקני לפני שממשיכים.

---

## טיפים

- **שמירת התשובות שלו:** אם את ב-Claude Code, אתה יכול לשמור את כל המשתנים כקובץ ביניים `~/whatsapp-bot/.install-state.json`. זה יעזור אם משהו נשבר באמצע ההתקנה.
- **placeholder ריק:** אם המשתתף בחר שאין חשבוניות (HAS_INVOICES=false), חלק מה-placeholders יישארו ריקים. זה בסדר — בתבנית יש לוגיקה לדלג עליהם.
- **escape לעברית ב-JSON:** עברית עובד ב-JSON בלי escape מיוחד. אבל אם יש גרשיים כפולות בטקסט (`"`) — חייבים escape ל-`\"`.

---

## אחרי שסיימת

יש 3 קבצים אישיים מוכנים:

- `.env` עם כל ה-API keys
- `config.json` עם ה-system prompt המלא
- (אם בענן: זה נכנס ל-Railway environment variables, לא לקובץ)

עוברים לשלב 4: פריסה — לפי המסלול שבחרה.
