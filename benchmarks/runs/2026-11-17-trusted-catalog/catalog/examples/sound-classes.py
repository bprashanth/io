"""sound-classes: label each second of a recording as speech, music, quiet and so on (YAMNet, 521 sound classes).

Usage: python sound-classes.py AUDIO.wav
AUDIO.wav must be 16 kHz mono 16-bit (ffmpeg -i in.mp4 -ar 16000 -ac 1 out.wav).
The model is $IDLI_FILES/models/yamnet/yamnet.onnx with yamnet_class_map.csv beside it.
"""
import csv
import os
import sys
import wave

import numpy as np
import onnxruntime as ort

d = os.path.join(os.environ.get("IDLI_FILES", "."), "models", "yamnet")
with open(os.path.join(d, "yamnet_class_map.csv"), encoding="utf-8") as f:
    names = [row[2] for row in csv.reader(f)][1:]
with wave.open(sys.argv[1]) as w:
    assert w.getframerate() == 16000 and w.getnchannels() == 1 and w.getsampwidth() == 2, "need 16 kHz mono 16-bit"
    x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768

so = ort.SessionOptions()
so.intra_op_num_threads = 2
s = ort.InferenceSession(os.path.join(d, "yamnet.onnx"), so, providers=["CPUExecutionProvider"])
inp = s.get_inputs()[0].name
WIN, HOP = 15600, 8000  # 0.975 s windows every 0.5 s
SPEECH = {"Speech", "Child speech, kid speaking", "Conversation", "Narration, monologue"}
for i in range(0, max(1, len(x) - WIN + 1), HOP):
    win = x[i:i + WIN]
    win = np.pad(win, (0, WIN - len(win)))
    scores = s.run(None, {inp: win.astype(np.float32)})[0][0]
    top = scores.argsort()[::-1][:3]
    speech = max(scores[names.index(n)] for n in SPEECH if n in names)
    music = scores[names.index("Music")]
    label = "speech" if speech >= 0.5 else "music" if music >= 0.5 else "other"
    print(f"{i / 16000:6.1f} s  {label:6}  " + ", ".join(f"{names[k]} {scores[k]:.2f}" for k in top))
