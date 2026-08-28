#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""כלי עזר לעברית: ספירת הופעות עם גבולות מילה, וסריקת פרטיות.

grep לא אמין לגבולות מילה בעברית: התוצאה משתנה בין מימושים ולפי locale,
ולכן "שלום" נספר בתוך "תשלום" או לא נספר בכלל. הסקריפט הזה דטרמיניסטי.

שימוש:
  python3 hebtools.py count "מילה" "/נתיב/לקובץ"
  python3 hebtools.py lines "מילה" "/נתיב/לקובץ"
  python3 hebtools.py scan "/נתיב/לקובץ" [שם] [שם] ...
  python3 hebtools.py verify "/נתיב/SKILL.md" "/נתיב/_only-me.txt"
"""
import re
import sys

HEB = r"֐-׿"

SENSITIVE = [
    "ילד", "ילדה", "ילדים", "חולה", "מחלה", "ניתוח", "אשפוז", "אבחון",
    "גירוש", "גרוש", "אלמן", "אלמנה", "החזר", "חוב", "הלוואה", "משכנתא",
    "בעל", "בעלה", "אישה", "אשתו", "בן", "בת", "הריון", "פיטורים",
]


PREFIX = "הוbלשמכד".replace("b", "\u05d1")  # ה ו ב ל ש מ כ ד


def _pat(word, prefixes=False):
    """גבול מילה שמכבד אותיות עבריות, בלי תלות ב-locale.

    prefixes=True מתיר תחיליות עבריות לפני המילה (הבעל, לילד, ושלום),
    בלי לתפוס מילה אחרת שהמילה שלנו בלועה בתוכה (שלום בתוך תשלום).
    """
    pre = r"[{p}]{{0,2}}".format(p=PREFIX) if prefixes else ""
    return re.compile(
        r"(?<![{h}]){pre}(?:{w})(?![{h}])".format(
            h=HEB, pre=pre, w=re.escape(word)
        )
    )


def cmd_count(word, path):
    text = open(path, encoding="utf-8", errors="replace").read()
    bare = len(_pat(word).findall(text))
    pref = len(_pat(word, prefixes=True).findall(text))
    print("עצמאי: {}   כולל תחיליות: {}".format(bare, pref))
    if bare != pref:
        print("המספרים נבדלים, כלומר יש כאן צורות עם תחילית.")
        print("לרף שלוש ההופעות קח את המספר הכולל.")
        print("לטענה על צורת המילה עצמה, הרץ lines וקרא את השורות.")
    elif bare == 0:
        print("אפס. זו ראיה להיעדרות רק אחרי שהרצת lines וראית בעיניים,")
        print("ורק אם החומר גדול מספיק שהיית מצפה לראות את המילה.")
    else:
        print("מול רף שלוש ההופעות, השתמש במספר הזה.")


def cmd_lines(word, path):
    pat = _pat(word, prefixes=True)
    hits = 0
    for i, line in enumerate(
        open(path, encoding="utf-8", errors="replace"), 1
    ):
        if pat.search(line):
            hits += 1
            print("{}: {}".format(i, line.rstrip()))
    if hits == 0:
        print("(אפס הופעות, כולל תחיליות)")


def cmd_scan(path, names):
    """סורק פרטים רגישים. מדפיס שורה, מה נתפס, ולמה."""
    digits = re.compile(r"\d{3,}")
    name_pats = [(n, _pat(n, prefixes=True)) for n in names]
    sens_pats = [(w, _pat(w, prefixes=True)) for w in SENSITIVE]
    found = 0
    for i, line in enumerate(
        open(path, encoding="utf-8", errors="replace"), 1
    ):
        hits = []
        for n, p in name_pats:
            if p.search(line):
                hits.append("שם: " + n)
        for w, p in sens_pats:
            if p.search(line):
                hits.append("מילה רגישה: " + w)
        m = digits.search(line)
        if m:
            hits.append("מספר: " + m.group())
        if hits:
            found += 1
            print("{}: {}".format(i, line.rstrip()))
            print("    ← {}".format(" | ".join(hits)))
    if found == 0:
        print("(לא נתפס כלום. עדיין חובה לקרוא את הציטוטים בעיניים.)")
    else:
        print(
            "\n{} שורות לבדיקה. התאמה היא סימן, לא פסק דין: "
            "תקרא כל שורה ותחליט.".format(found)
        )



QUOTE_CHARS = '"\u201c\u201d\u05f4'
PROFILE_HEAD = "פרופיל הקול"
REQUESTED = "ניסוחים שהוא ביקש"


ANON = re.compile("[\u2039\u203a<>][^\u2039\u203a<>]{0,20}[\u2039\u203a<>]")


def _match_in(quote, src):
    """התאמה שמכבדת גבולות מילה בעברית, כדי שציטוט קצר לא יעבור
    בגלל שהוא בלוע בתוך מילה אחרת.

    ציטוט שהוחלף בו שם ב-‹שם› מאומת לפי הרצף הארוך ביותר שאין בו
    את ההחלפה, כך שאנונימיזציה לא הופכת ציטוט אמיתי למומצא."""
    if ANON.search(quote):
        parts = [x.strip(" ,.:;!?\"'-\u2013\u2014") for x in ANON.split(quote)]
        longest = max(parts, key=len) if parts else ""
        if len(longest.split()) < 2:
            return None  # מאונומם מדי לאימות
        return _pat(longest).search(src) is not None
    return _pat(quote).search(src) is not None


# גרשיים של ראשי תיבות יושבים לפני האות האחרונה במילה קצרה:
# עו״ד, בע״מ, מנכ״ל, ד״ר. מרכאה שאחריה מילה שלמה היא תוחם ציטוט
# אחרי תחילית, כמו ב"תודה", ואסור להתעלם ממנה.
GERSHAYIM = re.compile(
    "(?<=[\u0590-\u05ff])[\"\u05f4](?=[\u0590-\u05ff]{1,3}(?![\u0590-\u05ff]))")


def _delims(line):
    """סופר תווי מרכאה שהם באמת תוחמי ציטוט.
    גרשיים בתוך ראשי תיבות (עו״ד, בע״מ, מנכ״ל) אינם תוחמים."""
    return sum(1 for c in GERSHAYIM.sub("", line) if c in QUOTE_CHARS)


def _join_unbalanced(lines, notes=None):
    """מאחד ציטוט שנשבר לשתי שורות. מאחד שורה אחת בלבד קדימה,
    כדי ששורה עם מרכאה יחידה לא תבלע את שאר הקובץ."""
    out, buf, warn = [], None, []
    for i, line in enumerate(lines, 1):
        n = _delims(line)
        if buf is not None:
            merged = buf[1] + " " + line.strip()
            if n % 2 == 1:
                out.append(merged)
            else:
                warn.append(buf)
                out.append(buf[1])
                out.append(line)
            buf = None
            continue
        if n % 2 == 1:
            buf = (i, line)
        else:
            out.append(line)
    if buf is not None:
        warn.append(buf)
        out.append(buf[1])
    for i, text in warn:
        st = text.strip().lstrip("*_ ")
        if "איך זה נשמע אצלי" in text or st.startswith(("-", "*", "\u2022")):
            if notes is not None:
                notes.append((i, text.strip()[:52],
                              "מרכאה שלא נסגרה — הציטוט הזה לא נבדק. "
                              "תקן את המרכאות והרץ שוב"))
    return out


def _is_bullet(line):
    st = line.strip().lstrip("*_ ")
    return st.startswith(("-", "*", "\u2022"))


def _extract(line):
    skip = {m.start() for m in GERSHAYIM.finditer(line)}
    idx = [i for i, c in enumerate(line)
           if c in QUOTE_CHARS and i not in skip]
    if len(idx) < 2:
        return None, False
    return line[idx[0] + 1:idx[-1]].strip(), len(idx) > 2


def _head_num(text):
    """כותרת של חלק פרופיל: המספר הוא הטוקן הראשון בכותרת."""
    m = re.match(r"^\**\s*([0-8])\s*[.:)\u05f3]\s", text.strip() + " ")
    return int(m.group(1)) if m else None


def cmd_verify(skill_path, source_path):
    raw = open(skill_path, encoding="utf-8", errors="replace").read()
    src = open(source_path, encoding="utf-8", errors="replace").read()
    raw_lines = raw.split("\n")
    if raw_lines and raw_lines[0].strip() == "---":
        for k in range(1, len(raw_lines)):
            if raw_lines[k].strip() == "---":
                raw_lines = raw_lines[k + 1:]
                break
    src_lines = [l for l in raw_lines
                 if not l.strip().startswith("<") and "<!--" not in l]
    skipped = []
    lines = _join_unbalanced(src_lines, skipped)

    inside = False
    scope_depth = 99
    part = None
    quotes = []
    stray = []
    exempt = []
    parts_seen = set()
    requested = False
    seen_profile = False
    for i, line in enumerate(lines, 1):
        st = line.strip()
        if st.startswith("#"):
            depth = len(st) - len(st.lstrip("#"))
            text = st.lstrip("#").strip()
            if PROFILE_HEAD in text:
                inside = True
                seen_profile = True
                scope_depth = depth
                part = None
                requested = False
                continue
            num = _head_num(text) if seen_profile else None
            if num is not None:
                inside = True
                scope_depth = min(scope_depth, depth - 1)
                part = num
                parts_seen.add(num)
                requested = False
                continue
            requested = text.strip().startswith("ניסוחים ש")
            if inside and depth <= scope_depth:
                inside = False
                part = None
            continue

        # placeholder של התבנית, לא תוכן
        if st.startswith("<") or "<!--" in line:
            continue

        q, inner = _extract(line)
        is_calib = "איך זה נשמע אצלי" in line
        is_bullet = _is_bullet(line)

        if not inside:
            # הסעיף "ניסוחים שהוא ביקש" פטור מאימות אותנטיות, כי אלה
            # נוסחאות שנמסרו בעל פה. אבל הן מוצגות, כדי שלא יהיה מקום
            # בקובץ שאפשר להחביא בו טקסט בלי שאף אחד יראה אותו.
            if requested:
                if q:
                    exempt.append((i, q))
                continue
            if q:
                if len(q.split()) >= 2:
                    stray.append((i, q, inner))
                else:
                    skipped.append((i, q, "מחוץ לפרופיל וקצרה מדי לאימות "
                                          "— עבור עליה בעיניים"))
            continue

        # כל מחרוזת מצוטטת בהיקף מקבלת החלטה מפורשת. שום דבר לא נעלם בשקט.
        if "כשזה לא אני" in line:
            continue
        if q is None:
            if is_calib:
                skipped.append((i, "(בלי מרכאות)",
                                "שורת ציטוט בלי מרכאות — עטוף אותה"))
            continue
        if part == 7 and not is_calib:
            continue  # מילות האיסור בחלק 7, לפי ההגדרה
        if not (is_calib or is_bullet):
            skipped.append((i, q, "אזכור בתוך משפט הכלל, לא ציטוט כיול"))
            continue
        if len(q.split()) < 2:
            skipped.append((i, q, "מילה בודדת — קצר מדי לאימות אמין"))
            continue
        quotes.append((i, q, inner))

    if not quotes:
        print("=" * 62)
        print("שגיאה: לא נמצא אף ציטוט בהיקף. הבדיקה לא רצה.")
        print("=" * 62)
        print("אל תדווח שהאימות עבר. כמעט תמיד אחת מהשתיים:")
        print("  1. אין ב-SKILL.md כותרת שמכילה '" + PROFILE_HEAD + "'")
        print("  2. הציטוטים לא יושבים בשורות 'איך זה נשמע אצלי'")
        print("     ולא בתבליטים בחלקים 6 ו-8")
        print("תקן את מבנה הקובץ לפי references/personal-skill-template.md")
        print("והרץ שוב.")
        return

    seen = {}
    for i, q, inner in quotes:
        if q not in seen:
            seen[q] = (i, inner)

    print("נמצאו {} ציטוטים בהיקף ({} ייחודיים).\n".format(
        len(quotes), len(seen)))
    failed, merged = [], []
    for q, (i, inner) in seen.items():
        ok = _match_in(q, src)
        if ok is None:
            skipped.append((i, q, "מאונומם מדי לאימות — קצר את ההחלפה "
                                  "ל-‹שם› או ותר על הציטוט"))
            continue
        print("{}  שורה {:>4}  {}".format("עבר " if ok else "נכשל", i, q[:70]))
        if inner:
            merged.append((i, q))
        if not ok:
            failed.append((i, q))

    print("\n" + "-" * 62)

    print("חלקי פרופיל שנסרקו: {}".format(
        ", ".join(str(x) for x in sorted(parts_seen)) or "אף אחד"))
    if exempt:
        print("\n" + "-" * 62)
        print("{} ניסוחים בסעיף הניסוחים. **לא נבדקו מול החומר.**".format(
            len(exempt)))
        for i, q in exempt:
            print("  שורה {:>4}  {}".format(i, q[:60]))
        print("לכל אחד: הצבע על ההודעה שבה המשתמש כתב אותו במילותיו. "
              "אם אינך יכול, מחק אותו. ובדוק שאין בהם שם, מספר או מחיר.")

    if stray:
        print("\n" + "-" * 62)
        print("{} ציטוטים יושבים מחוץ לסעיף 'פרופיל הקול'. "
              "בדקתי אותם בכל זאת:".format(len(stray)))
        for i, q, _ in stray:
            ok = _match_in(q, src)
            print("{}  שורה {:>4}  {}".format(
                "עבר " if ok else "נכשל", i, q[:60]))
            ok = bool(ok)
            if not ok:
                failed.append((i, q))
        print("להעביר אותם לתוך הפרופיל, אחרת הסקיל לא ישתמש בהם.")

    if skipped:
        print("\n" + "!" * 62)
        print("{} מחרוזות מצוטטות לא נבדקו. עבור עליהן:".format(
            len(skipped)))
        print("!" * 62)
        for i, q, why in skipped:
            print("  שורה {:>4}  {}".format(i, q[:52]))
            print("            ← {}".format(why))
        print("\nאם אחת מהן היא ציטוט כיול אמיתי, תקן את מיקומה או את "
              "המרכאות והרץ שוב. אל תדווח שהאימות הושלם לפני כן.")
    if merged:
        print("\n{} ציטוטים הכילו מרכאות פנימיות ואוחדו למחרוזת אחת, "
              "כדי שלא ייבדק חצי ציטוט. אם אחד מהם הוא בעצם שני ציטוטים "
              "נפרדים באותה שורה, לפצל ולבדוק כל אחד לחוד:".format(
                  len(merged)))
        for i, q in merged:
            print("  שורה {}: {}".format(i, q[:70]))
    if failed:
        print("\n{} ציטוטים לא נמצאו. לפני שמוחקים, לעבור על ארבעת "
              "נתיבי הגיבוי ב-references/verification.md:".format(len(failed)))
        for i, q in failed:
            print("  שורה {}: {}".format(i, q))
        n_scope = sum(1 for i, q in failed if q in seen)
        if n_scope > 2:
            print("\n{} כשלים בתוך הפרופיל. אם הם לא נפתרים בנתיבי "
                  "הגיבוי, לעבור על כל הפרופיל מחדש. מחרוזות מחוץ "
                  "להיקף ותקלות חילוץ לא נספרו.".format(n_scope))
    elif skipped or stray:
        print("\nכל הציטוטים שנבדקו אומתו, אבל נשארה פעולה: יש מחרוזות "
              "ברשימות למעלה שצריך להעביר, לתקן או למחוק.")
    else:
        print("\nכל הציטוטים אומתו מול מה שהמשתמש עצמו כתב.")

    in_scope_failed = sum(1 for i, q in failed if q in seen)
    unchecked = sum(1 for i, q, _ in skipped if q in seen)
    passed = len(seen) - in_scope_failed - unchecked
    print("\n" + "=" * 62)
    if failed or skipped or stray:
        print("N זמני: {} ציטוטים עברו. אל תמסור אותו למשתמש עדיין —".format(
            passed))
        print("קודם לטפל בכשלים וברשימת 'לא נבדקו', ואז להריץ שוב.")
    else:
        print("N לדיווח למשתמש: {}".format(passed))
    print("=" * 62)

def main():
    a = sys.argv[1:]
    if not a:
        print(__doc__)
        return 1
    if a[0] == "count" and len(a) == 3:
        cmd_count(a[1], a[2])
    elif a[0] == "lines" and len(a) == 3:
        cmd_lines(a[1], a[2])
    elif a[0] == "scan" and len(a) >= 2:
        cmd_scan(a[1], a[2:])
    elif a[0] == "verify" and len(a) == 3:
        cmd_verify(a[1], a[2])
    else:
        print(__doc__)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
