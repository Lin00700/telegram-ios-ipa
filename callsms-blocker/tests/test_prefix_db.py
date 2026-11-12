import struct
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = (ROOT / "Resources" / "prefix_ranges.dat").read_bytes()


def load(blob: bytes):
    if blob[:4] != b"P7R1":
        raise AssertionError("bad magic")
    cursor = 4
    version = struct.unpack_from("<H", blob, cursor)[0]
    cursor += 2
    if version != 1:
        raise AssertionError(version)
    province_count = struct.unpack_from("<H", blob, cursor)[0]
    cursor += 2
    provinces = []
    for _ in range(province_count):
        length = blob[cursor]
        cursor += 1
        provinces.append(blob[cursor:cursor + length].decode())
        cursor += length
    area_count = struct.unpack_from("<H", blob, cursor)[0]
    cursor += 2
    areas = []
    for _ in range(area_count):
        length = blob[cursor]
        cursor += 1
        code = blob[cursor:cursor + length].decode()
        cursor += length
        length = blob[cursor]
        cursor += 1
        city = blob[cursor:cursor + length].decode()
        cursor += length
        province_index = struct.unpack_from("<H", blob, cursor)[0]
        cursor += 2
        areas.append((code, city, province_index))
    range_count = struct.unpack_from("<I", blob, cursor)[0]
    cursor += 4
    ranges = []
    for _ in range(range_count):
        start, length, area_index = struct.unpack_from("<IHH", blob, cursor)
        cursor += 8
        ranges.append((start, length, area_index))
    stored = struct.unpack_from("<I", blob, cursor)[0]
    if cursor + 4 != len(blob):
        raise AssertionError("trailing bytes")
    if stored != (zlib.crc32(blob[:-4]) & 0xFFFFFFFF):
        raise AssertionError("crc")
    return provinces, areas, ranges


def lookup(ranges, areas, provinces, prefix):
    low, high = 0, len(ranges) - 1
    while low <= high:
        mid = (low + high) // 2
        start, length, area_index = ranges[mid]
        if prefix < start:
            high = mid - 1
        elif prefix > start + length - 1:
            low = mid + 1
        else:
            code, city, province_index = areas[area_index]
            return provinces[province_index], code, city
    return None


class PrefixDatabaseTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.provinces, cls.areas, cls.ranges = load(DATA)

    def test_ranges_are_packed_and_ordered(self):
        self.assertGreater(len(self.ranges), 100_000)
        self.assertLess(len(DATA), 1_200_000)
        previous = -1
        for start, length, area_index in self.ranges:
            self.assertGreater(length, 0)
            self.assertLess(area_index, len(self.areas))
            self.assertGreater(start, previous)
            previous = start + length - 1

    def test_known_regions(self):
        self.assertIn("广东", self.provinces)
        self.assertIn("北京", self.provinces)
        self.assertEqual(lookup(self.ranges, self.areas, self.provinces, 1300000)[:2], ("山东", "0531"))
        shenzhen = next(area for area in self.areas if area[0] == "0755")
        self.assertEqual(self.provinces[shenzhen[2]], "广东")
        self.assertIn("深圳", shenzhen[1])
        xilin = lookup(self.ranges, self.areas, self.provinces, 1303045)
        self.assertEqual(xilin[:2], ("内蒙古", "0479"))
        self.assertIsNone(lookup(self.ranges, self.areas, self.provinces, 1000000))
        self.assertNotIn("00479", [area[0] for area in self.areas])


if __name__ == "__main__":
    unittest.main()
