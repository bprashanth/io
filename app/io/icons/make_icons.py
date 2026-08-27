#!/usr/bin/env python3

import io
import struct
from pathlib import Path

from PIL import Image


BUILD_DIR = Path(__file__).resolve().parent
SOURCE_PATH = BUILD_DIR / "icon.png"
ICO_PATH = BUILD_DIR / "icon.ico"
ICNS_PATH = BUILD_DIR / "icon.icns"

ICO_SIZES = [(size, size) for size in (16, 24, 32, 48, 64, 128, 256)]
ICNS_IMAGES = (
    (b"ic07", 128),
    (b"ic08", 256),
    (b"ic09", 512),
    (b"ic10", 1024),
    (b"ic11", 32),
    (b"ic12", 64),
    (b"ic13", 256),
    (b"ic14", 512),
)


def png_payload(source: Image.Image, size: int) -> bytes:
    resized = source.resize((size, size), Image.Resampling.LANCZOS)
    buffer = io.BytesIO()
    resized.save(buffer, format="PNG")
    return buffer.getvalue()


def make_ico(source: Image.Image) -> None:
    source.save(ICO_PATH, format="ICO", sizes=ICO_SIZES)


def make_icns(source: Image.Image) -> None:
    entries = []
    for ostype, size in ICNS_IMAGES:
        payload = png_payload(source, size)
        entries.append(ostype + struct.pack(">I", 8 + len(payload)) + payload)

    body = b"".join(entries)
    ICNS_PATH.write_bytes(b"icns" + struct.pack(">I", 8 + len(body)) + body)


def main() -> None:
    with Image.open(SOURCE_PATH) as image:
        source = image.convert("RGB")
        make_ico(source)
        make_icns(source)


if __name__ == "__main__":
    main()
