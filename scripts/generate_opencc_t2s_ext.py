#!/usr/bin/env python3
"""Reproduce OpenCC's TSCharactersExt extraction for the pinned source dictionary."""
from __future__ import annotations

import argparse
from pathlib import Path

PREFIX = "# @tofu-risk:"


def extract(source: Path, destination: Path) -> int:
    lines = source.read_text(encoding="utf-8").splitlines()
    result: list[str] = []
    for index, line in enumerate(lines):
        if not line.startswith(PREFIX):
            continue
        if index + 1 >= len(lines):
            raise ValueError(f"Missing mapping after tofu-risk marker at line {index + 1}")
        mapping = lines[index + 1]
        if not mapping.strip() or mapping.startswith("#"):
            raise ValueError(f"Expected mapping after tofu-risk marker at line {index + 1}")
        key, values_text = mapping.split("\t", 1)
        values = values_text.split()
        if values and values[0] == key:
            values = values[1:]
        if not values:
            raise ValueError(f"Expected extension mapping after tofu-risk marker at line {index + 1}")
        result.append(f"{key}\t{' '.join(values)}")
    destination.write_text("\n".join(result) + ("\n" if result else ""), encoding="utf-8")
    return len(result)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    args = parser.parse_args()
    print(f"Generated {extract(args.source, args.destination)} OpenCC t2s extension mappings")


if __name__ == "__main__":
    main()
