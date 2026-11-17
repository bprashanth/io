"""voice-anonymise: replace a speaker's voice with a synthetic one, keeping the words and roughly the timing.

Usage: python voice-anonymise.py IN_AUDIO OUT.wav [LANG=hi] [WHISPER=whisper-large-v3-turbo]
How: Whisper types out each stretch of speech, then a Piper voice says the same words at the same moment.
Protects: the voice itself (pitch, timbre, accent, the way a person speaks); background sounds are dropped too.
Does not protect: the words. Names, places and details said aloud stay. Read the transcript before sharing.
Whisper mistakes become wrong words in the new audio. Feelings, laughter and who-said-what are lost.
Models: $IDLI_FILES/models/<WHISPER>/ and $IDLI_FILES/models/piper/<voice>.onnx (+ .onnx.json).
"""
import os
import sys
import time
import wave

import numpy as np
from faster_whisper import WhisperModel
from piper import PiperVoice

src, out = sys.argv[1], sys.argv[2]
lang = sys.argv[3] if len(sys.argv) > 3 else "hi"
whisper = sys.argv[4] if len(sys.argv) > 4 else "whisper-large-v3-turbo"
files = os.environ.get("IDLI_FILES", ".")
voice = "hi_IN-pratham-medium" if lang in ("hi", "mr") else "en_US-lessac-medium"

t = time.time()
stt = WhisperModel(os.path.join(files, "models", whisper), device="cpu", compute_type="int8",
                   cpu_threads=min(8, os.cpu_count() or 4))
tts = PiperVoice.load(os.path.join(files, "models", "piper", voice + ".onnx"))
rate = tts.config.sample_rate
segments, info = stt.transcribe(src, language=lang, beam_size=5, vad_filter=True)
track = np.zeros(int(info.duration * rate) + rate, dtype=np.int16)
transcript = []
for seg in segments:
    text = seg.text.strip()
    if not text:
        continue
    transcript.append(f"[{seg.start:6.1f}] {text}")
    pcm = np.concatenate([np.frombuffer(c.audio_int16_bytes, dtype=np.int16) for c in tts.synthesize(text)])
    at = int(seg.start * rate)
    if at + len(pcm) > len(track):
        track = np.concatenate([track, np.zeros(at + len(pcm) - len(track), dtype=np.int16)])
    track[at:at + len(pcm)] = pcm  # a later stretch may start before this one ends: it then talks over it
with wave.open(out, "wb") as w:
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(rate)
    w.writeframes(track.tobytes())
print("\n".join(transcript))
print(f"wrote {out}: {len(track) / rate:.1f} s in {time.time() - t:.1f} s")
