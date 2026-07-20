#!/bin/bash
# TEASER variant (podcast-style): cut a clip, reframe a fixed vertical crop, burn ASS
# captions, then a 5s branded end-card with music. The music uses its FULL active length
# and ENDS exactly at the video end (quiet intro builds under the clip tail, beat lands on
# the end-card). Use crop_render.py instead when the subject MOVES (needs face-tracking).
#   usage: render_teaser.sh SRC START DUR CROP_X ASS ENDCARD_IMG MUSIC SND_LEN OUT [CENSOR_EXPR]
#     CROP_X = left x of a 608x1080 crop from a 1920x1080 source (tune so face is centred)
#     SND_LEN = seconds of music before its trailing silence (e.g. 13.69)
#   env FFMPEG (default ffmpeg), FONTS (default <skill>/fonts)
set -e
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
FF="${FFMPEG:-ffmpeg}"; FONTS="${FONTS:-$SKILL/fonts}"
SRC="$1"; START="$2"; DUR="$3"; CROPX="$4"; ASS="$5"; IMG="$6"; MUSIC="$7"; SND="$8"; OUT="$9"; CE="${10}"
ENDDUR=5
DELAY=$(awk "BEGIN{printf \"%d\",($DUR+$ENDDUR-$SND)*1000}")
TOTAL=$(awk "BEGIN{printf \"%.2f\",$DUR+$ENDDUR}")
VID="[0:v]setpts=PTS-STARTPTS,crop=608:1080:${CROPX}:0,scale=1080:1920,setsar=1,fps=30,subtitles='${ASS}':fontsdir='${FONTS}',format=yuv420p[cv];[1:v]scale=1080:1080,pad=1080:1920:0:420:color=black,setsar=1,fps=30,format=yuv420p[ev];[cv][ev]concat=n=2:v=1:a=0[outv]"
MUS="[2:a]atrim=0:${SND},asetpts=PTS-STARTPTS,afade=t=in:st=0:d=0.1,afade=t=out:st=$(awk "BEGIN{print $SND-0.4}"):d=0.4,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo,adelay=${DELAY}|${DELAY}[music]"
if [ -n "$CE" ]; then
  "$FF" -y -ss "$START" -t "$DUR" -i "$SRC" -loop 1 -framerate 30 -t "$ENDDUR" -i "$IMG" -i "$MUSIC" -f lavfi -t "$DUR" -i "sine=frequency=1000:sample_rate=48000" \
   -filter_complex "${VID};[0:a]asetpts=PTS-STARTPTS,volume=volume='if(${CE},0,1)':eval=frame,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[voice];${MUS};[3:a]volume=volume='if(${CE},0.33,0)':eval=frame,aformat=sample_fmts=fltp:channel_layouts=stereo[beep];[voice][beep][music]amix=inputs=3:duration=longest:normalize=0[outa]" \
   -map "[outv]" -map "[outa]" -t "$TOTAL" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart "$OUT" -loglevel error
else
  "$FF" -y -ss "$START" -t "$DUR" -i "$SRC" -loop 1 -framerate 30 -t "$ENDDUR" -i "$IMG" -i "$MUSIC" \
   -filter_complex "${VID};[0:a]asetpts=PTS-STARTPTS,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo[voice];${MUS};[voice][music]amix=inputs=2:duration=longest:normalize=0[outa]" \
   -map "[outv]" -map "[outa]" -t "$TOTAL" -c:v libx264 -preset medium -crf 20 -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart "$OUT" -loglevel error
fi
echo "teaser -> $OUT"
