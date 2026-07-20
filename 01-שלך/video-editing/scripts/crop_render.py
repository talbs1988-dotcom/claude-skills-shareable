# -*- coding: utf-8 -*-
# Follow-zoom crop (keeps the subject centered via track.py trajectory) + burn ASS
# captions + keep audio. If <ASS>.ce exists (censor spans), mute+beep those spans.
# usage: python crop_render.py SRC START DUR CW Y0 ASS TRACK.json OUT.mp4
#   env FFMPEG (default "ffmpeg"), fonts auto-found in <skill>/fonts
import cv2, numpy as np, json, sys, subprocess, os
SK=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FF=os.environ.get("FFMPEG","ffmpeg"); FONTS=os.path.join(SK,"fonts")
src=sys.argv[1]; start=float(sys.argv[2]); dur=float(sys.argv[3])
CW=int(sys.argv[4]); Y0=int(sys.argv[5]); ass=sys.argv[6]; trackjson=sys.argv[7]; out=sys.argv[8]
tr=json.load(open(trackjson)); ts=np.array(tr["ts"],float); xs=np.array(tr["x"],float); W=tr["W"]; H=tr["H"]
def medfilt(a,k=9):
    k|=1; p=k//2; ap=np.pad(a,(p,p),'edge'); return np.array([np.median(ap[i:i+k]) for i in range(len(a))])
def smooth(a,win):
    win=max(1,win|1); return np.convolve(np.pad(a,(win//2,win//2),'edge'),np.ones(win)/win,'valid')[:len(a)]
xs=smooth(medfilt(xs,9),21)   # median kills spikes, moving-average -> stable "locked" pan
CH=int(round(CW*16/9)); Y0=max(0,min(Y0,H-CH))
cap=cv2.VideoCapture(src); fps=cap.get(cv2.CAP_PROP_FPS) or 30
cap.set(cv2.CAP_PROP_POS_FRAMES,int(round(start*fps))); nframes=int(round(dur*fps))
ce=""
if os.path.exists(ass+".ce"): ce=open(ass+".ce").read().strip()
inputs=["-f","rawvideo","-pix_fmt","bgr24","-s","1080x1920","-r",f"{fps:.5f}","-i","-","-ss",str(start),"-t",str(dur),"-i",src]
if ce:
    inputs+=["-f","lavfi","-t",str(dur),"-i","sine=frequency=1000:sample_rate=48000"]
    fc=(f"[0:v]subtitles='{ass}':fontsdir='{FONTS}'[v];"
        f"[1:a]volume=volume='if({ce},0,1)':eval=frame,aformat=sample_fmts=fltp:channel_layouts=stereo[vo];"
        f"[2:a]volume=volume='if({ce},0.33,0)':eval=frame,aformat=sample_fmts=fltp:channel_layouts=stereo[bp];"
        f"[vo][bp]amix=inputs=2:duration=first:normalize=0[a]"); amap=["-map","[v]","-map","[a]"]
else:
    fc=f"[0:v]subtitles='{ass}':fontsdir='{FONTS}'[v]"; amap=["-map","[v]","-map","1:a"]
p=subprocess.Popen([FF,"-y"]+inputs+["-filter_complex",fc]+amap+
    ["-c:v","libx264","-preset","medium","-crf","20","-pix_fmt","yuv420p","-c:a","aac","-b:a","160k","-movflags","+faststart",out],
    stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for k in range(nframes):
    ok,fr=cap.read()
    if not ok: break
    x=float(np.interp(start+k/fps,ts,xs)); x0=int(np.clip(round(x-CW/2),0,W-CW))
    crop=cv2.resize(fr[Y0:Y0+CH, x0:x0+CW],(1080,1920),interpolation=cv2.INTER_LANCZOS4)
    p.stdin.write(crop.tobytes())
p.stdin.close(); p.wait(); cap.release(); print("done",out)
