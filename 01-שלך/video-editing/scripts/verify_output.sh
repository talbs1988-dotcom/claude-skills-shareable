#!/bin/bash
# Automatic QA for rendered clips — runs the measurable part of the "ready" checklist.
#   usage: verify_output.sh CLIP.mp4 [CLIP2.mp4 ...]
#          verify_output.sh DIR            (checks every *.mp4 in DIR)
#   env FFPROBE (default: ffprobe from PATH, then ./.videowork/bin/ffprobe)
# checks per clip: resolution 1080x1920, duration 40-90s (outside = warning), audio stream present
set -u
FP="${FFPROBE:-ffprobe}"
command -v "$FP" >/dev/null 2>&1 || FP="$PWD/.videowork/bin/ffprobe"
command -v "$FP" >/dev/null 2>&1 || { echo "ffprobe לא נמצא - להריץ קודם: bash scripts/setup.sh"; exit 1; }

files=()
for a in "$@"; do
  if [ -d "$a" ]; then
    while IFS= read -r f; do files+=("$f"); done < <(find "$a" -maxdepth 1 -iname '*.mp4' | sort)
  else
    files+=("$a")
  fi
done
[ ${#files[@]} -gt 0 ] || { echo "usage: verify_output.sh CLIP.mp4 [...] | DIR"; exit 1; }

fails=0; warns=0
for f in "${files[@]}"; do
  if [ ! -e "$f" ]; then echo "✗ $f - הקובץ לא קיים"; fails=$((fails+1)); continue; fi
  W=$("$FP" -v error -select_streams v:0 -show_entries stream=width  -of csv=p=0 "$f" 2>/dev/null)
  H=$("$FP" -v error -select_streams v:0 -show_entries stream=height -of csv=p=0 "$f" 2>/dev/null)
  DUR=$("$FP" -v error -show_entries format=duration -of csv=p=0 "$f" 2>/dev/null)
  AUD=$("$FP" -v error -select_streams a:0 -show_entries stream=codec_type -of csv=p=0 "$f" 2>/dev/null)
  name=$(basename "$f"); ok=1; msg=""
  if [ "$W" != "1080" ] || [ "$H" != "1920" ]; then ok=0; msg="$msg רזולוציה ${W:-?}x${H:-?} (צריך 1080x1920);"; fi
  if [ -z "$AUD" ]; then ok=0; msg="$msg אין פס אודיו;"; fi
  durw=""
  if [ -n "$DUR" ] && [ "$DUR" != "N/A" ]; then
    inrange=$(awk -v d="$DUR" 'BEGIN{print (d>=40 && d<=90) ? 1 : 0}')
    [ "$inrange" = "1" ] || durw=" ⚠ אורך $(awk -v d="$DUR" 'BEGIN{printf "%.1f", d}') שניות (מחוץ ל-40-90, לטיזר זה בסדר)"
  else
    ok=0; msg="$msg לא ניתן לקרוא אורך;"
  fi
  if [ $ok = 1 ]; then
    echo "✓ $name - ${W}x${H}, $(awk -v d="$DUR" 'BEGIN{printf "%.1f", d}')s, אודיו תקין$durw"
    [ -n "$durw" ] && warns=$((warns+1))
  else
    echo "✗ $name -$msg$durw"; fails=$((fails+1))
  fi
done
echo ""
echo "סה\"כ: ${#files[@]} קבצים, $fails נכשלו, $warns אזהרות"
[ $fails = 0 ] || exit 1
