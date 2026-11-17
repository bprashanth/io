"""Build catalog.json from pins.json (what solved), the mirrored files, and measured needs (needs.json)."""
import datetime, hashlib, json, os

ROOT = "/mnt/seagate/silo/idli-catalog"
FILES = os.path.join(ROOT, "files")
WORK = "/mnt/seagate/idli-catalog-work"
pins = json.load(open(f"{WORK}/pins.json"))
needs = json.load(open(f"{WORK}/needs.json")) if os.path.exists(f"{WORK}/needs.json") else {}
man = json.load(open(f"{WORK}/dl/manifest.json"))
HF = "https://huggingface.co"
WS = f"{HF}/Systran/faster-whisper-small/tree/536b0662742c02347bc0e980a01041f333bce120"
WT = f"{HF}/dropbox-dash/faster-whisper-large-v3-turbo/tree/0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf"
NL = f"{HF}/facebook/nllb-200-distilled-600M/tree/f8d333a098d19b4fd9a8b18f94170487ad3f821d"


def src(dl_rel):
    return man[dl_rel]["source"]


# file under files/ -> (name, source, unpack)
M = {
    "fonts/NotoSansDevanagari.ttf": ("Noto Sans Devanagari font (OFL-1.1)", src("fonts/NotoSansDevanagari.ttf"), "none"),
    "fonts/OFL.txt": ("Noto font licence text", src("fonts/OFL.txt"), "none"),
    "models/whisper-small.tar": ("Whisper small, CTranslate2 format", WS, "tar"),
    "models/whisper-large-v3-turbo.tar": ("Whisper large-v3-turbo, CTranslate2 format", WT, "tar"),
    "models/piper/hi_IN-pratham-medium.onnx": ("Piper Hindi voice pratham (medium)",
                                               src("piper-hi_IN-pratham-medium/hi_IN-pratham-medium.onnx"), "none"),
    "models/piper/hi_IN-pratham-medium.onnx.json": ("Piper Hindi voice pratham, settings",
                                                    src("piper-hi_IN-pratham-medium/hi_IN-pratham-medium.onnx.json"), "none"),
    "models/piper/en_US-lessac-medium.onnx": ("Piper English voice lessac (medium)",
                                              src("piper-en_US-lessac-medium/en_US-lessac-medium.onnx"), "none"),
    "models/piper/en_US-lessac-medium.onnx.json": ("Piper English voice lessac, settings",
                                                   src("piper-en_US-lessac-medium/en_US-lessac-medium.onnx.json"), "none"),
    "models/kokoro/kokoro-v1.0.onnx": ("Kokoro v1.0 (82M) ONNX", src("kokoro/kokoro-v1.0.onnx"), "none"),
    "models/kokoro/voices-v1.0.bin": ("Kokoro v1.0 voices", src("kokoro/voices-v1.0.bin"), "none"),
    "models/nllb-200-distilled-600M-ct2-int8.tar": ("NLLB-200 distilled 600M, CTranslate2 int8 (converted by us)", NL, "tar"),
    "models/tessdata/hin.traineddata": ("Tesseract Hindi (tessdata_best 4.1.0)", src("tessdata/hin.traineddata"), "none"),
    "models/tessdata/mar.traineddata": ("Tesseract Marathi (tessdata_best 4.1.0)", src("tessdata/mar.traineddata"), "none"),
    "models/tessdata/eng.traineddata": ("Tesseract English (tessdata_best 4.1.0)", src("tessdata/eng.traineddata"), "none"),
    "models/tessdata/configs/hocr": ("Tesseract hocr output setting", src("tessdata/configs/hocr"), "none"),
    "models/tessdata/configs/tsv": ("Tesseract tsv output setting", src("tessdata/configs/tsv"), "none"),
    "models/tessdata/configs/txt": ("Tesseract txt output setting", src("tessdata/configs/txt"), "none"),
    "models/rapidocr/ch_PP-OCRv5_det_mobile.onnx": ("PP-OCRv5 text finder (mobile)", src("rapidocr/ch_PP-OCRv5_det_mobile.onnx"), "none"),
    "models/rapidocr/devanagari_PP-OCRv5_rec_mobile.onnx": ("PP-OCRv5 Devanagari reader (mobile)",
                                                            src("rapidocr/devanagari_PP-OCRv5_rec_mobile.onnx"), "none"),
    "models/silero/silero_vad.onnx": ("Silero VAD v6.2.1 ONNX", src("silero/silero_vad.onnx"), "none"),
    "models/yamnet/yamnet.onnx": ("YAMNet ONNX (converted by us from Google's TFLite)", src("yamnet/yamnet.tflite"), "none"),
    "models/yamnet/yamnet_class_map.csv": ("YAMNet class names", src("yamnet/yamnet_class_map.csv"), "none"),
    "models/yunet/face_detection_yunet_2023mar.onnx": ("YuNet face finder (2023mar) ONNX",
                                                       src("yunet/face_detection_yunet_2023mar.onnx"), "none"),
}
PIPER = ["models/piper/hi_IN-pratham-medium.onnx", "models/piper/hi_IN-pratham-medium.onnx.json",
         "models/piper/en_US-lessac-medium.onnx", "models/piper/en_US-lessac-medium.onnx.json"]
