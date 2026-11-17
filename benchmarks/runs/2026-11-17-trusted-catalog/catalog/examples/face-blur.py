"""face-blur: hide faces in a photo or a video (OpenCV with the YuNet face finder). Nobody is recognised.

Usage: python face-blur.py IN.(jpg|png|mp4|...) OUT.(jpg|png|mp4) [--boxes]
Faces are pixelated in a box a little larger than the face. Video keeps its sound (ffmpeg).
--boxes also prints where faces were found. The model is $IDLI_FILES/models/yunet/face_detection_yunet_2023mar.onnx.
Check the result by eye: small, turned or covered faces can be missed.
"""
import os
import shutil
import subprocess
import sys
import time

import cv2
import numpy as np

src, out = sys.argv[1], sys.argv[2]
show = "--boxes" in sys.argv
model = os.path.join(os.environ.get("IDLI_FILES", "."), "models", "yunet", "face_detection_yunet_2023mar.onnx")
det = cv2.FaceDetectorYN.create(model, "", (320, 320), score_threshold=0.5, nms_threshold=0.3, top_k=5000)


def faces(img):
    h, w = img.shape[:2]
    scale = min(1.0, 1280 / max(h, w))  # find faces on a copy at most 1280 px wide, for speed
    small = cv2.resize(img, (int(w * scale), int(h * scale))) if scale < 1 else img
    det.setInputSize((small.shape[1], small.shape[0]))
    _, found = det.detect(small)
    return [] if found is None else [tuple(int(v / scale) for v in f[:4]) for f in found]


def hide(img, boxes):
    h, w = img.shape[:2]
    for x, y, bw, bh in boxes:
        x0, y0 = max(0, x - bw // 5), max(0, y - bh // 4)
        x1, y1 = min(w, x + bw + bw // 5), min(h, y + bh + bh // 5)
        roi = img[y0:y1, x0:x1]
        if roi.size:
            tiny = cv2.resize(roi, (8, 8), interpolation=cv2.INTER_AREA)
            img[y0:y1, x0:x1] = cv2.resize(tiny, (x1 - x0, y1 - y0), interpolation=cv2.INTER_NEAREST)
    return img


t = time.time()
img = cv2.imread(src)
if img is not None:  # a photo
    boxes = faces(img)
    cv2.imwrite(out, hide(img, boxes))
    print(len(boxes), "face(s) hidden" + (f": {boxes}" if show else ""), f"in {time.time() - t:.1f} s")
    sys.exit(0)

cap = cv2.VideoCapture(src)
fps = cap.get(cv2.CAP_PROP_FPS) or 25
w, h = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)), int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
ffmpeg = shutil.which("ffmpeg")
enc = subprocess.run([ffmpeg, "-hide_banner", "-encoders"], capture_output=True, text=True).stdout
vcodec = ["-c:v", "libx264", "-crf", "23", "-preset", "veryfast"] if " libx264 " in enc else ["-c:v", "libopenh264"]
p = subprocess.Popen([ffmpeg, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24", "-s", f"{w}x{h}",
                      "-r", str(fps), "-i", "-", "-i", src, "-map", "0:v", "-map", "1:a?", *vcodec,
                      "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", out], stdin=subprocess.PIPE)
recent, frames, total = [], 0, 0
while True:
    ok, frame = cap.read()
    if not ok:
        break
    boxes = faces(frame)
    recent = (recent + [boxes])[-5:]  # also hide where a face was in the last 4 frames, so a missed frame does not show it
    hidden = [b for bs in recent for b in bs]
    p.stdin.write(np.ascontiguousarray(hide(frame, hidden)).tobytes())
    frames += 1
    total += len(boxes)
p.stdin.close()
p.wait()
print(f"{frames} frames, faces found in {total} frame-faces, written to {out} in {time.time() - t:.1f} s")
