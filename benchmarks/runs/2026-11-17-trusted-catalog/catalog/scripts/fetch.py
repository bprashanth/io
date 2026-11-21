"""Download upstream files into dl/, verify sha256 against upstream where it publishes one, record a manifest."""
import hashlib, json, os, subprocess, sys, urllib.request

DL = "/mnt/seagate/idli-catalog-work/dl"
MAN = os.path.join(DL, "manifest.json")
HF = "https://huggingface.co"
RS = "v3.10.0"
MS = f"https://www.modelscope.cn/models/RapidAI/RapidOCR/resolve/{RS}/onnx/PP-OCRv5"

def hf(repo, rev, files, dest):
    meta = json.load(urllib.request.urlopen(f"{HF}/api/models/{repo}/revision/{rev}?blobs=true"))
    lfs = {s["rfilename"]: (s.get("lfs") or {}).get("sha256") for s in meta["siblings"]}
    return [(f"{HF}/{repo}/resolve/{rev}/{f}", f"{dest}/{os.path.basename(f)}", lfs.get(f)) for f in files]

ITEMS = []
ITEMS += hf("Systran/faster-whisper-small", "536b0662742c02347bc0e980a01041f333bce120",
            ["config.json", "model.bin", "tokenizer.json", "vocabulary.txt"], "whisper-small")
ITEMS += hf("dropbox-dash/faster-whisper-large-v3-turbo", "0a363e9161cbc7ed1431c9597a8ceaf0c4f78fcf",
            ["config.json", "model.bin", "preprocessor_config.json", "tokenizer.json", "vocabulary.json"], "whisper-large-v3-turbo")
pv = "e9ab671f2a0e50a701b34361136ba3e6a3a9eb0c"
ITEMS += hf("rhasspy/piper-voices", pv, ["hi/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx",
            "hi/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx.json", "hi/hi_IN/pratham/medium/MODEL_CARD"], "piper-hi_IN-pratham-medium")
ITEMS += hf("rhasspy/piper-voices", pv, ["en/en_US/lessac/medium/en_US-lessac-medium.onnx",
            "en/en_US/lessac/medium/en_US-lessac-medium.onnx.json", "en/en_US/lessac/medium/MODEL_CARD"], "piper-en_US-lessac-medium")
ITEMS += hf("facebook/nllb-200-distilled-600M", "f8d333a098d19b4fd9a8b18f94170487ad3f821d",
            ["config.json", "generation_config.json", "pytorch_model.bin", "sentencepiece.bpe.model", "special_tokens_map.json",
             "tokenizer.json", "tokenizer_config.json", "README.md"], "nllb-original")
KO = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
ITEMS += [(f"{KO}/kokoro-v1.0.onnx", "kokoro/kokoro-v1.0.onnx", None), (f"{KO}/voices-v1.0.bin", "kokoro/voices-v1.0.bin", None)]
for l in ("hin", "mar", "eng"):
    ITEMS.append((f"https://github.com/tesseract-ocr/tessdata_best/raw/4.1.0/{l}.traineddata", f"tessdata/{l}.traineddata", None))
for c in ("hocr", "tsv", "txt"):
    ITEMS.append((f"https://github.com/tesseract-ocr/tesseract/raw/5.5.4/tessdata/configs/{c}", f"tessdata/configs/{c}", None))
ITEMS += [(f"{MS}/det/ch_PP-OCRv5_det_mobile.onnx", "rapidocr/ch_PP-OCRv5_det_mobile.onnx", None),
          (f"{MS}/rec/devanagari_PP-OCRv5_rec_mobile.onnx", "rapidocr/devanagari_PP-OCRv5_rec_mobile.onnx",
           "d6f0a906580e3fa6b324a318718f1f31f268b6ea8ef985f91c2012a37f52c91e"),
          (f"{MS}/cls/ch_PP-LCNet_x0_25_textline_ori_cls_mobile.onnx", "rapidocr/ch_PP-LCNet_x0_25_textline_ori_cls_mobile.onnx",
           "54379ae5174d026780215fc748a7f31910dee36818e63d49e17dc598ecc82df7")]
ITEMS.append(("https://github.com/snakers4/silero-vad/raw/v6.2.1/src/silero_vad/data/silero_vad.onnx", "silero/silero_vad.onnx", None))
ITEMS.append(("https://storage.googleapis.com/mediapipe-models/audio_classifier/yamnet/float32/1/yamnet.tflite", "yamnet/yamnet.tflite", None))
ITEMS.append(("https://github.com/tensorflow/models/raw/8f3b2e48fff92a7fa8d504908b51a6eb51e868a0/research/audioset/yamnet/yamnet_class_map.csv",
              "yamnet/yamnet_class_map.csv", None))
ITEMS.append(("https://github.com/opencv/opencv_zoo/raw/48b10fa505aeb51fbd127fc60a5c660040e823b7/models/face_detection_yunet/face_detection_yunet_2023mar.onnx",
              "yunet/face_detection_yunet_2023mar.onnx", None))
ITEMS.append(("https://github.com/google/fonts/raw/7af0d90b4d532ffa4b041937b560c6df4e7b1e95/ofl/notosansdevanagari/NotoSansDevanagari%5Bwdth,wght%5D.ttf",
              "fonts/NotoSansDevanagari.ttf", None))
ITEMS.append(("https://github.com/google/fonts/raw/7af0d90b4d532ffa4b041937b560c6df4e7b1e95/ofl/notosansdevanagari/OFL.txt", "fonts/OFL.txt", None))

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 22), b""):
            h.update(b)
    return h.hexdigest()

man = json.load(open(MAN)) if os.path.exists(MAN) else {}
only = sys.argv[1:]
for url, rel, want in ITEMS:
    if only and not any(o in rel for o in only):
        continue
    p = os.path.join(DL, rel)
    if rel in man and os.path.exists(p) and man[rel]["bytes"] == os.path.getsize(p):
        continue
    os.makedirs(os.path.dirname(p), exist_ok=True)
    subprocess.run(["curl", "-sSLf", "--retry", "3", "-o", p + ".part", url], check=True)
    os.replace(p + ".part", p)
    got = sha(p)
    if want and got != want:
        sys.exit(f"SHA MISMATCH {rel}: {got} != {want}")
    man[rel] = {"source": url, "sha256": got, "bytes": os.path.getsize(p), "upstream_sha256_checked": bool(want)}
    json.dump(man, open(MAN, "w"), indent=1)
    print("ok", rel, man[rel]["bytes"], "checked" if want else "recorded", flush=True)
print("done")