PIPER_CAUTION = ("The Hindi voice (pratham) is CC-BY-NC-SA-4.0: non-commercial, share-alike. The English voice (lessac) "
                 "was trained on the Blizzard 2013 Lessac data under a research licence. Fine for tests and internal "
                 "work; for public material prefer voice-kokoro (Apache-2.0 voices).")
WHISPER_CAUTION = "Speech is typed out on this computer. Check names and numbers by ear: Whisper can mishear or invent words in long silences."

T = [
 dict(id="media-ffmpeg", name="FFmpeg (video and audio)", pin="media-ffmpeg",
      **{"for": "Cut, join and convert video and audio, shrink clips for WhatsApp, and burn in subtitles (Hindi too)."},
      licence="GPL-2.0-or-later (this conda-forge build includes x264); Noto Sans Devanagari: OFL-1.1",
      cautions=["Burned-in Hindi subtitles need the 'ass' filter with shaping=complex: the plain 'subtitles' filter draws Devanagari unjoined. The example does this.",
                "Some ffmpeg builds have OpenH264 instead of x264; the example picks whichever is there."],
      models=["fonts/NotoSansDevanagari.ttf", "fonts/OFL.txt"], example="examples/media-ffmpeg.py",
      tags=["video", "audio", "subtitles", "hindi", "cut", "convert", "whatsapp"]),
 dict(id="speech-whisper-small", name="Speech to text, quick (Whisper small)", pin="speech-whisper",
      **{"for": "Type out speech quickly: a first pass over many recordings. Hindi, Marathi, English and more."},
      licence="faster-whisper: MIT; Whisper weights: MIT",
      cautions=[WHISPER_CAUTION, "Small is quick but makes more mistakes in Hindi and Marathi than speech-whisper-turbo."],
      models=["models/whisper-small.tar"], example="examples/speech-whisper.py",
      tags=["speech", "transcribe", "hindi", "marathi", "english", "subtitles"]),
 dict(id="speech-whisper-turbo", name="Speech to text, careful (Whisper large-v3-turbo)", pin="speech-whisper",
      **{"for": "Type out speech carefully, for the recordings that matter. Hindi, Marathi, English and more."},
      licence="faster-whisper: MIT; Whisper weights: MIT",
      cautions=[WHISPER_CAUTION, "About twice as slow as small and needs about 2 GB of memory."],
      models=["models/whisper-large-v3-turbo.tar"], example="examples/speech-whisper.py",
      tags=["speech", "transcribe", "hindi", "marathi", "english", "subtitles"]),
 dict(id="voice-piper", name="Text to speech (Piper)", pin="voice-piper",
      **{"for": "Say Hindi or English text out loud into a sound file. Fast, small, works offline."},
      licence="piper-tts: GPL-3.0-or-later; voices: see cautions",
      cautions=[PIPER_CAUTION], models=PIPER, example="examples/voice-piper.py",
      tags=["speech", "voice", "tts", "hindi", "english"]),
 dict(id="voice-kokoro", name="Text to speech (Kokoro)", pin="voice-kokoro",
      **{"for": "Say Hindi or English text out loud in a natural voice. Two women's and two men's Hindi voices."},
      licence="kokoro-onnx: MIT; Kokoro-82M weights and voices: Apache-2.0; phonemizer and espeak-ng: GPL-3.0",
      cautions=["Hindi pronunciation comes from espeak-ng and is sometimes off for names; listen before publishing."],
      models=["models/kokoro/kokoro-v1.0.onnx", "models/kokoro/voices-v1.0.bin"], example="examples/voice-kokoro.py",
      tags=["speech", "voice", "tts", "hindi", "english"]),
 dict(id="translate-nllb", name="Translation (NLLB-200)", pin="translate-nllb",
      **{"for": "Translate text between English, Hindi, Marathi and about 200 other languages, on this computer."},
      licence="NLLB-200 weights: CC-BY-NC-4.0 (non-commercial); ctranslate2: MIT; sentencepiece: Apache-2.0",
      cautions=["Non-commercial licence: fine for an NGO's own reports, not for paid products or services.",
                "Meta publishes these weights only as pytorch_model.bin, a pickle file. We converted it once on our server with ct2-transformers-converter (ctranslate2 4.9.0, transformers 4.57.6, which loads it with torch weights_only) to CTranslate2 int8. Teams get only the converted files: no pickle and no PyTorch.",
                "Have a fluent reader check anything that goes out: names, numbers and negations can slip."],
      models=["models/nllb-200-distilled-600M-ct2-int8.tar"], example="examples/translate-nllb.py",
      tags=["translate", "hindi", "marathi", "english", "text", "docx"]),
 dict(id="ocr-tesseract", name="Text from images (Tesseract) and tables (img2table)", pin="ocr-tesseract",
      **{"for": "Read printed Hindi, Marathi and English from scans and photos, and pull ruled tables into a spreadsheet."},
      licence="Tesseract and tessdata_best: Apache-2.0; img2table: MIT",
      cautions=["Good on clean printed text. Handwriting is poor: try ocr-rapidocr or the 9B's vision.",
                "img2table runs the 'tesseract' program, so run it inside the tool's environment (pixi run).",
                "The configs/ files must sit next to the language files, or table reading finds nothing."],
      models=["models/tessdata/hin.traineddata", "models/tessdata/mar.traineddata", "models/tessdata/eng.traineddata",
              "models/tessdata/configs/hocr", "models/tessdata/configs/tsv", "models/tessdata/configs/txt"],
      example="examples/ocr-tesseract.py", tags=["ocr", "image", "table", "spreadsheet", "hindi", "marathi", "english"]),
 dict(id="ocr-rapidocr", name="Text from photos (RapidOCR, Devanagari)", pin="ocr-rapidocr",
      **{"for": "Read Hindi and Marathi text from phone photos of forms and notices, line by line with a confidence."},
      licence="RapidOCR: Apache-2.0; PaddleOCR PP-OCRv5 models: Apache-2.0",
      cautions=["All model files come from the catalog; nothing is fetched from modelscope.cn at run time.",
                "The line-turning model is off (it flips Devanagari lines), so photos must be the right way up.",
                "Handwriting works only sometimes; check each field."],
      models=["models/rapidocr/ch_PP-OCRv5_det_mobile.onnx", "models/rapidocr/devanagari_PP-OCRv5_rec_mobile.onnx"],
      example="examples/ocr-rapidocr.py", tags=["ocr", "image", "photo", "form", "hindi", "marathi"]),
 dict(id="speech-vad", name="Where people speak (Silero VAD)", pin="speech-vad",
      **{"for": "Find the stretches of a recording where someone speaks, to cut silences or long pauses."},
      licence="Silero VAD: MIT; onnxruntime: MIT", cautions=["Finds speech, not who speaks. Loud music can count as speech."],
      models=["models/silero/silero_vad.onnx"], example="examples/speech-vad.py",
      tags=["speech", "audio", "silence", "cut", "video"]),
 dict(id="sound-classes", name="What kind of sound (YAMNet)", pin="sound-classes",
      **{"for": "Label each half second of a recording as speech, music, quiet or one of 521 sound types."},
      licence="YAMNet: Apache-2.0; onnxruntime: MIT",
      cautions=["We converted Google's YAMNet TFLite (MediaPipe float32) to ONNX with tf2onnx 1.17.0 (opset 17), so it runs on Windows too. On our test it agreed with the TFLite on 22 of 25 windows; the 3 others were near-silent noise.",
                "It knows kinds of sound, not people: it does not recognise anyone."],
      models=["models/yamnet/yamnet.onnx", "models/yamnet/yamnet_class_map.csv"], example="examples/sound-classes.py",
      tags=["audio", "music", "speech", "classify", "video"]),
 dict(id="face-blur", name="Hide faces (YuNet)", pin="face-blur",
      **{"for": "Pixelate faces in photos and videos before sharing. Finds faces without recognising anyone."},
      licence="YuNet model: MIT; OpenCV: Apache-2.0; ffmpeg: GPL-2.0-or-later",
      cautions=["Check the result by eye: small, turned, covered or very blurry faces can be missed.",
                "Hides faces only: name tags, voices, places and clothes can still identify people."],
      models=["models/yunet/face_detection_yunet_2023mar.onnx"], example="examples/face-blur.py",
      tags=["video", "photo", "privacy", "faces", "blur"]),
 dict(id="voice-anonymise", name="Replace a voice (Whisper then Piper)", pin="voice-anonymise",
      **{"for": "Make a speaker unrecognisable by voice: the words are typed out and said again by a synthetic voice."},
      licence="faster-whisper and Whisper: MIT; piper-tts: GPL-3.0-or-later; voices: see voice-piper",
      cautions=["Protects the voice: pitch, timbre, accent and way of speaking are gone. Background sounds are dropped too.",
                "Does not protect the words: names, places and details said aloud stay. Read the transcript before sharing.",
                "Whisper mistakes become wrong words in the new audio. Feelings, laughter and who said what are lost.",
                "Pitch or formant shifting was not chosen: it is easy to undo and keeps the way a person speaks.",
                PIPER_CAUTION],
      models=["models/whisper-large-v3-turbo.tar"] + PIPER, example="examples/voice-anonymise.py",
      tags=["privacy", "speech", "voice", "anonymise", "hindi", "english"]),
 dict(id="office-files", name="Word and Excel files", pin="office-files",
      **{"for": "Read and write .docx and .xlsx files, and work on tables with pandas."},
      licence="python-docx: MIT; openpyxl: MIT; pandas: BSD-3-Clause",
      cautions=["Formulas written with openpyxl are computed when the file is opened in Excel; pandas reads them as empty."],
      models=[], example="examples/office-files.py", tags=["docx", "xlsx", "word", "excel", "spreadsheet", "table"]),
 dict(id="page-server", name="Local web page", pin="page-server",
      **{"for": "Serve a small web page on this computer, for example a voice chatbot page with a microphone button."},
      licence="Python standard library: PSF-2.0",
      cautions=["Listens on 127.0.0.1 only, so other devices on the wifi cannot open it. Do not change that to 0.0.0.0.",
                "Browsers allow the microphone on 127.0.0.1 without https."],
      models=[], example="examples/page-server.py", tags=["page", "web", "chatbot", "voice", "local"]),
]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()


