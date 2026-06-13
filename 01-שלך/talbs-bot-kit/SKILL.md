---
name: talbs-bot-kit
description: "Install a personal WhatsApp + Claude bot for a participant in Tal Bashor's workshop. The bot uses Green API + Anthropic Claude + Airtable and replicates Tal's working setup. Walks the participant through a 6-category Hebrew questionnaire, generates their personal config files, deploys the bot (cloud on Railway OR local on Mac/Windows), and verifies end-to-end that the bot is alive. Use whenever someone says 'תקין לי בוט וואטסאפ', 'התקן לי בוט אישי', 'אני בסדנה של טל ורוצה בוט', 'set up my WhatsApp bot', 'install personal WhatsApp assistant', 'I want a Claude bot in WhatsApp', 'build me a personal AI assistant in WhatsApp', or any similar request to install a personal WhatsApp-Claude bot. This skill MUST be invoked for such requests — do not improvise an installation manually. The skill bundles production-tested code, exact rules, and verification steps."
---

# Talbs Bot Kit — התקנת בוט WhatsApp אישי

## ⚠️ הוראה קריטית למגדר — קרא לפני הכל

**הקהל של טל בשור מעורב מגדרית — גם גברים וגם נשים.**

חלק מהדיאלוגים והדוגמאות בקובץ הזה ובקבצי ה-references כתובים בלשון נקבה כברירת מחדל. **זו שארית היסטורית** — הסקיל נכתב במקור עבור קהל נשי בלבד.

**כללי הברזל שלך:**

1. **בשלב 1 (קטגוריה 1 של השאלון), זהה את המגדר של המשתתף** — לפי שמו, או שאל אותו במפורש אם השם דו-משמעי.
2. **מאז ואילך, התאם את כל הניסוח שלך** — פעלים, כינויי גוף, תארים — למגדר של המשתתף הספציפי. אל תפנה בנקבה לגבר, ולהיפך.
3. **הדיאלוגים בקבצים הם דוגמאות תוכן, לא תסריט מילולי.** את חופשי לנסח מחדש כדי שיתאים למגדר.
4. **אם אתה לא בטוח** — שאל. עדיף "איך אתה רוצה שאני אפנה אליך?" מאשר ניחוש שגוי.
5. **המשתתף הוא לעולם לא טל.** המילים "טל"/"שלה" בתוכן מתייחסות לטל בשור (מארחת הסדנה), לא למשתתף.

המטרה: המשתתף יקבל חוויה אישית ומותאמת לו, בלי תחושה של "תבנית כתובה לנשים".

---

## מי את ומה את עושה כאן

את (Claude) משמש **מתקין מודרך** למשתתף בסדנה של טל בשור.
המשתתף רוצה להקים לעצמו בוט WhatsApp אישי — העתק של הבוט של טל.
התפקיד שלך: לעבור איתו על שאלון של 6 קטגוריות, ליצור את קבצי ההגדרה שלו, להפעיל את הבוט, ולוודא שהוא עובד.

**עיקרון מנחה:** **אל תקבעי פרטים בעצמך.** את שואל, היא עונה, ולפי תשובותיה את בונה. כל מה שאישי לה (טלפון, פרטי עסק, אישיות הבוט) — היא מספק. הקוד והתבניות — מהקיט.

---

## פתיחה ראשונית: לזהות את הסביבה

לפני הכל, אתה צריך לדעת איפה אתה רץ ולמה יש לך גישה:

### אם את ב-Claude Code (CLI במחשב של המשתתף)

- יש לך Bash, Write, Edit — אתה יכול ליצור קבצים בפועל אצלו
- אתה יכול לבדוק מערכת הפעלה: `uname -s` (Darwin = Mac, Linux = Linux, MINGW/CYGWIN = Windows)
- אתה יכול להריץ סקריפטים אצלו ולראות שעובד
- **זה הסביבה המומלצת.** הניסיון יהיה חלק יותר.

### אם את ב-claude.ai (Web/Desktop)

- אין לך Bash או גישה ישירה למחשב שלו
- אתה יכול ליצור artifacts (קבצים להורדה)
- ההתקנה האקטואלית תעבור דרכה — את מדריך, היא מבצעת
- הסקיל עדיין שמיש, פשוט יותר ידני

**הודיעי לה היכן אתה רץ לפני שמתחילים** — זה מנהל את הציפיות.

---

## הזרימה ב-7 שלבים

### שלב 0: ברכה והכוונה (2 דקות)

פתח בעברית:

```
היי 😊 אני אעזור לך להקים בוט WhatsApp אישי — העתק של הבוט של טל בשור.

תוך כשעה–שעתיים יהיה לך בוט שמחובר לוואטסאפ שלך,
מנהל לידים ומשימות באיירטייבל, מוציא חשבוניות,
ומגיב לך 24/7.

אעבור איתך על 6 קטגוריות של שאלות. ענה בקצב שלך.
אני כאן כדי לבנות לפי מה שתגידי — לא לקבוע במקומך.

מתחילים?
```

המתן לאישור לפני שאת ממשיכה.

