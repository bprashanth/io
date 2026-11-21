"""speech-vad: find where people speak in a recording (Silero VAD), so silences can be cut.

Usage: python speech-vad.py AUDIO.wav [THRESHOLD=0.5]
AUDIO.wav must be 16 kHz mono 16-bit (ffmpeg -i in.mp4 -ar 16000 -ac 1 out.wav).
Prints speech stretches in seconds. The model is $IDLI_FILES/models/silero/silero_vad.onnx.
"""
import os
import sys
import wave

import numpy as np
import onnxruntime as ort

path = sys.argv[1]
threshold = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
model = os.path.join(os.environ.get("IDLI_FILES", "."), "models", "silero", "silero_vad.onnx")
with wave.open(path) as w:
    assert w.getframerate() == 16000 and w.getnchannels() == 1 and w.getsampwidth() == 2, "need 16 kHz mono 16-bit"
    x = np.frombuffer(w.readframes(w.getnframes()), "<i2").astype(np.float32) / 32768

so = ort.SessionOptions()
so.intra_op_num_threads = 1
s = ort.InferenceSession(model, so, providers=["CPUExecutionProvider"])
state = np.zeros((2, 1, 128), np.float32)
ctx = np.zeros((1, 64), np.float32)  # the model expects the last 64 samples before each 512-sample window
sr = np.array(16000, dtype=np.int64)
probs = []
for i in range(0, len(x) - 511, 512):
    chunk = x[i:i + 512].reshape(1, -1)
    out, state = s.run(None, {"input": np.concatenate([ctx, chunk], 1), "state": state, "sr": sr})
    ctx = chunk[:, -64:]
    probs.append(float(out[0, 0]))

# Join speech windows; ignore gaps shorter than 0.3 s and stretches shorter than 0.25 s.
step = 512 / 16000
segs, start, quiet = [], None, 0
for i, p in enumerate(probs):
    if p >= threshold:
        start = i if start is None else start
        quiet = 0
    elif start is not None:
        quiet += 1
        if quiet * step >= 0.3:
            segs.append((start * step, (i - quiet + 1) * step))
            start, quiet = None, 0
if start is not None:
    segs.append((start * step, len(probs) * step))
segs = [(a, b) for a, b in segs if b - a >= 0.25]
for a, b in segs:
    print(f"speech {a:6.2f} - {b:6.2f} s")
print(f"{sum(b - a for a, b in segs):.1f} s of speech in {len(x) / 16000:.1f} s")
