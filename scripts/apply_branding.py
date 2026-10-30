#!/usr/bin/env python3
"""Apply the project's non-official name/icon to a checked-out upstream tree."""
import argparse
import re
import subprocess
from pathlib import Path

SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,29}$")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--app-root", required=True, type=Path)
    parser.add_argument("--display-name", default="Unofficial Chat")
    parser.add_argument("--icon", type=Path, default=Path(__file__).resolve().parents[1] / "assets/unofficial-chat-icon.png")
    args = parser.parse_args()
    if not SAFE_NAME.fullmatch(args.display_name):
        raise SystemExit("display name must be 1-30 simple Latin letters, numbers, spaces, dots, underscores or hyphens")
    if not args.app_root.is_dir() or not args.icon.is_file():
        raise SystemExit("app root or original icon asset is missing")

    catalog_names = ("DefaultAppIcon.xcassets", "AppIcons.xcassets", "Icons.xcassets")
    targets = set()
    for name in catalog_names:
        catalog = args.app_root / name
        if catalog.is_dir():
            targets.update(catalog.rglob("*.png"))
    for alticon in args.app_root.rglob("*.alticon"):
        if alticon.is_dir():
            targets.update(alticon.rglob("*.png"))
    telegram_icon_assets = args.app_root / "Telegram.icon" / "Assets"
    if telegram_icon_assets.is_dir():
        targets.update(telegram_icon_assets.rglob("*.png"))
    targets.update(args.app_root.glob("IconDefault*.png"))
    if not targets:
        raise SystemExit("no app-icon PNG assets were found; refusing to keep the official default icon")

    for target in sorted(targets):
        dims = subprocess.run(
            ["sips", "-g", "pixelWidth", "-g", "pixelHeight", str(target)],
            check=True,
            capture_output=True,
            text=True,
        ).stdout
        width_match = re.search(r"pixelWidth:\s*(\d+)", dims)
        height_match = re.search(r"pixelHeight:\s*(\d+)", dims)
        if not width_match or not height_match:
            raise SystemExit(f"could not read icon dimensions: {target}")
        width, height = int(width_match.group(1)), int(height_match.group(1))
        temp = target.with_name(target.name + ".cue-tmp.png")
        subprocess.run(
            ["sips", "-s", "format", "png", "-z", str(height), str(width), str(args.icon), "--out", str(temp)],
            check=True,
            capture_output=True,
            text=True,
        )
        temp.replace(target)

    for config in args.app_root.glob("Config*.xcconfig"):
        source = config.read_text(encoding="utf-8")
        updated, count = re.subn(r"(?m)^APP_NAME=.*$", f"APP_NAME={args.display_name}", source)
        if count:
            config.write_text(updated, encoding="utf-8")

    print(f"Applied unofficial display name and custom icon to {len(targets)} app-icon images.")


if __name__ == "__main__":
    main()
