# Scripts — production-tested code

זה הקוד שהבוט מריץ בפועל. בעת התקנה ללקוח, הסקיל מעתיק את הקבצים האלה לסביבת העבודה שלו.

## מבנה

- **`bot/`** — הבוט עצמו (Node.js)
  - `green-api-bot.js` — Polling Green API, יוצר session per user, מפעיל Claude CLI
  - `package.json` — dependency declaration (Node 20+)
- **`invoice/`** — סקריפטי חשבונית ירוקה (Python 3)
  - `greeninvoice_quote.py` — הצעת מחיר (type 10)
  - `greeninvoice_invoice.py` — חשבון עסקה (100) / חשבונית מס קבלה (320) / קבלה (400). 🚫 חוסם 405
  - `send_quote_to_whatsapp.py` — שולח PDF דרך Green API
- **`automations/`** — שלוש אוטומציות יומיות (Bash)
  - `morning-agenda.sh` — אגנדת בוקר מ-Google Calendar (08:00 כברירת מחדל)
  - `daily-summary.sh` — סיכום ערב מ-Airtable (20:00 כברירת מחדל)
  - `health-check.sh` — בדיקת בריאות + ריסטרט אוטומטי כל שעה

## ✅ כל הקבצים גנריים — קוראים מ-.env

הסקריפטים הסתיו לקרוא את כל הפרטים האישיים (JID, paths, Airtable IDs, ntfy topic) מקובץ `.env` שיושב באותה תיקייה (או רמה אחת מעל). זה אומר:

- **אותו קוד עובד אצל כל לקוח**
- **לא נדרש sed/replacement** בעת התקנה
- **עדכון לקוד** = החלפת קבצים בלבד, `.env` נשאר כמו שהוא

ראה `references/07-templating.md` לפרטים על מבנה ה-`.env`.

## למה לא להמיר את הקוד לתבנית עם placeholders

הסקריפטים shell משתמשים ב-`heredoc` עם משתנים — קשה לכתוב אותם כתבניות נקיות בלי לפגוע בקריאות. הגישה הקיימת (`.env` בזמן ריצה) פותרת את זה יותר אלגנטית: אותו קוד, פרטים שונים פר-לקוח.
