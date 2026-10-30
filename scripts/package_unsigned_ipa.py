#!/usr/bin/env python3
"""Preserve bundle structure and package a verified unsigned IPA for user signing."""
import argparse
import os
import plistlib
import re
import shutil
import stat
import subprocess
import tempfile
import zipfile
from pathlib import Path

BUNDLE_DIRS = {".app", ".appex", ".framework", ".bundle", ".xpc"}
VALID_BUNDLE_ID = re.compile(r"^[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)+$")
SAFE_DISPLAY_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 ._-]{0,29}$")


def remove_signature(path: Path) -> None:
    subprocess.run(["/usr/bin/codesign", "--remove-signature", str(path)], capture_output=True, check=False)


def update_info_plists(payload: Path, base_bundle_id: str, new_bundle_id: str, display_name: str) -> int:
    changed = 0
    for path in payload.rglob("Info.plist"):
        try:
            with path.open("rb") as stream:
                data = plistlib.load(stream)
        except (OSError, plistlib.InvalidFileException):
            continue
        identifier = data.get("CFBundleIdentifier")
        if isinstance(identifier, str) and (identifier == base_bundle_id or identifier.startswith(base_bundle_id + ".")):
            data["CFBundleIdentifier"] = new_bundle_id + identifier[len(base_bundle_id):]
            changed += 1
        for key in ("CFBundleDisplayName", "CFBundleName"):
            if key in data:
                data[key] = display_name
        with path.open("wb") as stream:
            plistlib.dump(data, stream, fmt=plistlib.FMT_XML, sort_keys=False)

    # Localized InfoPlist.strings can override the visible app/extension name.
    for path in payload.rglob("InfoPlist.strings"):
        for key in ("CFBundleDisplayName", "CFBundleName"):
            result = subprocess.run(
                ["/usr/bin/plutil", "-replace", key, "-string", display_name, str(path)],
                capture_output=True,
                check=False,
            )
            if result.returncode != 0:
                subprocess.run(
                    ["/usr/bin/plutil", "-insert", key, "-string", display_name, str(path)],
                    capture_output=True,
                    check=False,
                )
    return changed


def safe_extract(archive: zipfile.ZipFile, destination: Path) -> None:
    base = destination.resolve()
    seen = set()
    directories = []
    for member in archive.infolist():
        if member.filename in seen:
            raise SystemExit("input IPA contains duplicate archive paths")
        seen.add(member.filename)
        target = (destination / member.filename).resolve()
        if target != base and base not in target.parents:
            raise SystemExit("input IPA contains an unsafe archive path")
        mode = member.external_attr >> 16
        if member.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            directories.append((target, stat.S_IMODE(mode) or 0o755))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        if stat.S_ISLNK(mode):
            link = archive.read(member).decode('utf-8')
            resolved_link = (target.parent / link).resolve()
            if os.path.isabs(link) or (resolved_link != base and base not in resolved_link.parents):
                raise SystemExit("input IPA contains an unsafe symlink")
            target.symlink_to(link)
        else:
            with archive.open(member) as source, target.open('wb') as output:
                shutil.copyfileobj(source, output)
            target.chmod(stat.S_IMODE(mode) or 0o644)
    for target, mode in reversed(directories):
        target.chmod(mode)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-ipa", required=True, type=Path)
    parser.add_argument("--output-ipa", required=True, type=Path)
    parser.add_argument("--base-bundle-id", required=True)
    parser.add_argument("--bundle-id", required=True)
    parser.add_argument("--display-name", required=True)
    args = parser.parse_args()
    if not args.input_ipa.is_file():
        raise SystemExit(f"input IPA not found: {args.input_ipa}")
    if not VALID_BUNDLE_ID.fullmatch(args.bundle_id):
        raise SystemExit("bundle ID must be a reverse-DNS identifier using letters, numbers, dots or hyphens")
    if not SAFE_DISPLAY_NAME.fullmatch(args.display_name):
        raise SystemExit("display name must be 1-30 simple Latin letters, numbers, spaces, dots, underscores or hyphens")
    if not args.base_bundle_id or "." not in args.base_bundle_id:
        raise SystemExit("invalid configured base bundle ID")

    args.output_ipa.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="cue-unsigned-ipa-") as temp_name:
        work = Path(temp_name)
        with zipfile.ZipFile(args.input_ipa) as archive:
            safe_extract(archive, work)
        payload = work / "Payload"
        apps = sorted(payload.glob("*.app")) if payload.is_dir() else []
        if len(apps) != 1:
            raise SystemExit("expected exactly one top-level Payload/*.app in the upstream IPA")

        changed = update_info_plists(payload, args.base_bundle_id, args.bundle_id, args.display_name)
        if changed == 0:
            raise SystemExit("no bundle IDs matched the configured base app ID; refusing an ambiguous package")

        # Remove nested code signatures deepest-first, then the containing app
        # signature. Do not keep any provisioning profile in a user-signed IPA.
        candidates = []
        for path in payload.rglob("*"):
            if path.is_dir() and path.suffix in BUNDLE_DIRS:
                candidates.append(path)
            elif path.is_file() and (path.suffix in {".dylib", ".so"} or os.access(path, os.X_OK)):
                candidates.append(path)
        for path in sorted(candidates, key=lambda item: len(item.parts), reverse=True):
            remove_signature(path)

        for path in sorted(payload.rglob("*"), key=lambda item: len(item.parts), reverse=True):
            if path.is_dir() and path.name == "_CodeSignature":
                shutil.rmtree(path, ignore_errors=True)
            elif path.is_file() and path.name == "embedded.mobileprovision":
                path.unlink(missing_ok=True)

        residual = [p for p in payload.rglob("*") if p.is_dir() and p.name == "_CodeSignature"]
        profiles = list(payload.rglob("embedded.mobileprovision"))
        if residual or profiles:
            raise SystemExit("signature directories or embedded provisioning profiles remain")
        for path in candidates:
            check = subprocess.run(["/usr/bin/codesign", "-dv", "--verbose=2", str(path)], capture_output=True, check=False)
            if check.returncode == 0:
                raise SystemExit(f"a code signature remains after stripping: {path}")

        app = apps[0]
        safe_name = re.sub(r"[^A-Za-z0-9._-]+", "", args.display_name.replace(" ", "")) or "UnofficialChat"
        renamed = app.with_name(f"{safe_name}.app")
        if renamed != app:
            app.rename(renamed)
        if args.output_ipa.exists():
            args.output_ipa.unlink()
        subprocess.run(
            ["/usr/bin/ditto", "-c", "-k", "--sequesterRsrc", "--keepParent", str(payload), str(args.output_ipa.resolve())],
            check=True,
        )
    print(f"Created unsigned IPA: {args.output_ipa} (updated {changed} bundle IDs; no embedded profiles/signature directories)")


if __name__ == "__main__":
    main()
