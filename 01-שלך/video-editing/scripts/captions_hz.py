# -*- coding: utf-8 -*-
# Big karaoke Hebrew captions: each word drawn separately via \pos (white always +
# highlight when spoken), RLI-wrapped so RTL punctuation lands on the LEFT. Also masks
# + records beep spans for censored words. Writes OUT.ass and OUT.ass.ce (censor expr).
# usage: python captions_hz.py WORDS.json OUT.ass CY FS CORR.json LAST_END
#   WORDS.json = [{"s":sec,"e":sec,"w":"word"}...] (word-level, segment-relative)
#   CORR.json  = {"corr":{idx:text}, "drops":[idx], "repl":{"exactword":"replacement"}}  (or "-")
#   HIGHLIGHT env = ASS &HBBGGRR& color for the spoken word (default pink)
import json, sys, os, re
from PIL import ImageFont
SK=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
words=json.load(open(sys.argv[1])); out=sys.argv[2]; CY=int(sys.argv[3]); FS=int(sys.argv[4])
corr={}; drops=set(); repl={}; last_end=None
if len(sys.argv)>5 and sys.argv[5]!="-":
    c=json.load(open(sys.argv[5])); corr={int(k):v for k,v in c.get("corr",{}).items()}; drops=set(c.get("drops",[])); repl=c.get("repl",{})
if len(sys.argv)>6 and sys.argv[6]!="-": last_end=float(sys.argv[6])
if last_end is None: last_end=words[-1]["e"]+0.4
RLI="⁧"; PDI="⁩"; CX=540; MAXW=1000
HL=os.environ.get("HIGHLIGHT","&HAA37FF&")            # pink; yellow="&H00E5FF&"
font=ImageFont.truetype(os.path.join(SK,"fonts","Arial Bold.ttf"),FS); SP=font.getlength(" ")
# words Facebook/Meta dislike -> beep audio + mask text (edit as needed)
CENSOR_SUB=["סקס","זיין","זיינ","זיון","זיוני","זונ","אורגי","פאק","מזדיי","תזיי","לזיי","נזדיי","בתחת","פורנו"]
WHITELIST=["זייף","מזון","איזון","מזונ","סקסי","מתחת","תחתונ","תחתי"]
def hebonly(s): return re.sub(r"[^֐-׿]","",s)
def t(s):
    if s<0:s=0
    return f"{int(s//3600)}:{int((s%3600)//60):02d}:{s%60:05.2f}"
HEADER=f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Cap, Arial, {FS}, &H00FFFFFF, &H00FFFFFF, &H00000000, &H00000000, -1, 0, 0, 0, 100, 100, 0, 0, 1, 8, 3, 5, 0, 0, 0, 1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
def endp(s): return s.rstrip()[-1:] in ".?!,"
spans=[]; toks=[]
for i,w in enumerate(words):
    if i in drops: continue
    tx=corr.get(i,w["w"]).strip()
    core=tx.rstrip(".,?!:")
    if core in repl: tx=repl[core]+tx[len(core):]     # exact-token replacement (safe)
    ct=hebonly(tx)
    if ct and not any(x in ct for x in WHITELIST) and any(s in ct for s in CENSOR_SUB):
        trail="".join(c for c in tx if c in ".,?!:"); tx=ct[0]+"*"*min(max(len(ct)-1,2),3)+trail
        spans.append((w["s"],w["e"]))
    if tx: toks.append((i,tx))
open(out+".ce","w").write("+".join(f"between(t,{max(0,s-0.03):.2f},{e+0.08:.2f})" for s,e in spans))
# group into rolling lines of <=3 words (break on punctuation or a >0.4s gap)
lines=[]; cur=[]
for n,(i,tx) in enumerate(toks):
    cur.append((i,tx))
    gap=(words[toks[n+1][0]]["s"]-words[i]["e"]) if n+1<len(toks) else 99
    if endp(tx) or len(cur)>=3 or gap>0.4: lines.append(cur); cur=[]
if cur: lines.append(cur)
ev=[]
for li,line in enumerate(lines):
    hold=words[lines[li+1][0][0]]["s"] if li+1<len(lines) else last_end
    texts=[x for _,x in line]; wds=[font.getlength(x) for x in texts]; total=sum(wds)+SP*(len(texts)-1)
    f=min(1.0,MAXW/total) if total>0 else 1.0; wds=[x*f for x in wds]; sp=SP*f; total*=f
    sc="" if f>=0.999 else f"\\fscx{f*100:.1f}\\fscy{f*100:.1f}"; xr=CX+total/2; ls=words[line[0][0]]["s"]
    for j,(idx,tx) in enumerate(line):
        cx=xr-(sum(wds[:j])+sp*j)-wds[j]/2
        ev.append((0,ls,hold,f"{{\\an5\\pos({cx:.1f},{CY}){sc}\\q2}}{RLI}{tx}{PDI}"))
        hs=words[idx]["s"]; he=words[line[j+1][0]]["s"] if j+1<len(line) else min(hold,words[idx]["e"]+0.35)
        ev.append((1,hs,he,f"{{\\an5\\pos({cx:.1f},{CY}){sc}\\q2\\1c{HL}}}{RLI}{tx}{PDI}"))
open(out,"w",encoding="utf-8").write(HEADER+"".join(f"Dialogue: {l},{t(a)},{t(b)},Cap,,0,0,0,,{tx}\n" for l,a,b,tx in ev))
print(f"{len(lines)} lines, {len(spans)} censored -> {out}")
