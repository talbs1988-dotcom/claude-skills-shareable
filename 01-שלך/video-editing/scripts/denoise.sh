#!/bin/bash
# Clean vehicle/background noise from a talking video (keeps the voice natural) and
# optionally burn captions. RNN denoise (arnndn) + low-rumble cut + loudness normalise.
# Keeps native resolution (small file). Verified to drop background 15-18 dB in pauses.
#   usage: denoise.sh SRC OUT [ASS]     env FFMPEG (default ffmpeg), FONTS
set -e
SKILL="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")/.." && pwd)"
FF="${FFMPEG:-ffmpeg}"; FONTS="${FONTS:-$SKILL/fonts}"; MODEL="$SKILL/models/bd.rnnn"
SRC="$1"; OUT="$2"; ASS="$3"
AUD="aformat=channel_layouts=mono,highpass=f=80,arnndn=m=$MODEL:mix=0.9,loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"
if [ -n "$ASS" ]; then
  "$FF" -y -i "$SRC" -filter_complex "[0:v]setsar=1,fps=30,subtitles='${ASS}':fontsdir='${FONTS}',format=yuv420p[v];[0:a]${AUD}[a]" \
    -map "[v]" -map "[a]" -c:v libx264 -preset medium -crf 21 -pix_fmt yuv420p -c:a aac -b:a 160k -movflags +faststart "$OUT" -loglevel error
else
  "$FF" -y -i "$SRC" -af "$AUD" -c:v copy -c:a aac -b:a 160k "$OUT" -loglevel error
fi
echo "denoised -> $OUT"
# mix=0.9 is a strong-but-natural clean. Lower to ~0.8 for gentler, raise toward 1.0 for max.
