"""speech-whisper-small / speech-whisper-turbo: type out speech (Hindi, Marathi, English and more) on this computer.

Usage: python speech-whisper.py AUDIO [LANG=hi] [MODEL=whisper-small|whisper-large-v3-turbo] [OUT.srt]
The model folder is $IDLI_FILES/models/<MODEL>/ (the catalog's .tar unpacked next to itself).
"""
import os
import sys
import time

from faster_whisper import WhisperModel

audio = sys.argv[1]
lang = sys.argv[2] if len(sys.argv) > 2 else "hi"
name = sys.argv[3] if len(sys.argv) > 3 else "whisper-small"
srt = sys.argv[4] if len(sys.argv) > 4 else None
model_dir = os.path.join(os.environ.get("IDLI_FILES", "."), "models", name)

t = time.time()
model = WhisperModel(model_dir, device="cpu", compute_type="int8", cpu_threads=min(8, os.cpu_count() or 4))
segments, info = model.transcribe(audio, language=lang, beam_size=5, vad_filter=True)


def ts(s):
    return f"{int(s // 3600):02}:{int(s % 3600 // 60):02}:{int(s % 60):02},{int(s * 1000 % 1000):03}"


lines = []
for i, seg in enumerate(segments, 1):
    print(f"[{seg.start:6.1f} - {seg.end:6.1f}] {seg.text.strip()}")
    lines.append(f"{i}\n{ts(seg.start)} --> {ts(seg.end)}\n{seg.text.strip()}\n")
if srt:
    with open(srt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
print(f"{info.duration:.1f} s of audio in {time.time() - t:.1f} s")
