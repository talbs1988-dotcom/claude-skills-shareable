# -*- coding: utf-8 -*-
# Cut-aware speaker tracker for a multi-cam clip.
# Detects hard cuts (frame diff) and, per continuous shot, locks onto the
# dominant face (largest at the cut, then nearest within the shot). Produces a
# plan of shots [{t0,t1,cx,cy}] in SOURCE pixels so the renderer can center a
# 9:16 crop on the active speaker and SNAP (not glide) at every cut.
# usage: track_clip.py SRC START DUR OUT.json
import sys, json, subprocess, numpy as np, cv2
import os as _os
FF = _os.environ.get("FFMPEG") or "ffmpeg"
FFPROBE = _os.environ.get("FFPROBE") or "ffprobe"
YUNET = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "models", "yunet.onnx")

src, start, dur, out = sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
TRK_W, TRK_H, TRK_FPS = 1280, 720, 10.0
CUT_THRESH = 16.0   # mean abs gray diff (0-255) that counts as a hard cut

meta = json.loads(subprocess.check_output([FFPROBE, "-v", "error", "-select_streams", "v:0",
        "-show_entries", "stream=width,height", "-of", "json", src]))
SW = meta["streams"][0]["width"]; SH = meta["streams"][0]["height"]
sx = SW / TRK_W; sy = SH / TRK_H

p = subprocess.Popen([FF, "-v", "error", "-ss", str(start), "-t", str(dur), "-i", src,
    "-vf", f"scale={TRK_W}:{TRK_H},fps={TRK_FPS}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
    stdout=subprocess.PIPE)
fd = cv2.FaceDetectorYN.create(YUNET, "", (TRK_W, TRK_H), score_threshold=0.6)
fd.setInputSize((TRK_W, TRK_H))
fb = TRK_W * TRK_H * 3

ts = []; xs = []; ys = []; hs = []; cut_flags = []
prev_small = None; locked = None; k = 0
while True:
    buf = p.stdout.read(fb)
    if len(buf) < fb: break
    fr = np.frombuffer(buf, np.uint8).reshape(TRK_H, TRK_W, 3)
    small = cv2.resize(cv2.cvtColor(fr, cv2.COLOR_BGR2GRAY), (64, 36))
    is_cut = False
    if prev_small is not None:
        if np.mean(np.abs(small.astype(np.int16) - prev_small.astype(np.int16))) > CUT_THRESH:
            is_cut = True
    prev_small = small
    n, faces = fd.detect(fr)
    cx = cy = fh = None
    if faces is not None and len(faces):
        cand = [(f[0] + f[2] / 2, f[1] + f[3] / 2, f[3], f[4]) for f in faces]  # cx,cy,h,score
        if is_cut or locked is None:
            best = max(cand, key=lambda c: c[2] * c[3])            # biggest/most confident
        else:
            best = min(cand, key=lambda c: abs(c[0] - locked))     # stay on same speaker
        cx, cy, fh = best[0] * sx, best[1] * sy, best[2] * sy
        locked = best[0]
    ts.append(k / TRK_FPS); xs.append(cx); ys.append(cy); hs.append(fh); cut_flags.append(is_cut)
    k += 1
p.wait()

# Segment into shots at cut flags
bounds = [i for i, c in enumerate(cut_flags) if c]
starts = [0] + bounds; ends = bounds + [len(ts)]
shots = []
def med(vals):
    v = [x for x in vals if x is not None]
    return float(np.median(v)) if v else None
last_cx = SW / 2; last_cy = SH * 0.32; face_hs = []
for a, b in zip(starts, ends):
    if b <= a: continue
    cx = med(xs[a:b]); cy = med(ys[a:b]); fh = med(hs[a:b])
    if cx is None: cx = last_cx
    if cy is None: cy = last_cy
    if fh is not None: face_hs.append(fh)
    last_cx, last_cy = cx, cy
    shots.append({"t0": round(ts[a], 3), "t1": round(ts[b-1] + 1.0/TRK_FPS, 3),
                  "cx": round(cx, 1), "cy": round(cy, 1)})
face_h_med = float(np.median(face_hs)) if face_hs else SH * 0.18

json.dump({"SW": SW, "SH": SH, "dur": dur, "shots": shots,
           "face_h_med": round(face_h_med, 1)}, open(out, "w"))
print(f"{len(shots)} shots, face_h_med={face_h_med:.0f}px, "
      f"cx range {min(s['cx'] for s in shots):.0f}-{max(s['cx'] for s in shots):.0f}")
