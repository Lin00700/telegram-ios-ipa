#!/usr/bin/env python3
"""Enable a runner-local, explicitly unsigned Telegram device build.

The pinned rules_apple fork supports disable_legacy_signing, but its iOS
application/extension rules still unconditionally embed device profiles.
Patch only those profile branches to honor that feature. No signer, certificate
or provisioning profile is introduced. Signed builds retain their old behavior.
"""
import argparse
import re
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
OLD_ARGS = "            combined_arguments += ['--//Telegram:disableProvisioningProfiles']"
NEW_ARGS = "            combined_arguments += ['--//Telegram:disableProvisioningProfiles', '--features=disable_legacy_signing']"
OLD_PROFILE_BRANCH = re.compile(
    r'    if platform_prerequisites\.platform\.is_device:\n'
    r'        processor_partials\.append\(\n'
    r'            partials\.provisioning_profile_partial\('
)
NEW_PROFILE_BRANCH = (
    '    if platform_prerequisites.platform.is_device and "disable_legacy_signing" not in features:\n'
    '        processor_partials.append(\n'
    '            partials.provisioning_profile_partial('
)


def patch(source: str) -> str:
    build_start = source.find(PARSER_START)
    if build_start < 0:
        raise SystemExit('unsupported Make.py: could not locate the build parser')
    parser_marker = source.find(PARSER_MARKER, build_start)
    if parser_marker < 0:
        raise SystemExit('unsupported Make.py: build configuration argument marker changed')
    if "'--disableProvisioningProfiles'" not in source[build_start:parser_marker]:
        source = source[:parser_marker] + FLAG_ARGUMENT + source[parser_marker:]

    fn_start = source.find('def build(bazel, arguments):')
    if fn_start < 0:
        raise SystemExit('unsupported Make.py: could not locate build()')
    fn_end = source.find('\ndef ', fn_start + len('def build(bazel, arguments):'))
    if fn_end < 0:
        fn_end = len(source)
    fn = source[fn_start:fn_end]
    if 'set_disable_provisioning_profiles()' not in fn:
        if CONSTRUCTOR not in fn:
            raise SystemExit('unsupported Make.py: build() BazelCommandLine setup changed')
        fn = fn.replace(CONSTRUCTOR, CONSTRUCTOR + '\n' + FLAG_FORWARD.rstrip('\n'), 1)
        source = source[:fn_start] + fn + source[fn_end:]
    if NEW_ARGS not in source:
        if source.count(OLD_ARGS) != 1:
            raise SystemExit('unsupported Make.py: unsigned build argument list changed')
        source = source.replace(OLD_ARGS, NEW_ARGS, 1)
    return source


def patch_ios_rules(source: str) -> str:
    old_count = len(OLD_PROFILE_BRANCH.findall(source))
    new_count = source.count(NEW_PROFILE_BRANCH)
    if old_count == 0 and new_count == 6:
        return source
    if old_count != 6 or new_count != 0:
        raise SystemExit('unsupported rules_apple: expected exactly six iOS profile branches')
    return OLD_PROFILE_BRANCH.sub(lambda _: NEW_PROFILE_BRANCH, source)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--make-script', required=True, type=Path)
    parser.add_argument('--rules-apple-root', required=True, type=Path)
    args = parser.parse_args()
    rules_path = args.rules_apple_root / 'apple/internal/ios_rules.bzl'
    signing_path = args.rules_apple_root / 'apple/internal/codesigning_support.bzl'
    signing_source = signing_path.read_text(encoding='utf-8')
    if 'if "disable_legacy_signing" in features:' not in signing_source:
        raise SystemExit('unsupported rules_apple: disable_legacy_signing feature missing')

    # Validate both transformations before writing either file.
    make_source = args.make_script.read_text(encoding='utf-8')
    rules_source = rules_path.read_text(encoding='utf-8')
    updated_make = patch(make_source)
    updated_rules = patch_ios_rules(rules_source)
    compile(updated_make, str(args.make_script), 'exec')
    if updated_make != make_source:
        args.make_script.write_text(updated_make, encoding='utf-8')
    if updated_rules != rules_source:
        rules_path.write_text(updated_rules, encoding='utf-8')
    print('Runner-local unsigned mode ready: device profiles omitted and legacy signing disabled.')


if __name__ == '__main__':
    main()
