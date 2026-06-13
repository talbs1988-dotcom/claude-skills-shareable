---
name: security-and-hardening
description: "מאבטח סביבת Claude Code — 3 שכבות הגנה. הפעל כשרוצים לאבטח סביבה חדשה, לחסום גישה לקבצי .env, להוסיף hooks אבטחתיים, או לסקור את מצב האבטחה."
user-invocable: true
---

# אבטחת סביבת Claude Code

## למה זה חשוב?

Claude Code פועל כ-agent עם גישה לקבצים, טרמינל, ואינטרנט. אם קובץ זדוני (prompt injection) מגיע לפרויקט — Claude עשוי לבצע פקודות בלי שהרגשת. שלוש השכבות הבאות עוצרות את זה.

## מצב לפני התחלה — בדיקה מהירה

הרץ את זה בטרמינל כדי לראות מה חסר:

```bash
echo "=== בדיקת אבטחת Claude Code ===" && \
grep -q '"deny"' ~/.claude/settings.json 2>/dev/null && echo "✅ deny rules" || echo "❌ deny rules חסרות" && \
jq -e '.hooks.PreToolUse[] | select(.hooks[]?.command | contains(".env"))' ~/.claude/settings.json >/dev/null 2>&1 && echo "✅ security hook" || echo "❌ security hook חסר" && \
grep -q "כללי אבטחת מידע" ~/.claude/CLAUDE.md 2>/dev/null && echo "✅ כללי CLAUDE.md" || echo "❌ כללי CLAUDE.md חסרים" && \
jq --version >/dev/null 2>&1 && echo "✅ jq מותקן" || echo "❌ jq חסר — הרץ: brew install jq"
```

## כשמפעילים את הסקיל — מה Claude יעשה

כשמישהו מפעיל `/security-and-hardening`, Claude יבצע את 3 השכבות הבאות **בפועל** ב-settings.json וב-CLAUDE.md:

---

## שכבה 1 — Deny Rules (חוסם קריאת .env)

**מה:** Claude יוסיף ל-`~/.claude/settings.json` תחת `permissions`:

```json
"deny": [
  "Read(**/.env)",
  "Read(**/.env.*)",
  "Read(**/.env*)"
]
```

**למה:** Claude לא יוכל לקרוא קבצי `.env` גם אם יתבקש — גם על-ידי קובץ זדוני.

**בדיקה אחרי:** בקש מ-Claude לקרוא `~/.env` — צריך לקבל שגיאת הרשאות.

---

## שכבה 2 — PreToolUse Hook (חוסם cat .env)

**מה:** Claude יוסיף ל-`hooks.PreToolUse` ב-settings.json:

```json
{
  "matcher": "Bash",
  "hooks": [
    {
      "type": "command",
      "command": "cmd=$(jq -r '.tool_input.command // empty'); if echo \"$cmd\" | grep -qiE '(cat|less|more|head|tail)[[:space:]].*\\.env'; then echo '🛡️ BLOCKED: קריאת קובץ .env חסומה מטעמי אבטחה' >&2; exit 2; fi"
    }
  ]
}
```

**למה:** אם Claude מנסה להריץ `cat .env` — הפקודה נחסמת לפני שמגיעה למעטפת (`exit 2` = חסימה מוחלטת).

**דרישה:** `jq` חייב להיות מותקן:

```bash
jq --version || brew install jq
```

---

## שכבה 3 — כללי בית (CLAUDE.md)

**מה:** Claude יוסיף ל-`~/.claude/CLAUDE.md`:

```markdown
## כללי אבטחת מידע

- **לעולם** אל תרשום מפתחות API, סיסמאות או טוקנים ישירות בתוך קבצי קוד
- אם צריך משתנה סביבה חדש — בקש להוסיף אותו ל-settings.json דרך `read -s`
- אל תריץ `cat .env` או פקודות שקוראות קבצי סודות ישירות
- לפני חיבור שרת MCP חדש — עצור ובקש אישור מפורש
- אל תשתמש ב-`eval` או `exec` עם קלט לא מוודא מהמשתמש
```

**למה:** Claude קורא את הקובץ הזה בתחילת כל שיחה — זו שכבת כוונה שמחזקת את כללי האבטחה.

---

## סדר ביצוע (Claude יבצע בסדר הזה)

1. בדוק אם `jq` מותקן — אם לא, הנחה להתקין
2. קרא את `~/.claude/settings.json`
3. הוסף `deny` rules אם חסרות
4. הוסף security hook ל-`PreToolUse` אם חסר
5. פתח `~/.claude/CLAUDE.md` והוסף קטע אבטחה אם חסר
6. הרץ את בדיקת התקינות ואשר שהכול ירוק

---

## אזהרות MCP

לפני חיבור שרת MCP חדש — בדוק:

| שאלה                             | סיכון אם לא בדקת                              |
| -------------------------------- | --------------------------------------------- |
| האם ה-repo ב-GitHub מוכר ומוודא? | שרת מזויף יכול לרוץ כ-agent                   |
| מי כתב את ה-schema של הכלים?     | כלי עם `description` זדוני = prompt injection |
| האם יש גישה לרשת / קבצים?        | data exfiltration                             |

**כלל:** ספק מוכר (Anthropic, GitHub, Cloudflare) בלבד — לא repo אקראי ב-npm/GitHub.

---

## רמות אבטחה לפי גודל

| רמה        | מי זה        | מה מתאים                                                   |
| ---------- | ------------ | ---------------------------------------------------------- |
| **בסיסי**  | בעל עסק יחיד | שכבות 1–3 (מה שעשינו כאן)                                  |
| **צוות**   | 2–10 אנשים   | + shared `settings.json` ב-repo + code review על CLAUDE.md |
| **ארגוני** | 10+ / ייצור  | + Docker sandbox + audit logs + SIEM                       |

---

## בדיקת תקינות סופית

```bash
echo "=== תוצאה סופית ===" && \
grep -q '"deny"' ~/.claude/settings.json && echo "✅ deny rules פעילות" || echo "❌ deny rules חסרות" && \
jq -e '.hooks.PreToolUse[] | select(.hooks[]?.command | contains(".env"))' ~/.claude/settings.json >/dev/null 2>&1 && echo "✅ security hook פעיל" || echo "❌ security hook חסר" && \
grep -q "כללי אבטחת מידע" ~/.claude/CLAUDE.md && echo "✅ כללי CLAUDE.md קיימים" || echo "❌ כללי CLAUDE.md חסרים"
```

כל ✅ = מוגנת. כל ❌ = החזר /security-and-hardening ובקש מ-Claude לתקן.