cache = {}
tools = []
for t in T:
    p = pins[t.pop("pin")]
    models = []
    for f in t.pop("models"):
        path = os.path.join(FILES, f)
        if f not in cache:
            cache[f] = (sha(path), os.path.getsize(path))
        name, source, unpack = M[f]
        models.append({"name": name, "file": f, "source": source, "sha256": cache[f][0], "bytes": cache[f][1],
                       "unpack": unpack})
    assert os.path.isfile(os.path.join(FILES, t["example"])), t["example"]
    entry = {"id": t["id"], "name": t["name"], "for": t["for"], "licence": t["licence"], "vetted": "2026-11-17",
             "cautions": t["cautions"],
             "pixi": {"dependencies": p["dependencies"], "pypi-dependencies": p["pypi-dependencies"]},
             "platforms": p["platforms"], "models": models,
             "needs": needs.get(t["id"], {"disk_gb": None, "ram_gb": None, "cores": None, "gpu": False}),
             "example": t["example"], "tags": t["tags"]}
    tools.append(entry)
cat = {"version": 1, "updated": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
       "tools": tools}
tmp = os.path.join(ROOT, "catalog.json.tmp")
with open(tmp, "w", encoding="utf-8") as f:
    json.dump(cat, f, indent=1, ensure_ascii=False)
os.replace(tmp, os.path.join(ROOT, "catalog.json"))
print(len(tools), "tools;", sum(b for _, b in cache.values()) / 1e9, "GB of files")
