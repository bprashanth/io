"""Check that face-blur changed the face and little else (runs inside the face-blur environment).

Usage: python check_face.py ORIGINAL HIDDEN   (two images, or two videos: the middle frame of each is compared)
The astronaut's face sits at about x 170-290, y 70-210 of the 512 px photo (scaled for the 640 px clip).
"""
import json
import shutil
import subprocess
import sys

import cv2
import numpy as np


def frame(p):
    img = cv2.imread(p)
    if img is not None:
        return img
    cap = cv2.VideoCapture(p)
    n = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    cap.set(cv2.CAP_PROP_POS_FRAMES, max(n // 2, 0))
    ok, img = cap.read()
    if not ok:
        sys.exit(f'cannot read a frame of {p}')
    return img


a, b = frame(sys.argv[1]), frame(sys.argv[2])
if a.shape != b.shape:
    sys.exit(f'sizes differ: {a.shape} {b.shape}')
s = a.shape[1] / 512
fx0, fx1, fy0, fy1 = int(185 * s), int(275 * s), int(90 * s), int(190 * s)  # inside the face
diff = np.abs(a.astype(int) - b.astype(int)).mean(axis=2)
face = diff[fy0:fy1, fx0:fx1].mean()
mask = np.ones(diff.shape, bool)
mask[int(40 * s):int(260 * s), int(130 * s):int(330 * s)] = False  # well outside the face box
rest = diff[mask].mean()
out = {'face_diff': round(float(face), 2), 'rest_diff': round(float(rest), 2)}
video = sys.argv[2].lower().endswith('.mp4')
ok = face > 8 and rest < (6 if video else 3)  # video frames carry some re-encoding noise
if video:
    ff = shutil.which('ffprobe')
    streams = subprocess.run([ff, '-v', 'error', '-show_entries', 'stream=codec_type', '-of', 'json', sys.argv[2]],
                             capture_output=True, text=True).stdout if ff else '{}'
    kinds = [x.get('codec_type') for x in json.loads(streams or '{}').get('streams', [])]
    out['streams'] = kinds
    ok = ok and 'audio' in kinds and 'video' in kinds
print(json.dumps(out), 'OK' if ok else 'FAIL')
sys.exit(0 if ok else 1)
