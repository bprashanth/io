"""voice-kokoro: speak Hindi or English text into a .wav file with Kokoro, on this computer.

Usage: python voice-kokoro.py "TEXT" OUT.wav [VOICE=hf_alpha] [LANG=hi]
Hindi voices: hf_alpha, hf_beta (women), hm_omega, hm_psi (men). English: af_heart, am_michael and more (lang en-us).
The model files are $IDLI_FILES/models/kokoro/kokoro-v1.0.onnx and voices-v1.0.bin.
"""
import os
import sys
import time

import soundfile as sf
from kokoro_onnx import Kokoro

text, out = sys.argv[1], sys.argv[2]
voice = sys.argv[3] if len(sys.argv) > 3 else "hf_alpha"
lang = sys.argv[4] if len(sys.argv) > 4 else "hi"
d = os.path.join(os.environ.get("IDLI_FILES", "."), "models", "kokoro")
t = time.time()
k = Kokoro(os.path.join(d, "kokoro-v1.0.onnx"), os.path.join(d, "voices-v1.0.bin"))
samples, rate = k.create(text, voice=voice, speed=1.0, lang=lang)
sf.write(out, samples, rate)
print("wrote", out, f"{len(samples) / rate:.1f} s of speech in {time.time() - t:.1f} s")
