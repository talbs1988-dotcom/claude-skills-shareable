#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════
#  ספריית הסקילים של טל בשור — סדנת Claude Code Business
#  התקנת סקיל בודד:   ... | bash -s <skill-name>
#  התקנת הכל:         ... | bash
# ════════════════════════════════════════════════════════════
set -e
REPO="https://github.com/talbs1988-dotcom/claude-skills-shareable.git"
DEST="$HOME/.claude/skills"
WANT="${1:-}"
TMP="$(mktemp -d)"

if [ -n "$WANT" ]; then
  echo "📥 מתקין את הסקיל '$WANT'..."
else
  echo "📥 מתקין את כל הסקילים של טל..."
fi

git clone --depth 1 "$REPO" "$TMP" >/dev/null 2>&1 || {
  echo "❌ ההתקנה נכשלה. ודאו חיבור לאינטרנט ונסו שוב."
  exit 1
}

mkdir -p "$DEST"
n=0
last=""
while IFS= read -r sk; do
  name="$(basename "$sk")"
  if [ -z "$WANT" ] || [ "$WANT" = "$name" ]; then
    rm -rf "$DEST/$name"
    cp -R "$sk" "$DEST/"
    echo "  ✓ $name"
    n=$((n + 1))
    last="$name"
  fi
done < <(find "$TMP" -name SKILL.md -not -path '*/.git/*' -exec dirname {} \;)

rm -rf "$TMP"

if [ "$n" -eq 0 ]; then
  echo "❌ הסקיל '$WANT' לא נמצא בספרייה."
  exit 1
fi

echo ""
if [ -n "$WANT" ] && [ "$n" -eq 1 ]; then
  echo "✅ הסקיל '$last' הותקן בהצלחה (רק הוא)."
else
  echo "✅ הותקנו $n סקילים."
fi
echo "🔄 הפעילו מחדש את Claude Code (Cmd+Shift+P → Reload Window) כדי שהסקיל ייטען."
