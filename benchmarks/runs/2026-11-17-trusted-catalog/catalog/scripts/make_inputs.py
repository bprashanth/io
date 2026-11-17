"""Make the tiny test inputs (run in the testkit env). Speech wavs come from voice-piper beforehand."""
import os, subprocess, sys
import numpy as np
from PIL import Image, ImageDraw
from skimage import data

W = "/mnt/seagate/idli-catalog-work/inputs"
FONT = "/mnt/seagate/idli-catalog-work/installed/fonts/NotoSansDevanagari.ttf"
FF = "ffmpeg"

def esc(t):
    return t.replace(":", "\\:").replace("'", "\\'")

def text_image(path, canvas, items, size=40):
    """items: (x, y, text). Text is drawn by libass (ffmpeg's subtitles filter), which shapes Devanagari properly."""
    base = path + ".base.png"
    canvas.save(base)
    w, h = canvas.size
    ass = path + ".ass"
    ev = "".join(f"Dialogue: 0,0:00:00.00,0:00:05.00,D,,0,0,0,,{{\\an7\\pos({x},{y})}}{t}\n" for x, y, t in items)
    open(ass, "w", encoding="utf-8").write(
        f"[Script Info]\nScriptType: v4.00+\nPlayResX: {w}\nPlayResY: {h}\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, OutlineColour, BorderStyle, Outline, Shadow\n"
        f"Style: D,Noto Sans Devanagari,{size},&H00000000,&H00FFFFFF,1,0,0\n\n[Events]\n"
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n" + ev)
    fonts = os.path.dirname(FONT)
    subprocess.run([FF, "-y", "-loglevel", "error", "-i", base, "-vf", f"ass={ass}:fontsdir={fonts}:shaping=complex",
                    "-frames:v", "1", path], check=True)
    os.remove(base); os.remove(ass)

# 1. a table of three columns
rows = [("नाम", "गाँव", "उम्र"), ("सीता देवी", "रामपुर", "34"), ("मोहन लाल", "शिवगढ़", "52"), ("गीता", "नंदपुर", "27")]
cw, rh = 300, 90
img = Image.new("RGB", (cw * 3 + 40, rh * len(rows) + 40), "white")
d = ImageDraw.Draw(img)
for r in range(len(rows) + 1):
    d.line([(20, 20 + r * rh), (20 + 3 * cw, 20 + r * rh)], fill="black", width=3)
for c in range(4):
    d.line([(20 + c * cw, 20), (20 + c * cw, 20 + len(rows) * rh)], fill="black", width=3)
items = [(40 + c * cw, 35 + r * rh, t) for r, row in enumerate(rows) for c, t in enumerate(row)]
text_image(f"{W}/table_hi.png", img, items)

# 2. a short paragraph in Hindi and Marathi
lines = ["आज की बैठक में बीस किसान आए।", "पानी की टंकी अगले महीने बनेगी।", "आमच्या गावात शाळा आहे."]
img = Image.new("RGB", (1000, 80 * len(lines) + 40), "white")
text_image(f"{W}/text_hi.png", img, [(30, 25 + i * 80, t) for i, t in enumerate(lines)])

# 3. a face: scikit-image's astronaut (public domain, NASA), as a photo and a 4 s video with Hindi speech
Image.fromarray(data.astronaut()).save(f"{W}/face.png")
subprocess.run([FF, "-y", "-loglevel", "error", "-loop", "1", "-i", f"{W}/face.png", "-i", f"{W}/hi_speech.wav",
                "-vf", "scale=640:640,zoompan=z='1+0.002*on':d=1:s=640x640:fps=25", "-t", "4", "-c:v", "libx264",
                "-pix_fmt", "yuv420p", "-c:a", "aac", f"{W}/face.mp4"], check=True)

# 4. sound: 2 s quiet, Hindi speech, 1 s quiet, 4 s of music (a few chords), all 16 kHz mono
sr = 16000
t = np.arange(int(sr * 4)) / sr
notes = [261.6, 329.6, 392.0, 523.3]
music = sum(np.sin(2 * np.pi * f * t) * (0.5 + 0.5 * np.sin(2 * np.pi * 2 * t + i)) for i, f in enumerate(notes))
music = (music / np.abs(music).max() * 0.4).astype(np.float32)
subprocess.run([FF, "-y", "-loglevel", "error", "-i", f"{W}/hi_speech.wav", "-ar", str(sr), "-ac", "1", "-f", "f32le",
                f"{W}/speech.f32"], check=True)
speech = np.fromfile(f"{W}/speech.f32", dtype=np.float32)
os.remove(f"{W}/speech.f32")
z = lambda s: np.random.default_rng(0).normal(0, 0.002, int(sr * s)).astype(np.float32)
mix = np.concatenate([z(2), speech, z(1), music])
import wave
with wave.open(f"{W}/mixed.wav", "wb") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(sr)
    w.writeframes((np.clip(mix, -1, 1) * 32767).astype("<i2").tobytes())
print("speech", len(speech) / sr, "s; mixed", len(mix) / sr, "s")

# 5. a subtitle file for the cut
open(f"{W}/subs_hi.srt", "w", encoding="utf-8").write(
    "1\n00:00:00,000 --> 00:00:02,000\nनमस्ते, आज हमारी बैठक है।\n\n2\n00:00:02,000 --> 00:00:04,000\nसभी किसान कागज़ साथ लाएँ।\n")
