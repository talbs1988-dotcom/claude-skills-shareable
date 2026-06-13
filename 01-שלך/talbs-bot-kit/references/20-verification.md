# 20 — אימות End-to-End

המטרה: לוודא שהבוט באמת עובד — לא רק שהוא "פרוס", אלא שהוא מקבל הודעה ומגיב.

## למה חשוב

deployment שעלה לא אומר שהבוט מגיב. שיהיה authorized ב-Green API לא אומר שהוא יודע לדבר עם Claude. **חייבים לבדוק end-to-end** לפני שאנחנו מסיימים את ההתקנה ומכריזים על הצלחה.

## ארבע הבדיקות (לפי הסדר)

עבור על כולן. אם אחת נכשלת — אל תמשיך לבאה.

### בדיקה 1: התהליך/האפליקציה רץ

**ענן (Railway):**

- היכנס ל-Railway → ה-project → Deployments
- האם הסטטוס "Active" (ירוק)?
- לחצי על ה-deployment → Logs
- חפשי בלוגים: `🚀 Green API bot starting` או `🟢 starting poll loop`
- ✅ אם רואים — בדיקה עבר
- ❌ אם לא — עבור ל-`30-troubleshooting.md`, סעיף "deployment לא רץ"

**Mac (אם בחר מקומי):**

```bash
pgrep -fl green-api-bot.js
```

- ✅ אם החזיר PID — רץ
- ❌ אם לא — `launchctl load ~/Library/LaunchAgents/com.[user].green-api-bot.plist`

**Windows (אם בחר מקומי):**

- פתח Task Manager
- חפשי `node.exe` שרץ עם green-api-bot
- ✅ אם יש — רץ
- ❌ אם לא — Task Scheduler → השם של המשימה → Run

### בדיקה 2: HTTP endpoint מגיב

הבוט מריץ HTTP server על port 7654 (מקומי) או על הדומיין של Railway.

**ענן:**

```
פתח בדפדפן: [Dashboard URL מ-Railway]
```

צריך לראות עמוד דאשבורד עם "🤖 [שם הבוט]" וסטטוס.

**מקומי:**

```bash
curl -s http://127.0.0.1:7654/ | head -5
```

או פתח בדפדפן `http://127.0.0.1:7654/`.

- ✅ אם רואים HTML עם שם הבוט — עובר
- ❌ אם "Connection refused" או דף ריק — הבוט לא טען נכון. בדוק logs

### בדיקה 3: Green API מחובר (Authorized)

זה הקריטי. בלי זה — הבוט לא יקבל שום הודעה מ-WhatsApp.

```bash
# מקומי
INSTANCE=[GREEN_API_INSTANCE_ID]
TOKEN=[GREEN_API_TOKEN]
curl -s "https://api.green-api.com/waInstance${INSTANCE}/getStateInstance/${TOKEN}"
```

או דרך הדפדפן: `https://console.green-api.com/` → instance → State.

**תוצאות אפשריות:**

- `{"stateInstance":"authorized"}` ✅ — בדיקה עבר!
- `{"stateInstance":"notAuthorized"}` ❌ — צריך לסרוק QR שוב
- `{"stateInstance":"blocked"}` ❌ — חשבון Green API נחסם, פני לתמיכה
- `{"stateInstance":"starting"}` ⏳ — חכה 30 שניות ונסי שוב

### בדיקה 4: הודעת בדיקה אמיתית (החשובה ביותר)

זה ה-test האולטימטיבי:

```
בקש מהמשתתפת:

"עכשיו אצלך ב-WhatsApp:
1. שלח הודעה לעצמך (לצ'אט הפרטי שלך, אותו מספר):
   'בדיקה — מה השעה?'

2. חכה 5-15 שניות.

3. תקבלי תשובה מהבוט שלך?"
```

**אפשרויות:**

- ✅ קיבלה תשובה רלוונטית — **🎉 הבוט עובד!** עבור לשלב 6.
- ⏳ חכתה דקה ועדיין שום דבר — בדוק logs (`30-troubleshooting.md`)
- ❌ קיבלה הודעת שגיאה ("מצטער, יש בעיה") — בדוק שה-ANTHROPIC_API_KEY תקף

---

## ✅ אם כל 4 הבדיקות עברו

ברך אותה:

```
🎉 הבוט שלך פעיל ועובד!

עברנו את כל הבדיקות:
✅ הבוט רץ ב-[Railway/מק/Windows]
✅ הדאשבורד נגיש: [URL]
✅ WhatsApp מחובר (authorized)
✅ קיבלת תגובה ראשונה

עכשיו אנחנו עוברים לשלב האחרון — סיכום והוראות להמשך.
```

עבור לשלב 6 ב-SKILL.md.

---

## ❌ אם משהו נכשל

**אל תסיימי את ההתקנה.** עבור ל-`30-troubleshooting.md` ופתרי את הבעיה הספציפית.

אם אחרי 30 דקות עדיין לא עובד:

- שמור את כל ה-credentials במקום בטוח אצלו
- תעדי במדויק מה לא עבד (לוגים, screenshots)
- הצע שתחזרי אליך אחרי ש-Tal תבדוק (אם זה במסגרת הסדנה)

---

## צ'קליסט מהיר

לפני שאת מכריזה על סוף — וודא:

- [ ] Process running (Railway active / pgrep returns PID)
- [ ] HTTP responding (dashboard loads)
- [ ] Green API state = "authorized"
- [ ] Real WhatsApp message → real Claude response
- [ ] Logs נקיים (אין repeating errors)
- [ ] (אם רלוונטי) אגנדת בוקר מתוזמנת
- [ ] (אם רלוונטי) סיכום ערב מתוזמן
- [ ] (אם רלוונטי) Health check רץ
- [ ] משתתף יודע איפה הדאשבורד שלו
- [ ] משתתף יודע מה לעשות אם הבוט נופל
