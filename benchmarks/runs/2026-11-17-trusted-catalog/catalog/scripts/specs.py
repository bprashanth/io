# Loose specs for the first solve; pinned afterwards from what solved.
SPECS = {
 "media-ffmpeg": ({"python": "3.11.*", "ffmpeg": "*"}, {}),
 "speech-whisper": ({"python": "3.11.*"}, {"faster-whisper": "*"}),
 "voice-piper": ({"python": "3.11.*"}, {"piper-tts": "*"}),
 "voice-kokoro": ({"python": "3.11.*", "pysoundfile": "*"}, {"kokoro-onnx": "*"}),
 "translate-nllb": ({"python": "3.11.*", "sentencepiece": "*"}, {"ctranslate2": "*"}),
 "ocr-tesseract": ({"python": "3.11.*", "tesseract": "*", "pillow": "*", "pandas": "*", "xlsxwriter": "*", "openpyxl": "*"}, {"img2table": "*"}),
 "ocr-rapidocr": ({"python": "3.11.*", "onnxruntime": "*"}, {"rapidocr": "*"}),
 "speech-vad": ({"python": "3.11.*", "numpy": "*", "onnxruntime": "*"}, {}),
 "sound-classes": ({"python": "3.11.*", "numpy": "*", "onnxruntime": "*"}, {}),
 "face-blur": ({"python": "3.11.*", "numpy": "*", "ffmpeg": "*"}, {"opencv-python-headless": "*"}),
 "voice-anonymise": ({"python": "3.11.*", "ffmpeg": "*"}, {"faster-whisper": "*", "piper-tts": "*"}),
 "office-files": ({"python": "3.11.*", "python-docx": "*", "openpyxl": "*", "pandas": "*"}, {}),
 "page-server": ({"python": "3.11.*"}, {}),
}
