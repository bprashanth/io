"""media-ffmpeg: cut a clip, burn Hindi subtitles into it, and make it small enough for WhatsApp.

Usage: python media-ffmpeg.py IN.mp4 SUBS.srt OUT.mp4 [START_S END_S]
SUBS.srt is timed from the start of the cut. The Devanagari font comes from the catalog:
$IDLI_FILES/fonts/NotoSansDevanagari.ttf (IDLI_FILES is the local copy of the catalog's files/ folder).
Hindi needs the 'ass' filter with shaping=complex: the plain 'subtitles' filter draws Devanagari unjoined.
"""
import os
import re
import shutil
import subprocess
import sys

src, srt, out = sys.argv[1:4]
cut = ["-ss", sys.argv[4], "-to", sys.argv[5]] if len(sys.argv) > 5 else []
fonts = os.path.join(os.environ.get("IDLI_FILES", "."), "fonts")
ffmpeg = shutil.which("ffmpeg")
encoders = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
if " libx264 " in encoders:
    h264 = ["-c:v", "libx264", "-preset", "veryfast", "-crf", "28"]
else:  # some ffmpeg builds carry only OpenH264
    h264 = ["-c:v", "libopenh264", "-b:v", "1M"]


def esc(p):  # paths inside an ffmpeg filter need '\', ':' and quotes escaped
    return p.replace("\\", "/").replace(":", "\\:").replace("'", "\\'")


# 1. SRT to ASS, with the Devanagari font in the style.
ass = out + ".ass"
subprocess.run([ffmpeg, "-y", "-loglevel", "error", "-i", srt, ass], check=True)
with open(ass, encoding="utf-8") as f:
    text = f.read()
text = re.sub(r"^(Style: Default,)[^,]*,[^,]*,", r"\1Noto Sans Devanagari,22,", text, flags=re.M)
with open(ass, "w", encoding="utf-8") as f:
    f.write(text)
# 2. 720p at most, subtitles drawn by libass with complex shaping, H.264 video and AAC sound.
vf = f"scale='min(1280,iw)':-2,ass='{esc(ass)}':fontsdir='{esc(fonts)}':shaping=complex"
subprocess.run([ffmpeg, "-y", "-loglevel", "error"] + cut + ["-i", src, "-vf", vf] + h264 +
               ["-c:a", "aac", "-b:a", "96k", "-movflags", "+faststart", out], check=True)
os.remove(ass)
print("wrote", out, os.path.getsize(out), "bytes")
