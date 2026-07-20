# -*- coding: utf-8 -*-
# Hebrew word-level transcription with mlx-whisper (Apple Silicon). Feed a WAV/MP4.
# usage: python transcribe.py AUDIO_OR_VIDEO OUT.json [words|segments]
#   words   -> [{"s","e","w"}]  (for karaoke captions)
#   segments-> [{"start","end","text"}] (for finding strong moments)  + prints [mm:ss] text
import sys, json
import mlx_whisper
src=sys.argv[1]; out=sys.argv[2]; mode=sys.argv[3] if len(sys.argv)>3 else "words"
r=mlx_whisper.transcribe(src, path_or_hf_repo="mlx-community/whisper-large-v3-turbo",
                         language="he", word_timestamps=(mode=="words"), verbose=False,
                         condition_on_previous_text=False)
if mode=="words":
    w=[{"s":round(x["start"],2),"e":round(x["end"],2),"w":x["word"].strip()}
       for s in r["segments"] for x in s.get("words",[])]
    json.dump(w,open(out,"w"),ensure_ascii=False); print(len(w),"words")
else:
    segs=[{"start":round(s["start"],2),"end":round(s["end"],2),"text":s["text"].strip()} for s in r["segments"]]
    json.dump(segs,open(out,"w"),ensure_ascii=False)
    def f(t): return f"{int(t//60):02d}:{int(t%60):02d}"
    for s in segs:
        if s["text"] and "taką" not in s["text"]: print(f"[{f(s['start'])}] {s['text']}")
# NOTE: whisper sometimes hallucinates ("taką"/"ид"/English) on a hard/long stretch.
# Fix by re-transcribing THAT window in ~10s chunks (chunking breaks the loop).
