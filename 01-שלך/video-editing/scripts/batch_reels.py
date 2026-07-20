# -*- coding: utf-8 -*-
# Orchestrate 8 reels from one multi-cam podcast: per clip ->
#   cut-aware face track -> clip audio -> word transcribe -> karaoke captions -> render.
# Runs mlx transcription sequentially (no concurrent Metal jobs). Resumable.
# usage: batch_reels.py CLIPS.json SRC OUTDIR WORKDIR [FACE_MULT] [CY] [FS]
import sys, os, json, subprocess
HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.environ.get("PY") or sys.executable

clips = json.load(open(sys.argv[1]))
SRC, OUTDIR, WORK = sys.argv[2], sys.argv[3], sys.argv[4]
FACE_MULT = sys.argv[5] if len(sys.argv) > 5 else "2.1"
CY = sys.argv[6] if len(sys.argv) > 6 else "1540"
FS = sys.argv[7] if len(sys.argv) > 7 else "140"
os.makedirs(OUTDIR, exist_ok=True); os.makedirs(WORK, exist_ok=True)
FF = os.environ.get("FFMPEG") or "ffmpeg"

def run(cmd, **kw):
    r = subprocess.run(cmd, **kw)
    if r.returncode != 0:
        raise SystemExit(f"FAILED: {' '.join(map(str,cmd))}")

for c in clips:
    n = c["name"]; start = float(c["start"]); dur = float(c["dur"])
    tag = c.get("tag", n.split(" ")[0])
    plan = f"{WORK}/plan_{tag}.json"; wav = f"{WORK}/seg_{tag}.wav"
    wj = f"{WORK}/w_{tag}.json"; ass = f"{WORK}/a_{tag}.ass"
    out = f"{OUTDIR}/{n}.mp4"
    print(f"=== {n}  ({start}+{dur}) ===", flush=True)
    # 1) cut-aware track
    run([PY, f"{HERE}/track_clip.py", SRC, str(start), str(dur), plan])
    # 2) clip audio (16k mono for whisper)
    run([FF, "-y", "-ss", str(start), "-t", str(dur), "-i", SRC,
         "-vn", "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le", wav],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    # 3) word transcribe
    run([PY, f"{HERE}/transcribe.py", wav, wj, "words"])
    # 4) captions (censor OFF by default); resolve corr relative to WORK if not absolute
    corr = c.get("corr", "-")
    if corr != "-" and not os.path.isabs(corr):
        corr = os.path.join(WORK, corr)
    cmd = [PY, f"{HERE}/captions.py", wj, ass, CY, FS, corr, str(round(dur-0.4, 2))]
    if c.get("censor"): cmd.append("--censor")
    run(cmd)
    # 5) render
    run([PY, f"{HERE}/render_clip.py", SRC, str(start), str(dur), plan, ass, WORK, out, FACE_MULT])
    print(f"    -> {out}", flush=True)
print("BATCHDONE", flush=True)
