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

echo "📥 מוריד את הסקילים של טל..."
git clone --depth 1 "$REPO" "$TMP" >/dev/null 2>&1 || {
  echo "❌ ההורדה נכשלה. ודאו חיבור לאינטרנט."
  exit 1
}

mkdir -p "$DEST"
n=0
while IFS= read -r sk; do
  name="$(basename "$sk")"
  if [ -z "$WANT" ] || [ "$WANT" = "$name" ]; then
    rm -rf "$DEST/$name"
    cp -R "$sk" "$DEST/"
    echo "  ✓ $name"
    n=$((n + 1))
  fi
done < <(find "$TMP" -name SKILL.md -not -path '*/.git/*' -exec dirname {} \;)

rm -rf "$TMP"
if [ "$n" -eq 0 ]; then
  echo "❌ הסקיל '$WANT' לא נמצא."
  exit 1
fi
echo ""
echo "✅ הותקנו $n סקילים. הפעילו מחדש את Claude Code."
