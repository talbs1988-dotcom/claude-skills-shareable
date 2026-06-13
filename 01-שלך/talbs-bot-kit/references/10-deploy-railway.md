# 10 — פריסה לענן (Railway) — המסלול המומלץ

המטרה: להעלות את הבוט לשרת ענן Railway, להגדיר את ה-environment variables, ולחבר את WhatsApp.

## למה Railway

- $5 לחודש קבוע
- 5 דקות מאפס לבוט עובד
- ממשק ויזואלי, בלי terminal
- מבוסס על תשתית של Google Cloud — אבטחה ברמה גבוהה
- הבוט רץ 24/7 — לא תלוי במחשב של המשתתף

## דרישות מקדימות

לפני שמתחילים:

- ✅ כל הקבצים מוכנים מ-`07-templating.md` (config.json, .env)
- ✅ חשבון Green API (יש credentials)
- ✅ Anthropic API key
- ✅ Airtable API key
- ✅ כרטיס אשראי לחיוב Railway

## שלבי הפריסה

### שלב 1: יצירת חשבון Railway

הסבר:

```
עכשיו ניצור לך חשבון בענן Railway.

1. תיכנס ל-https://railway.app
2. לחצי "Login" → "Login with GitHub"
   (אם אין לך GitHub — תיצרי בחינם ב-github.com/signup ראשונה)
3. אשרי הרשאות בסיסיות
4. תקבלי credit ראשוני חינם של $5 לבדיקה
```

המתן שתאשר ושיש לה חשבון פעיל.

### שלב 2: יצירת project ו-deploy של הקוד

יש שתי דרכים — בחר לפי הסביבה שלך:

#### דרך A — את ב-Claude Code (CLI)

```bash
# התקנת Railway CLI (פעם אחת)
npm install -g @railway/cli

# התחברות (יפתח דפדפן לאישור)
railway login

# יצירת project ו-deploy
cd ~/whatsapp-bot
railway init
railway up
```

הסבר לה כל פעולה לפני ביצוע. בקש אישור לפני `railway up`.

#### דרך B — דרך הדפדפן (claude.ai)

```
1. ב-Railway → New Project → Deploy from GitHub
2. אתה צריך להעלות את הקוד ל-GitHub repo קודם:
   - תפתח repo חדש (פרטי!) ב-github.com/new
   - שם: whatsapp-bot
   - תעלי לשם את הקבצים שיצרנו (אני אעזור לך לארוז zip)
3. ב-Railway, בחר את ה-repo
4. Railway יעשה deploy אוטומטית
```

### שלב 3: הגדרת Environment Variables

ב-Railway → ה-project → Variables:

הזן את כל המפתחות מ-`.env`. **לא** לעלות את `.env` עצמו ל-GitHub.

```
GREEN_API_INSTANCE_ID = [מ-2.1]
GREEN_API_TOKEN = [מ-2.1]
ANTHROPIC_API_KEY = [מ-2.2]
AIRTABLE_API_KEY = [מ-4]
AIRTABLE_BASE_ID = [מ-4]
GREENINVOICE_API_KEY = [מ-3, אם רלוונטי]
GREENINVOICE_API_SECRET = [מ-3, אם רלוונטי]
PORT = 7654
```

הסבר: "אלה אותם מפתחות שעבדנו איתם. שמור אותם ב-Railway, לא ב-GitHub."

### שלב 4: חיבור WhatsApp (סריקת QR)

זה השלב הקריטי. הוראות:

```
עכשיו נחבר את WhatsApp שלך ל-Green API:

1. תיכנס ל-https://console.green-api.com/
2. בחר את ה-instance שלך
3. תיראי QR code

4. בטלפון שלך:
   - פתח WhatsApp
   - תפריט (3 נקודות) → מכשירים מקושרים
   - "קשרי מכשיר"
   - אישור עם Face ID / טביעת אצבע / קוד
   - סרקי את ה-QR מהמסך

5. תוך 5 שניות תראי "Authorized" ב-Green API.
```

**אזהרה:** "אם הסטטוס לא הופך ל-Authorized תוך דקה — נסה שוב, או רענני את ה-QR ב-Green API."

### שלב 5: וידוא ש-deployment עלה

בדוק ב-Railway → ה-project → Deployments:

- האם הסטטוס "Active"?
- האם יש שגיאות ב-logs?

אם יש שגיאות:

- `missing GREEN_API_INSTANCE_ID` → לא הגדרת Environment Variable כראוי
- `ECONNREFUSED` → בעיית רשת זמנית, חכה 30 שניות ונסי
- אחר → עבור ל-`30-troubleshooting.md`

### שלב 6: קבלת ה-URL של הדאשבורד (אופציונלי)

ב-Railway → Settings → Networking → Generate Domain:

```
תקבלי URL כמו: https://whatsapp-bot-production-XXXX.up.railway.app
זה הדאשבורד של הבוט שלך. שמור אותו במועדפים.
```

---

## פלט שלב הפריסה

```
✅ Railway project: [project_name]
✅ Deployment status: Active
✅ Green API state: authorized
✅ Dashboard URL: https://...
✅ Environment Variables: 7+
```

---

## עוברים לשלב 5: אימות (`20-verification.md`)

---

## טיפים

- **אם Railway מבקש כרטיס אשראי לפני deploy** — זה אחרי ה-$5 credit. הסבר שזה רק לאחר שהשתמשנו ב-$5.
- **GitHub repo חייב להיות Private** אם הקוד מכיל פרטים אישיים. למרות שאנחנו לא שמים את `.env` ב-repo, עדיין עדיף private.
- **אם הוא לא בנוח עם GitHub** — דרך A (CLI) פותרת את זה. אבל דורש שתהיה ב-Claude Code.
- **Logs ב-Railway:** ה-logs נשמרים 7 ימים בתוכנית Hobby. אם זה מציק — אפשר לשדרג ל-Pro או להוריד logs יזומה.
