import json
W = "/mnt/seagate/idli-catalog-work"
cat = json.load(open("/mnt/seagate/silo/idli-catalog/catalog.json"))
v = json.load(open(f"{W}/verify.json"))
TEST = {"media-ffmpeg": "cut 3.5 s of a 640 px clip and burn Hindi subtitles", "speech-whisper-small": "6.4 s of Hindi speech",
        "speech-whisper-turbo": "6.4 s of Hindi speech", "voice-piper": "one Hindi sentence (6 s of speech)",
        "voice-kokoro": "one Hindi sentence (5 s of speech)", "translate-nllb": "3 English lines into Hindi",
        "ocr-tesseract": "a 4 by 3 Hindi table into .xlsx", "ocr-rapidocr": "3 lines of Hindi and Marathi",
        "speech-vad": "13 s of sound", "sound-classes": "13 s of sound", "face-blur": "4 s video, 100 frames at 640 px",
        "voice-anonymise": "4.6 s of Hindi speech", "office-files": "write and read a .docx and an .xlsx",
        "page-server": "start, load the page, send sound"}
rows = ["| id | For | Platforms | Files | Disk | RAM | Test on the DGX | Time |", "|---|---|---|---|---|---|---|---|"]
for t in cat["tools"]:
    b = sum(m["bytes"] for m in t["models"])
    size = "none" if not b else f"{b / 1e9:.2f} GB" if b >= 1e8 else f"{b / 1e6:.1f} MB"
    plats = ", ".join(t["platforms"])
    n = t["needs"]
    rows.append(f"| `{t['id']}` | {t['for']} | {plats} | {size} | {n['disk_gb']} GB | {n['ram_gb']} GB | "
                f"{TEST[t['id']]} | {v[t['id']]['seconds']} s |")
tail = """

Times are whole runs of the example on the DGX (Grace CPU, 20 cores), including loading the model, with the
network cut. Every tool solved on all four platforms on 2026-11-17.

## Cautions in short

- Non-commercial: `translate-nllb` (NLLB weights CC-BY-NC-4.0) and the Hindi Piper voice in `voice-piper` and
  `voice-anonymise` (CC-BY-NC-SA-4.0). The English Piper voice comes from research-licence data.
- GPL code: ffmpeg (this build), piper-tts, phonemizer and espeak-ng. Fine to install and use. Copying them into
  something we hand out brings GPL terms.
- Converted by us: the NLLB model (from a pickle file to CTranslate2) and YAMNet (from TFLite to ONNX). How is in
  each tool's cautions.
- Privacy tools hide only what they say: `face-blur` hides faces, `voice-anonymise` hides the voice but keeps the
  words. Check results before sharing.

How tools are vetted and how requests are reviewed: `VETTING.md` in the repo at
`benchmarks/runs/2026-11-17-trusted-catalog/catalog/`.
"""
head = open(f"{W}/scripts/readme_head.md").read()
open("/mnt/seagate/silo/idli-catalog/README.md", "w").write(head + "\n" + "\n".join(rows) + tail)
