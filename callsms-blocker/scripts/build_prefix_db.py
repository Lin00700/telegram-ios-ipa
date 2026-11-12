#!/usr/bin/env python3
"""Compress an MIT-licensed phone.dat into the app's prefix range table.

The upstream README at https://github.com/ls0f/phone states that the database
is MIT licensed. This script does not vendor phone.dat. It writes:

  prefix_ranges.dat     fixed-size ranges the SMS filter can binary-search
  virtual_prefixes.txt  7-digit prefixes for the call-segment picker
  SOURCE.json           checksums and counts

phone.dat layout (little-endian index):
  4 byte ASCII version, 4 byte index offset,
  zero-terminated records "province|city|zip|area",
  9-byte index entries <IIB> = prefix, record offset, carrier type.

Carrier types used by that database: 1 移动, 2 联通, 3 电信,
4 电信虚拟, 5 联通虚拟, 6 移动虚拟, 7 广电.

prefix_ranges.dat layout (little-endian):
  magic b"P7R1"
  version u16 = 1
  province_count u16
    repeated: u8 byte length, UTF-8 name
  area_count u16
    repeated: u8 code length, UTF-8 code, u8 city length, UTF-8 city,
              u16 province index
  range_count u32
    repeated 8-byte records: start u32, length u16, area index u16
    inclusive end prefix = start + length - 1
  crc32 u32 (IEEE) of every preceding byte
"""

from __future__ import annotations

import argparse
import hashlib
import json
import struct
import zlib
from collections import Counter, defaultdict
from pathlib import Path

MAGIC = b"P7R1"
VERSION = 1
VIRTUAL_CARDS = {4, 5, 6}
VIRTUAL_FAMILIES = ("162", "165", "167", "170", "171")
INDEX_SIZE = 9


def normalize_area(raw: str) -> str:
    digits = "".join(ch for ch in raw if ch.isdigit())
    # Upstream has a 5-digit typo "00479" for 锡林郭勒. The real code is 0479.
    if len(digits) == 5 and digits.startswith("00"):
        digits = digits[1:]
    if digits and not digits.startswith("0"):
        digits = "0" + digits
    if len(digits) not in (3, 4):
        raise ValueError(f"unusable area code {raw!r}")
    return digits


def city_label(counts: Counter) -> str:
    names = [name for name, _ in counts.most_common(3)]
    label = "、".join(names)
    if len(counts) > 3:
        label += "等"
    return label


def load_records(blob: bytes):
    if len(blob) < 8:
        raise SystemExit("phone.dat is too small")
    version = blob[:4].decode("ascii", "replace")
    offset = struct.unpack_from("<I", blob, 4)[0]
    if offset >= len(blob) or (len(blob) - offset) % INDEX_SIZE != 0:
        raise SystemExit("phone.dat index is not aligned")
    count = (len(blob) - offset) // INDEX_SIZE
    cache: dict[int, tuple[str, str, str, str]] = {}

    def record(position: int) -> tuple[str, str, str, str]:
        cached = cache.get(position)
        if cached is not None:
            return cached
        end = blob.index(b"\x00", position)
        parts = blob[position:end].decode("utf-8").split("|")
        if len(parts) < 4:
            raise SystemExit(f"bad record at {position}")
        parsed = (parts[0], parts[1], parts[2], normalize_area(parts[3]))
        cache[position] = parsed
        return parsed

    rows = []
    for index in range(count):
        prefix, rec_off, card = struct.unpack_from("<IIB", blob, offset + index * INDEX_SIZE)
        province, city, _zip, area = record(rec_off)
        rows.append((prefix, province, city, area, card))
    rows.sort()
    return version, rows


def build(rows):
    province_names = sorted({row[1] for row in rows})
    province_index = {name: i for i, name in enumerate(province_names)}
    area_cities: dict[str, Counter] = defaultdict(Counter)
    area_province: dict[str, str] = {}
    for _prefix, province, city, area, _card in rows:
        area_cities[area][city] += 1
        previous = area_province.get(area)
        if previous is not None and previous != province:
            raise SystemExit(f"area code {area} maps to both {previous} and {province}")
        area_province[area] = province
    area_codes = sorted(area_province)
    area_index = {code: i for i, code in enumerate(area_codes)}
    areas = [
        {
            "code": code,
            "city": city_label(area_cities[code]),
            "province": area_province[code],
        }
        for code in area_codes
    ]

    ranges = []
    virtual = set()
    start = length = area_i = None
    for prefix, province, _city, area, card in rows:
        text = str(prefix)
        if card in VIRTUAL_CARDS or text.startswith(VIRTUAL_FAMILIES):
            virtual.add(text)
        current_area = area_index[area]
        if start is None:
            start, length, area_i = prefix, 1, current_area
            continue
        contiguous = prefix == start + length and current_area == area_i and length < 65535
        if contiguous:
            length += 1
            continue
        ranges.append((start, length, area_i))
        start, length, area_i = prefix, 1, current_area
    if start is not None:
        ranges.append((start, length, area_i))
    return province_names, areas, ranges, sorted(virtual)


def encode(provinces, areas, ranges) -> bytes:
    out = bytearray()
    out += MAGIC
    out += struct.pack("<HH", VERSION, len(provinces))
    province_index = {name: i for i, name in enumerate(provinces)}
    for name in provinces:
        raw = name.encode("utf-8")
        if not 1 <= len(raw) <= 255:
            raise SystemExit(f"province name length is out of range: {name}")
        out += struct.pack("<B", len(raw))
        out += raw
    out += struct.pack("<H", len(areas))
    for area in areas:
        code = area["code"].encode("utf-8")
        city = area["city"].encode("utf-8")
        if not 1 <= len(code) <= 255 or not 1 <= len(city) <= 255:
            raise SystemExit(f"area string length is out of range: {area}")
        out += struct.pack("<B", len(code))
        out += code
        out += struct.pack("<B", len(city))
        out += city
        out += struct.pack("<H", province_index[area["province"]])
    out += struct.pack("<I", len(ranges))
    previous_end = -1
    for start, length, area_i in ranges:
        if length < 1 or length > 65535:
            raise SystemExit(f"bad range length {length}")
        end = start + length - 1
        if start <= previous_end:
            raise SystemExit("ranges overlap or are unsorted")
        previous_end = end
        out += struct.pack("<IHH", start, length, area_i)
    crc = zlib.crc32(out) & 0xFFFFFFFF
    out += struct.pack("<I", crc)
    return bytes(out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--phone-dat", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    blob = args.phone_dat.read_bytes()
    version, rows = load_records(blob)
    provinces, areas, ranges, virtual = build(rows)
    payload = encode(provinces, areas, ranges)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "prefix_ranges.dat").write_bytes(payload)
    (args.out / "virtual_prefixes.txt").write_text("\n".join(virtual) + "\n", encoding="utf-8")
    source = {
        "upstream": "https://github.com/ls0f/phone",
        "upstream_path": "phone/phone.dat",
        "upstream_license": "MIT, as stated in the upstream README",
        "upstream_version_header": version,
        "upstream_sha256": hashlib.sha256(blob).hexdigest(),
        "records": len(rows),
        "provinces": len(provinces),
        "area_codes": len(areas),
        "ranges": len(ranges),
        "virtual_prefixes": len(virtual),
        "derived_bytes": len(payload),
        "normalization": "Upstream area code 00479 (锡林郭勒) is stored as 0479.",
    }
    (args.out / "SOURCE.json").write_text(
        json.dumps(source, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(source, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
