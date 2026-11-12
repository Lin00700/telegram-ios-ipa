#!/usr/bin/env python3
"""Write Config/Shared.xcconfig from the workflow's bundle id and display name."""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9-]*(\.[A-Za-z][A-Za-z0-9-]*)+$")
NAME_RE = re.compile("^[0-9A-Za-z_ \\u4e00-\\u9fff.·-]{1,30}$")


def main() -> None:
    bundle = (os.environ.get("APP_BUNDLE_ID") or "com.lin00700.callsmsblocker").strip()
    name = (os.environ.get("APP_DISPLAY_NAME") or "来电短信过滤").strip()
    if not BUNDLE_RE.fullmatch(bundle):
        raise SystemExit("APP_BUNDLE_ID must be a reverse-DNS identifier")
    if not NAME_RE.fullmatch(name) or "//" in name or "=" in name:
        raise SystemExit("APP_DISPLAY_NAME must be 1-30 letters, digits, spaces or Chinese characters")
    text = "\n".join([
        f"APP_BUNDLE_ID = {bundle}",
        f"APP_GROUP_ID = group.{bundle}",
        f"APP_DISPLAY_NAME = {name}",
        "MARKETING_VERSION = 1.0.0",
        "CURRENT_PROJECT_VERSION = 1",
        "",
    ])
    (ROOT / "Config" / "Shared.xcconfig").write_text(text, encoding="utf-8")
    print(f"bundle {bundle}")
    print(f"app group group.{bundle}")


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(0)
