# -*- coding: utf-8 -*-
# Big karaoke captions, Hebrew RTL-safe, word-by-word highlight.
# usage: captions.py WORDS.json OUT.ass CY FS [CORR.json|-] [LAST_END|-] [--censor]
#   WORDS.json : [{"s":start,"e":end,"w":"word"}, ...]
#   CY,FS      : caption vertical center (px in 1920) and font size
#   CORR.json  : {"corr":{idx:text}, "drops":[idx], "repl":{token:text}} (optional)
#   LAST_END   : when the last line should disappear (optional)
#   --censor   : enable auto-mask of explicit Hebrew words (default OFF)
import json, sys, os, re
from PIL import ImageFont
import os as _os
FONT_TTF = _os.path.join(_os.path.dirname(_os.path.dirname(_os.path.abspath(__file__))), "fonts", "Arial Bold.ttf")

args = [a for a in sys.argv[1:] if a != "--censor"]
CENSOR = "--censor" in sys.argv
words = json.load(open(args[0])); out = args[1]
CY = int(args[2]); FS = int(args[3])
corr = {}; drops = set(); last_end = None; repl = {}
if len(args) > 4 and args[4] != "-":
    c = json.load(open(args[4])); corr = {int(k): v for k, v in c.get("corr", {}).items()}
    drops = set(c.get("drops", [])); repl = c.get("repl", {})
if len(args) > 5 and args[5] != "-":
    last_end = float(args[5])
if last_end is None:
    last_end = words[-1]["e"] + 0.4

RLI = "⁧"; PDI = "⁩"; CX = 540; MAXW = 1000
HL = "&H00DDFF&"   # highlight of spoken word: bright yellow (BBGGRR)
font = ImageFont.truetype(FONT_TTF, FS); SP = font.getlength(" ")

def t(s):
    if s < 0: s = 0
    return f"{int(s//3600)}:{int((s%3600)//60):02d}:{s%60:05.2f}"

HEADER = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap, Arial, {FS}, &H00FFFFFF, &H00FFFFFF, &H00000000, &H64000000, -1, 0, 0, 0, 100, 100, 0, 0, 1, 8, 4, 5, 0, 0, 0, 1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

def endp(s): return s.rstrip()[-1:] in ".?!,"

# Optional explicit-word masking (OFF by default; enable for Meta-safe content)
CENSOR_SUB = ["זיין","זיינ","זיון","זיוני","זונ","אורגי","פאק","מזדיי","תזיי","לזיי","נזדיי"]
WHITELIST  = ["זייף","מזון","איזון","מזונ","מתחת","תחתונ","תחתי"]
def hebonly(s): return re.sub(r"[^֐-׿]", "", s)

spans = []; toks = []
for i, w in enumerate(words):
    if i in drops: continue
    tx = corr.get(i, w["w"]).strip()
    _core = tx.rstrip(".,?!:")
    if _core in repl: tx = repl[_core] + tx[len(_core):]
    if CENSOR:
        ct = hebonly(tx)
        if ct and not any(x in ct for x in WHITELIST) and any(s in ct for s in CENSOR_SUB):
            trail = "".join(c for c in tx if c in ".,?!:")
            tx = ct[0] + "*" * min(max(len(ct)-1, 2), 3) + trail
            spans.append((w["s"], w["e"]))
    if tx: toks.append((i, tx))
ce = "+".join(f"between(t,{max(0,s-0.03):.2f},{e+0.08:.2f})" for s, e in spans)
open(out + ".ce", "w").write(ce)

lines = []; cur = []
for n, (i, tx) in enumerate(toks):
    cur.append((i, tx))
    gap = (words[toks[n+1][0]]["s"] - words[i]["e"]) if n+1 < len(toks) else 99
    if endp(tx) or len(cur) >= 3 or gap > 0.4:
        lines.append(cur); cur = []
if cur: lines.append(cur)

ev = []
for li, line in enumerate(lines):
    hold = words[lines[li+1][0][0]]["s"] if li+1 < len(lines) else last_end
    texts = [x for _, x in line]; wds = [font.getlength(x) for x in texts]
    total = sum(wds) + SP*(len(texts)-1); f = min(1.0, MAXW/total) if total > 0 else 1.0
    wds = [x*f for x in wds]; sp = SP*f; total *= f
    sc = "" if f >= 0.999 else f"\\fscx{f*100:.1f}\\fscy{f*100:.1f}"
    xr = CX + total/2; ls = words[line[0][0]]["s"]
    for j, (idx, tx) in enumerate(line):
        cx = xr - (sum(wds[:j]) + sp*j) - wds[j]/2
        ev.append((0, ls, hold, f"{{\\an5\\pos({cx:.1f},{CY}){sc}\\q2}}{RLI}{tx}{PDI}"))
        hs = words[idx]["s"]; he = words[line[j+1][0]]["s"] if j+1 < len(line) else min(hold, words[idx]["e"]+0.35)
        ev.append((1, hs, he, f"{{\\an5\\pos({cx:.1f},{CY}){sc}\\q2\\1c{HL}}}{RLI}{tx}{PDI}"))
open(out, "w", encoding="utf-8").write(
    HEADER + "".join(f"Dialogue: {l},{t(a)},{t(b)},Cap,,0,0,0,,{tx}\n" for l, a, b, tx in ev))
print(f"{len(lines)} lines -> {out}")
