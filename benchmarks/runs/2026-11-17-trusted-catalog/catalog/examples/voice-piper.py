"""voice-piper: speak Hindi or English text into a .wav file, on this computer.

Usage: python voice-piper.py "TEXT" OUT.wav [VOICE=hi_IN-pratham-medium|en_US-lessac-medium]
The voice files are $IDLI_FILES/models/piper/<VOICE>.onnx and <VOICE>.onnx.json.
"""
import os
import sys
import wave

from piper import PiperVoice

text, out = sys.argv[1], sys.argv[2]
voice = sys.argv[3] if len(sys.argv) > 3 else "hi_IN-pratham-medium"
path = os.path.join(os.environ.get("IDLI_FILES", "."), "models", "piper", voice + ".onnx")
v = PiperVoice.load(path)  # reads <voice>.onnx.json next to it
with wave.open(out, "wb") as w:
    v.synthesize_wav(text, w)
with wave.open(out) as w:
    print("wrote", out, f"{w.getnframes() / w.getframerate():.1f} s")
