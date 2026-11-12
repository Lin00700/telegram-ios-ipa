#!/usr/bin/env python3
"""Draw a simple 1024px app icon. No third-party image library required."""

import struct
import zlib
from pathlib import Path

WIDTH = 1024


def chunk(tag: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)


def png(pixels: bytes) -> bytes:
    header = struct.pack(">IIBBBBB", WIDTH, WIDTH, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(pixels, 9)) + chunk(b"IEND", b"")


def blend(color, cover):
    return tuple(int(channel * cover) for channel in color)


def main() -> None:
    background = (18, 61, 58)
    paper = (244, 239, 230)
    ink = (18, 61, 58)
    coral = (196, 92, 74)
    rows = bytearray()
    center = WIDTH / 2
    radius = 360
    for y in range(WIDTH):
        rows.append(0)
        for x in range(WIDTH):
            dx = x - center
            dy = y - center
            color = background
            if dx * dx + dy * dy <= radius * radius:
                color = paper
            # Handset body.
            if 390 <= x <= 634 and 300 <= y <= 700:
                color = ink
            # Earpiece and mouthpiece cutouts.
            if 450 <= x <= 574 and 340 <= y <= 390:
                color = paper
            if 450 <= x <= 574 and 610 <= y <= 660:
                color = paper
            # Block bar.
            if 430 <= x <= 700 and 730 <= y <= 790:
                color = coral
            rows.extend(color)
    destination = Path(__file__).resolve().parents[1] / "CallSMSBlocker" / "Assets.xcassets" / "AppIcon.appiconset" / "icon-1024.png"
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(png(bytes(rows)))
    print(destination, destination.stat().st_size)


if __name__ == "__main__":
    main()
