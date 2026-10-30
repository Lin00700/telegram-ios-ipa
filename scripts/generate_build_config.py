#!/usr/bin/env python3
"""Create a runner-local Telegram build config without importing signing data.

API values are read only from environment variables and never printed.
"""
import argparse
import json
import os
import plistlib
import re
from pathlib import Path

VALID_BUNDLE_ID = re.compile(r"^[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)+$")


def fail(message: str) -> None:
    raise SystemExit(f"build-config error: {message}")


def update_minimum_ios_version(upstream_root: Path, version: str) -> None:
    build_file = upstream_root / "Telegram/BUILD"
    if not build_file.is_file():
        fail(f"upstream Bazel app target not found: {build_file}")
    text = build_file.read_text(encoding="utf-8")
    old = 'minimum_os_version = "15.0"'
    new = f'minimum_os_version = "{version}"'
    if text.count(old) == 1:
        text = text.replace(old, new, 1)
    elif text.count(new) != 1:
        fail("expected exactly one shared minimum_os_version setting in Telegram/BUILD")
    escaped_version = version.replace(".", "\\\\.")
    extension_pattern = re.compile(r'(<<<MIN_OS_VERSION>>>/)\d+\\\\\.\d+(?=/g)')
    text, extension_count = extension_pattern.subn(lambda match: match.group(1) + escaped_version, text)
    if extension_count != 4:
        fail(f"expected exactly four extension MinimumOSVersion postprocessors, found {extension_count}")
    build_file.write_text(text, encoding="utf-8")
    print(f"Set Telegram app and shared iOS extension deployment target to iOS {version}.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--upstream-root", required=True, type=Path)
    parser.add_argument("--minimum-ios-version", default="15.5")
    args = parser.parse_args()

    api_id = os.environ.get("TG_API_ID", "").strip()
    api_hash = os.environ.get("TG_API_HASH", "").strip()
    bundle_id = os.environ.get("APP_BUNDLE_ID", "").strip()
    if not api_id.isdecimal():
        fail("TG_API_ID is missing or is not numeric; add it as a repository Actions secret")
    if len(api_hash) != 32 or any(ch not in "0123456789abcdefABCDEF" for ch in api_hash):
        fail("TG_API_HASH is missing or is not a 32-character hexadecimal API hash")
    if not VALID_BUNDLE_ID.fullmatch(bundle_id):
        fail("APP_BUNDLE_ID must be a reverse-DNS identifier using letters, numbers, dots or hyphens")
    if not args.template.is_file():
        fail(f"upstream template not found: {args.template}")
    if not re.fullmatch(r"\d+\.\d+", args.minimum_ios_version):
        fail("minimum iOS version must use a dotted numeric version such as 15.5")
    update_minimum_ios_version(args.upstream_root, args.minimum_ios_version)

    try:
        config = json.loads(args.template.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"could not read upstream configuration template: {exc}")

    # No team or certificate is needed by the patched device build: the Bazel
    # disableProvisioningProfiles setting prevents profile installation/signing.
    # This syntactically valid placeholder is discarded when the user re-signs.
    config.update({
        "bundle_id": bundle_id,
        "api_id": api_id,
        "api_hash": api_hash,
        "team_id": "0000000000",
        "app_center_id": "0",
        "is_internal_build": "true",
        "is_appstore_build": "false",
        "appstore_id": "0",
        "app_specific_url_scheme": "cuechat",
        "premium_iap_product_id": "",
        "enable_siri": False,
        "enable_icloud": False,
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    os.chmod(args.output, 0o600)
    print(f"Temporary unsigned build config created for bundle ID {bundle_id}; secrets were not printed.")


if __name__ == "__main__":
    main()
