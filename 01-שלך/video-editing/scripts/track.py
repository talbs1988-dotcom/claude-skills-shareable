# -*- coding: utf-8 -*-
# Track the speaker's FACE (YuNet) for a stable centered zoom; fall back to
# MobileNet-SSD person bbox when no face. Static camera assumed.
# Output: JSON {fps,W,H,ts[],x[],face_y}  used later by crop_render.py to follow the subject.
# usage: python track.py SRC_VIDEO OUT.json [DRAW.jpg CW]
import cv2, numpy as np, sys, json, os
SK=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
M=os.path.join(SK,"models")
src=sys.argv[1]; outjson=sys.argv[2]; draw=sys.argv[3] if len(sys.argv)>3 else None
cap=cv2.VideoCapture(src); fps=cap.get(cv2.CAP_PROP_FPS) or 30
W=int(cap.get(3)); H=int(cap.get(4))
fd=cv2.FaceDetectorYN.create(os.path.join(M,"yunet.onnx"),"",(W,H),score_threshold=0.5); fd.setInputSize((W,H))
net=cv2.dnn.readNetFromCaffe(os.path.join(M,"MobileNetSSD_deploy.prototxt"),os.path.join(M,"MobileNetSSD_deploy.caffemodel"))
step=max(1,int(round(fps/5))); prev=W/2
ts=[]; xs=[]; fys=[]; i=0
def person_cx(fr):
    blob=cv2.dnn.blobFromImage(cv2.resize(fr,(300,300)),0.007843,(300,300),127.5)
    net.setInput(blob); det=net.forward(); best=None
    for k in range(det.shape[2]):
        if int(det[0,0,k,1])==15 and det[0,0,k,2]>0.35:
            x1,_,x2,_=det[0,0,k,3:7]*[W,H,W,H]; c=(x1+x2)/2
            if best is None or abs(c-prev)<abs(best-prev): best=c
    return best
while True:
    ok,fr=cap.read()
    if not ok: break
    if i%step==0:
        n,faces=fd.detect(fr); cx=None; fy=None
        if faces is not None and len(faces):
            fx,fy=min([(f[0]+f[2]/2,f[1]+f[3]/2) for f in faces],key=lambda p:abs(p[0]-prev)); cx=float(fx)
        if cx is None: cx=person_cx(fr)
        if cx is not None: prev=cx
        ts.append(round(i/fps,2)); xs.append(cx); fys.append(fy)
    i+=1
cap.release()
last=None
for k in range(len(xs)):
    xs[k]=xs[k] if xs[k] is not None else last; last=xs[k] if xs[k] is not None else last
last=None
for k in range(len(xs)-1,-1,-1):
    xs[k]=xs[k] if xs[k] is not None else last; last=xs[k] if xs[k] is not None else last
xs=[(v if v is not None else W/2) for v in xs]
fyv=[f for f in fys if f is not None]; face_y=float(np.median(fyv)) if fyv else 400
json.dump({"fps":fps,"W":W,"H":H,"ts":ts,"x":[round(float(v),1) for v in xs],"face_y":face_y},open(outjson,"w"))
p5,p50,p95=np.percentile(xs,[5,50,95]); print(f"samples {len(ts)} face-hit {len(fyv)}/{len(ts)} x p5/p50/p95={p5:.0f}/{p50:.0f}/{p95:.0f} face_y~{face_y:.0f}")
if draw:
    CW=int(sys.argv[4]) if len(sys.argv)>4 else 410; CH=int(round(CW*16/9))
    xa=np.array(xs,float); win=15; xs_s=np.convolve(np.pad(xa,(win//2,win//2),'edge'),np.ones(win)/win,'valid')[:len(xa)]
    y0=int(np.clip(face_y-265,0,H-CH)); cap=cv2.VideoCapture(src); shots=[]
    for f in [0.05,0.25,0.45,0.65,0.85]:
        st=ts[int(len(ts)*f)]; cap.set(cv2.CAP_PROP_POS_FRAMES,int(st*fps)); ok,fr=cap.read()
        if not ok: continue
        xi=float(np.interp(st,ts,xs_s)); x0=int(np.clip(xi-CW/2,0,W-CW))
        cv2.rectangle(fr,(x0,y0),(x0+CW,y0+CH),(255,0,255),4); shots.append(cv2.resize(fr,(180,320)))
    cv2.imwrite(draw,cv2.hconcat(shots)); print("drew",draw,"y0",y0)