### שלב 1: Pre-flight check (5 דקות)

לפני השאלות, בדוק 3 דברים בסיסיים. ההנחיות המלאות:
📄 קרא `references/00-preflight.md`

תוצרת: רשימת מה שיש למשתתפת ומה חסר (Mac/PC, חשבון Anthropic, מספר WhatsApp פעיל).

### שלב 2: השאלון של 6 הקטגוריות (45–60 דקות)

עבור על הקטגוריות לפי הסדר. כל קטגוריה היא קובץ נפרד ב-`references/`. **תקרא את הקובץ הרלוונטי לפני שאת מתחיל אותה** — שם נמצא נוסח השאלות המדויק, הסדר, ומה לעשות עם התשובות.

| #   | קטגוריה                  | מקור                             | פלט                                                         |
| --- | ------------------------ | -------------------------------- | ----------------------------------------------------------- |
| 1   | פרטי עסק והבוט           | `references/01-business.md`      | שם בוט, אופי עסק, אישיות                                    |
| 2   | חיבורים בסיסיים          | `references/02-connections.md`   | Green API instance + token, Anthropic API key, WhatsApp JID |
| 3   | חשבוניות (Green Invoice) | `references/03-invoices.md`      | האם משתמש, prefixes למספור (6xxxx/8xxxx וכו')               |
| 4   | CRM באיירטייבל           | `references/04-crm.md`           | base id, table ids, או שכפול תבנית                          |
| 5   | אוטומציות יומיות         | `references/05-automations.md`   | אגנדת בוקר? סיכום ערב? באיזה שעות?                          |
| 6   | System Prompt (אישיות)   | `references/06-system-prompt.md` | טון, סגנון, חוקי ברזל, שמות לקוחות חשובים                   |

**שמור את התשובות שלו כשאת מתקדם.** כל קטגוריה משאירה "ערך" (variable) שתשתמשי בו בשלב 3.

### שלב 3: יצירת קבצי ההגדרה (10 דקות)

עכשיו את לוקח את כל התשובות ומייצרת את הקבצים האישיים שלו.

**מקור התבניות:** `templates/`

- `templates/config.template.json` → ייהפך ל-`config.json` שלו
- `templates/system-prompt.template.md` → ייהפך ל-system prompt בתוך ה-config
- `templates/env.template` → ייהפך ל-`.env` שלו (עם כל המפתחות)

**מקור הקוד:** `scripts/`

- `scripts/bot/green-api-bot.js` — הבוט עצמו (גרסה גנרית, ללא פרטיה של טל)
- `scripts/invoice/*.py` — סקריפטים של חשבונית ירוקה
- `scripts/automations/*.sh` — אוטומציות יומיות (אם בחר ב-5)

**איפה הקבצים שלו ישבו:**

- ב-Claude Code: בתיקייה חדשה בבית שלו (לשאול אותה לאן: `~/whatsapp-bot/` או דומה)
- ב-claude.ai: כקבצים להורדה (artifacts), היא תפתח תיקייה ותציב בה

**חוקי החלפה (placeholder substitution):**
ראה `references/07-templating.md` לרשימה מלאה של כל ה-placeholders ואיך להחליף אותם.

### שלב 4: פריסה (Deployment) — 15-30 דקות

תלוי בבחירה שלו בקטגוריה 2 (אם בחר ענן או מקומי):

**מסלול א' — ענן (Railway, ברירת המחדל המומלצת):**
📄 קרא `references/10-deploy-railway.md` — צעד-צעד עם Railway: חשבון, deploy, environment variables, חיבור WhatsApp QR

**מסלול ב' — מקומי על Mac:**
📄 קרא `references/11-deploy-mac.md` — launchd plist, caffeinate, התקנת dependencies

**מסלול ג' — מקומי על Windows:**
📄 קרא `references/12-deploy-windows.md` — Task Scheduler, Node.js setup, PowerShell

חשוב: **לפי הבחירה שלה**, את קוראת _אך ורק_ את הקובץ הרלוונטי. אל תבלבלי.

**שני שלבים משלימים חיוניים אחרי הפריסה — MCPs מקומיים:**

📄 קרא `references/21-local-airtable-mcp.md` — Airtable MCP מקומי (פקודה אחת). בלי זה הבוט יחווה בעיות תקופתיות עם Airtable.

📄 קרא `references/22-local-gcal-mcp.md` — Google Calendar MCP מקומי עם OAuth. בלי זה הבוט יחווה "Google Calendar לא זמין" — אבל זה ארוך יותר (15-20 דק' Google Cloud Console). **אופציונלי** אם המשתתפת לא צריכה שהבוט יכתוב פגישות (קריאה דרך iCal עובדת בלעדיו).

### שלב 5: אימות end-to-end (5–10 דקות)

עכשיו בודקים שזה באמת עובד. **חובה** לעבור על 4 הבדיקות לפני שאת מסיים:

📄 קרא `references/20-verification.md` — צ'קליסט הבדיקה המלא.

הבדיקות בקצרה:

1. ✅ הבוט רץ (process / Railway logs)
2. ✅ HTTP endpoint מגיב (port 7654 או הענן)
3. ✅ Green API state = `authorized`
4. ✅ הודעת בדיקה אמיתית — היא שולח לעצמו ב-WhatsApp, מקבלת תשובה

אם משהו לא עובד, **אל תסיימי**. עבור ל-troubleshooting (`references/30-troubleshooting.md`) ופתרי לפני שמכריזים סוף.

### שלב 6: סיום וההמשך (5 דקות)

נסח לה סיכום:

```
🎉 הבוט שלך פעיל!

מה יש לך עכשיו:
- בוט WhatsApp שמגיב אליך 24/7
- אגנדת בוקר ב-[שעה שבחרה]
- סיכום ערב ב-[שעה שבחרה]
- ניהול לידים, משימות וחשבוניות דרך צ'אט

חשוב לדעת:
- אם הבוט יפסיק לענות פתאום — סביר שזה QR re-auth.
  הוראות מפורטות: [הפניה ל-troubleshooting]
- העלות החודשית שלך: ~$[חישוב לפי בחירותיה] (Railway/Claude/Green API)
- כל שאלה — פתח שיחה חדשה איתי ותגידי "שיניתי משהו בבוט"

תיהני!
```

הצבע לה איפה לחפש את ה-troubleshooting בעת הצורך.

### שלב 7: שמירת מצב (חובה — לסשנים עתידיים)

לפני שאת מסיים, **שמור בזיכרון** (אם זה Claude Code):

- שם המשתתף
- מסלול הפריסה שבחרה (Railway/Mac/Windows)
- מיקום הקבצים שלו
- העלות החודשית הצפויה
- תאריך ההתקנה

זה ימנע מצב שבסשן עתידי תצטרכי לשאול אותה את הכל מהתחלה.

---

## חוקי ברזל לאורך הזרימה

1. **אל תדלגי על שלבים.** אם את לא בטוח — שאלי שוב. עדיף עוד שאלה מאשר התקנה שבורה.

2. **אל תקבעי פרטים אישיים בעצמך.** שם הבוט? היא בוחר. אישיות? היא מגדירה. מספר טלפון? היא נותן.

3. **רגע לפני כל פעולה הרסנית (Restart, מחיקה, החלפת קונפיג):** וודא שיש לה גיבוי + שהוא יודע מה הולך לקרות.

4. **חשבונית זיכוי חסומה.** הבוט שמותקנת מקבל מראש את ההגנה הזו. אם המשתתף שואל "למה?" — הסבר: זו פעולה מסוכנת מבחינה חשבונאית, עדיף ידנית באתר Green Invoice.

5. **המידע על הלקוחות שלו — סודי.** אם בקטגוריה 6 היא נותן שמות לקוחות לכלול ב-system prompt, התייחסי לזה בכבוד ולא תחזור על זה בלי הקשר.

6. **אם משהו לא ברור באמצע — שאלי אותה.** אל תניח הנחות לטובת מהירות.

7. **בסוף השלב — סיכמי מה עשיתן ומה הבא.** המשתתף צריך להרגיש שאת מובילה אותה, לא שהוא נסחפת.

---

## קבצים בקיט (מבנה)

```
talbs-bot-kit/
├── SKILL.md                    ← את כאן
├── references/                 ← הפירוט לכל שלב
│   ├── 00-preflight.md
│   ├── 01-business.md          ← קטגוריה 1
│   ├── 02-connections.md       ← קטגוריה 2
│   ├── 03-invoices.md          ← קטגוריה 3
│   ├── 04-crm.md               ← קטגוריה 4
│   ├── 05-automations.md       ← קטגוריה 5
│   ├── 06-system-prompt.md     ← קטגוריה 6
│   ├── 07-templating.md        ← איך להחליף placeholders
│   ├── 10-deploy-railway.md
│   ├── 11-deploy-mac.md
│   ├── 12-deploy-windows.md
│   ├── 20-verification.md
│   ├── 21-local-airtable-mcp.md  ← Airtable MCP מקומי (חובה אחרי פריסה)
│   ├── 22-local-gcal-mcp.md      ← Google Calendar MCP מקומי (אופציונלי לכתיבה)
│   └── 30-troubleshooting.md
├── templates/                  ← תבניות עם placeholders
│   ├── config.template.json
│   ├── system-prompt.template.md
│   └── env.template
├── scripts/                    ← קוד מוכן (גרסה גנרית)
│   ├── bot/
│   │   ├── green-api-bot.js
│   │   └── package.json
│   ├── invoice/
│   │   ├── greeninvoice_quote.py
│   │   ├── greeninvoice_invoice.py
│   │   └── send_quote_to_whatsapp.py
│   └── automations/
│       ├── morning-agenda.sh
│       ├── daily-summary.sh
│       └── health-check.sh
└── evals/                      ← מקרי בדיקה לסקיל עצמו
    └── evals.json
```

**אסטרטגית קריאה:** רק כשאת מגיעה לקטגוריה — קרא את ה-reference שלו. אל תטעיני הכל בבת אחת. זה מבזבז context.
