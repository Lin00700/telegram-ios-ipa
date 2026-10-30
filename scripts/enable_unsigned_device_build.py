#!/usr/bin/env python3
"""Expose Telegram's existing Bazel no-provisioning flag on Make.py build.

The upstream Bazel rule already supports this setting. This deterministic,
runner-local patch only forwards the existing Starlark flag for release_arm64.
It does not change or commit upstream source and does not introduce a signer.
"""
import argparse
from pathlib import Path

PARSER_START = "    buildParser = subparsers.add_parser('build', help='Build the app')"
PARSER_MARKER = "    buildParser.add_argument(\n        '--configuration',"
CONSTRUCTOR = """    bazel_command_line = BazelCommandLine(
        bazel=bazel,
        override_bazel_version=arguments.overrideBazelVersion,
        override_xcode_version=arguments.overrideXcodeVersion,
        bazel_user_root=arguments.bazelUserRoot
    )"""
FLAG_ARGUMENT = """    buildParser.add_argument(
        '--disableProvisioningProfiles',
        action='store_true',
        default=False,
        help='Build an unsigned device IPA without provisioning profiles.'
    )
"""
FLAG_FORWARD = """    if getattr(arguments, 'disableProvisioningProfiles', False):
        bazel_command_line.set_disable_provisioning_profiles()
"""


def patch(source: str) -> str:
    build_start = source.find(PARSER_START)
    if build_start < 0:
        raise SystemExit("unsupported Make.py: could not locate the build parser")
    parser_marker = source.find(PARSER_MARKER, build_start)
    if parser_marker < 0:
        raise SystemExit("unsupported Make.py: build configuration argument marker changed")

    build_parser_prefix = source[build_start:parser_marker]
    if "'--disableProvisioningProfiles'" not in build_parser_prefix:
        source = source[:parser_marker] + FLAG_ARGUMENT + source[parser_marker:]

    fn_start = source.find("def build(bazel, arguments):")
    if fn_start < 0:
        raise SystemExit("unsupported Make.py: could not locate build()")
    fn_end = source.find("\ndef ", fn_start + len("def build(bazel, arguments):"))
    if fn_end < 0:
        fn_end = len(source)
    fn = source[fn_start:fn_end]
    if "set_disable_provisioning_profiles()" not in fn:
        if CONSTRUCTOR not in fn:
            raise SystemExit("unsupported Make.py: build() BazelCommandLine setup changed")
        fn = fn.replace(CONSTRUCTOR, CONSTRUCTOR + "\n" + FLAG_FORWARD.rstrip("\n"), 1)
        source = source[:fn_start] + fn + source[fn_end:]
    return source


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--make-script", required=True, type=Path)
    args = parser.parse_args()
    text = args.make_script.read_text(encoding="utf-8")
    updated = patch(text)
    if updated == text:
        print("Make.py already exposes the unsigned device build flag.")
    else:
        args.make_script.write_text(updated, encoding="utf-8")
        print("Enabled upstream Bazel unsigned-device flag in the runner-local Make.py copy.")


if __name__ == "__main__":
    main()
