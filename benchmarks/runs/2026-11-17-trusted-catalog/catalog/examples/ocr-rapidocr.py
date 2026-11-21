"""ocr-rapidocr: read Hindi and Marathi (Devanagari) text from photos with RapidOCR (PaddleOCR PP-OCRv5 models).

Usage: python ocr-rapidocr.py IMAGE
Prints each line found with its confidence. All model files are local, nothing is fetched:
$IDLI_FILES/models/rapidocr/ch_PP-OCRv5_det_mobile.onnx (finds text) and devanagari_PP-OCRv5_rec_mobile.onnx (reads it).
Photos must be the right way up: the line-turning step is off.
"""
import os
import sys
import time

from rapidocr import LangDet, LangRec, ModelType, OCRVersion, RapidOCR

d = os.path.join(os.environ.get("IDLI_FILES", "."), "models", "rapidocr")
t = time.time()
engine = RapidOCR(params={
    "Global.log_level": "error",
    "Global.use_cls": False,  # its line-turning model is trained on Chinese and flips Devanagari lines
    "Det.lang_type": LangDet.CH, "Det.ocr_version": OCRVersion.PPOCRV5, "Det.model_type": ModelType.MOBILE,
    "Det.model_path": os.path.join(d, "ch_PP-OCRv5_det_mobile.onnx"),
    "Rec.lang_type": LangRec.DEVANAGARI, "Rec.ocr_version": OCRVersion.PPOCRV5, "Rec.model_type": ModelType.MOBILE,
    "Rec.model_path": os.path.join(d, "devanagari_PP-OCRv5_rec_mobile.onnx"),
})
result = engine(sys.argv[1])
for text, score in zip(result.txts or (), result.scores or ()):
    print(f"{score:.2f}  {text}")
print(f"done in {time.time() - t:.1f} s")
