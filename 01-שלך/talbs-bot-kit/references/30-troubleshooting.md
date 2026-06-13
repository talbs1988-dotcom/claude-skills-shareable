# 30 — Troubleshooting

מדריך פתרון בעיות נפוצות. עבור על הסעיפים לפי התסמין.

## ⚡ סעיף ראשון — Bot Stopped Responding (הכי נפוץ — 90% מהבעיות)

**תסמין:** המשתתף שולח הודעות, הבוט לא עונה.

**95% מהמקרים: WhatsApp ניתק מ-Green API.** WhatsApp Web עושה auto-logout מדי פעם.

**הפתרון (60 שניות):**

1. היכנס ל-https://console.green-api.com/
2. בחר את ה-instance שלך
3. אם הסטטוס "notAuthorized" — תראי QR חדש
4. בטלפון: WhatsApp → מכשירים מקושרים → קשרי מכשיר → סרקי QR
5. תוך 5 שניות — "authorized"
6. הבוט מיד יחזור לעבוד (ההודעות שחיכו בתור — יענה עליהן)

**הסיבה:** WhatsApp לפעמים מנתק את WhatsApp Web (החלפת SIM, אי-פעילות של 14 ימים, פתיחת WhatsApp Web במקום אחר, וכו'). זה לא תקלה בקוד שלך.

**מתי לדאוג:** רק אם זה קורה **פעם בשבוע או יותר**. אז יש מצב של בעיה אחרת.

---

## Bot Process לא רץ

**תסמין:** `pgrep` לא מחזיר כלום, Railway logs ריקים, או deployment "Failed".

### ענן (Railway)

1. ענה לטאב Logs ב-Railway
2. חפשי שגיאות. השכיחות:
   - `Cannot find module` → חסר dependency. בדוק `package.json` שלם
   - `missing GREEN_API_INSTANCE_ID` → Environment Variable לא הוגדרה ב-Railway
   - `EADDRINUSE :::7654` → port כבר תפוס. ב-Railway זה אומר deployment כפול — בטלי אחד
3. אם הכל נראה תקין — Click "Redeploy" ב-Railway

### Mac

```bash
# בדוק שה-plist קיים
ls ~/Library/LaunchAgents/com.*.green-api-bot.plist

# טעני מחדש
launchctl unload ~/Library/LaunchAgents/com.[user].green-api-bot.plist
launchctl load ~/Library/LaunchAgents/com.[user].green-api-bot.plist

# בדוק שרץ
pgrep -fl green-api-bot.js
```

### Windows

1. Task Scheduler → השם של המשימה
2. ימני קליק → "Run"
3. בדוק ב-Task Manager שיש `node.exe`

---

## HTTP Endpoint לא מגיב

**תסמין:** הדאשבורד לא נטען / `curl http://localhost:7654/` נכשל.

**מקומי:**

- בדוק שהתהליך באמת רץ (`pgrep`)
- בדוק שאין firewall שחוסם port 7654
- בדוק שאין תהליך אחר שמשתמש ב-port:
  ```bash
  lsof -i :7654
  ```

**ענן:**

- וודא שב-Railway יש PORT env var = 7654
- וודא שב-Railway יש Domain מוגדר (Settings → Networking)

---

## הבוט עונה אבל התשובות שגויות / רובוטיות

**תסמין:** הבוט עונה משהו כללי כמו "אני בוט AI" במקום הקונטקסט המותאם.

**הסיבות הסבירות:**

1. **`config.json` עם system prompt שגוי** — בדוק שה-`systemPromptAppend` מכיל את הטקסט שבנינו בקטגוריה 6
2. **placeholder לא הוחלף** — בדוק:
   ```bash
   grep -E "\{\{[A-Z_]+\}\}" ~/whatsapp-bot/config.json
   ```
3. **לא נטען config חדש** — צריך restart לבוט

**פתרון:** ערכי את `config.json`, restart לבוט:

```bash
# ענן
railway up

# Mac
pkill -f green-api-bot.js  # launchd יעלה אוטומטית
```

---

## הבוט עונה: "מצטער, יש בעיה" / שגיאת Claude

**תסמין:** במקום תשובה חכמה, הבוט עונה הודעת שגיאה.

**הסיבות:**

1. **ANTHROPIC_API_KEY לא תקף** — נסה ל-https://console.anthropic.com → API Keys → וודא שהמפתח שלך עובד
2. **הגעת ל-rate limit** — Claude Pro מוגבל. אם הבוט שולח הרבה הודעות — שדרגי ל-Max ($200) או לעבור ל-API ($)
3. **המפתח לא מוגדר ב-environment** — בדוק שב-Railway/`.env` יש `ANTHROPIC_API_KEY`

---

## חשבונית לא נוצרת / שגיאה ב-Green Invoice

**תסמין:** המשתתף ביקשה חשבונית, הבוט החזיר "ok: false" עם שגיאה.

**שגיאות נפוצות:**

- `"כשל בהתחלות"` — API key/secret שגוי
- `"חסר --payment-type"` — הבוט קרא לסקריפט בלי הפרמטר. צריך לעדכן את ה-config
- `"חשבונית זיכוי (type 405) חסומה"` — זה לא תקלה! זה ההגנה שלנו עובד. אם הוא צריך זיכוי — ידנית באתר Green Invoice
- `"prefix לא תואם"` — המספר שחזר לא תואם להגדרות. בדוק באתר Green Invoice שה-prefixes לא השתנו

---

## Airtable: "permission denied" / לא רואה רשומות

**תסמין:** הבוט אומר שהוא לא מצליח לקרוא/לכתוב ל-Airtable.

**הסיבות:**

1. **API token שגוי או פג תוקף** — צור חדש ב-airtable.com/create/tokens
2. **לטוקן אין הרשאות לבסיס המדויק** — בעת יצירת ה-token, בחר את ה-base הספציפי
3. **ה-table IDs שגויים** — בדוק דרך airtable.com/developers/web/api/introduction

---

## עלות חודשית גבוהה מדי

**תסמין:** המשתתף מקבלת חשבונות גבוהים מהצפוי.

**ברירות מחדל סבירות:**

- Railway: $5/חודש
- Claude Pro: $20/חודש
- Green API: $12/חודש
- **סה"כ: ~$37 (~140₪)**

אם זה יותר:

- **Claude:** את עוברת לתוכנית Max ($200)? בדוק ב-claude.ai → Settings → Billing
- **Railway:** הבוט שלך לא ב-Hobby plan? בדוק ב-Settings → Plan. אם זה Pro — הורידי
- **Green API:** אולי לחצת על Business+ במקום Developer/Business

---

## דברים שאני לא יודע לפתור

אם אחרי 30 דקות עדיין לא עובד:

1. **שמור screenshot/copy של ה-logs**
2. **שמור את כל הצעדים שניסית**
3. **הצע לפנות לטל בשור** (כי זה במסגרת הסדנה שלה)

אל תיתני למשתתפת תחושה שיש כשלון. תן לה תחושה שזו תקלה ידועה שיש לה פתרון, פשוט דורש מישהי טכנית יותר.

---

## חוקי זהב לפתרון בעיות

1. **תקרא את ה-logs קודם.** רוב הבעיות אפשר לאבחן רק מהלוגים.
2. **אל תקפצי לפתרון בלי לאבחן.** אם רץ "אולי זה ה-X" — בדוק X לפני שמשנה אותו.
3. **שיני דבר אחד בכל פעם.** אם משני 3 דברים יחד ומשהו נשבר — לא תדעי איזה גרם.
4. **שמור הגיבוי** של config.json לפני כל שינוי משמעותי.
5. **כשפותרים — תעדי מה היה ומה תיקנת.** המשתתף תזכור שזה קרה.
