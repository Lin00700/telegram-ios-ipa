#!/usr/bin/env python3
"""Validate the pinned Telegram unsigned IPA without reading embedded API values."""
import argparse
import hashlib
import json
import plistlib
import stat
import struct
import zipfile
from pathlib import Path, PurePosixPath

EXPECTED_EXTENSIONS = {'Share', 'NotificationContent', 'NotificationService', 'SiriIntents', 'Widget', 'BroadcastUpload'}
THIN = {b'\xce\xfa\xed\xfe': ('<', 28), b'\xcf\xfa\xed\xfe': ('<', 32), b'\xfe\xed\xfa\xce': ('>', 28), b'\xfe\xed\xfa\xcf': ('>', 32)}
FAT = {b'\xca\xfe\xba\xbe': ('>', 20), b'\xbe\xba\xfe\xca': ('<', 20), b'\xca\xfe\xba\xbf': ('>', 32), b'\xbf\xba\xfe\xca': ('<', 32)}


def macho_cpus(data: bytes) -> list[int]:
    magic = data[:4]
    if magic in FAT:
        endian, entry_size = FAT[magic]
        count = struct.unpack_from(endian + 'I', data, 4)[0]
        if count > 64 or 8 + count * entry_size > len(data):
            raise ValueError('invalid universal Mach-O header')
        result = []
        for i in range(count):
            pos = 8 + i * entry_size
            fmt = 'II' if entry_size == 20 else 'QQ'
            offset, size = struct.unpack_from(endian + fmt, data, pos + 8)
            if offset + size > len(data):
                raise ValueError('invalid universal Mach-O slice')
            cpus = macho_cpus(data[offset:offset + size])
            if not cpus:
                raise ValueError('invalid universal Mach-O slice magic')
            result.extend(cpus)
        return result
    if magic not in THIN:
        return []
    endian, header_size = THIN[magic]
    if len(data) < header_size:
        raise ValueError('truncated Mach-O header')
    cpu = struct.unpack_from(endian + 'I', data, 4)[0]
    count, commands_size = struct.unpack_from(endian + 'II', data, 16)
    end = header_size + commands_size
    if end > len(data) or count > commands_size // 8:
        raise ValueError('invalid Mach-O load command table')
    pos = header_size
    for _ in range(count):
        if pos + 8 > end:
            raise ValueError('truncated Mach-O load command')
        command, size = struct.unpack_from(endian + 'II', data, pos)
        if size < 8 or pos + size > end:
            raise ValueError('invalid Mach-O load command size')
        if command == 0x1D:
            raise ValueError('LC_CODE_SIGNATURE remains')
        pos += size
    if pos != end:
        raise ValueError('inconsistent Mach-O load command table')
    return [cpu]


def validate(path: Path, bundle_id: str) -> dict:
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [entry.filename for entry in infos]
        if len(names) != len(set(names)):
            raise ValueError('duplicate archive members')
        for name in names:
            parts = PurePosixPath(name).parts
            if name.startswith('/') or '..' in parts:
                raise ValueError('unsafe archive path')
            if '_CodeSignature' in parts or name.endswith(('.mobileprovision', '.provisionprofile')):
                raise ValueError('signature directory or provisioning profile remains')
        bad = archive.testzip()
        if bad:
            raise ValueError('ZIP integrity check failed: ' + bad)
        main_plists = [name for name in names if len(PurePosixPath(name).parts) == 3 and name.startswith('Payload/') and name.endswith('.app/Info.plist')]
        if len(main_plists) != 1:
            raise ValueError('expected exactly one Payload/*.app')
        app_root = str(PurePosixPath(main_plists[0]).parent)
        main = plistlib.loads(archive.read(main_plists[0]))
        if main.get('CFBundleIdentifier') != bundle_id or main.get('CFBundlePackageType') != 'APPL':
            raise ValueError('unexpected main app identity/type')
        extensions = []
        identifiers = set()
        bundle_executables = {}
        for name in names:
            if not name.endswith('/Info.plist'):
                continue
            parent = PurePosixPath(name).parent
            if parent.suffix not in {'.app', '.appex', '.framework', '.xpc'}:
                continue
            info = plistlib.loads(archive.read(name))
            identifier = info.get('CFBundleIdentifier')
            if identifier and parent.suffix in {'.app', '.appex', '.xpc'}:
                if identifier in identifiers:
                    raise ValueError('duplicate bundle identifier: ' + identifier)
                identifiers.add(identifier)
            executable = info.get('CFBundleExecutable')
            if executable:
                exe_path = str(parent / executable)
                if exe_path not in names:
                    raise ValueError('missing bundle executable: ' + exe_path)
                mode = archive.getinfo(exe_path).external_attr >> 16
                if not stat.S_IMODE(mode) & 0o111:
                    raise ValueError('bundle executable has no execute permission: ' + exe_path)
                bundle_executables[exe_path] = info
            if parent.suffix == '.appex':
                if not str(parent).startswith(app_root + '/PlugIns/') or not executable or not info.get('NSExtension', {}).get('NSExtensionPointIdentifier'):
                    raise ValueError('invalid extension structure: ' + str(parent))
                extensions.append({'path': str(parent), 'bundle_id': identifier, 'extension_point': info['NSExtension']['NSExtensionPointIdentifier']})
        expected = {bundle_id + '.' + suffix for suffix in EXPECTED_EXTENSIONS}
        if {item['bundle_id'] for item in extensions} != expected or len(extensions) != 6:
            raise ValueError('expected all six original iOS extensions')
        macho = {}
        for entry in infos:
            if entry.is_dir() or stat.S_ISLNK(entry.external_attr >> 16):
                continue
            with archive.open(entry) as stream:
                magic = stream.read(4)
                if magic not in THIN and magic not in FAT:
                    continue
            try:
                macho[entry.filename] = macho_cpus(archive.read(entry))
            except ValueError as error:
                raise ValueError(entry.filename + ': ' + str(error)) from error
        for executable in bundle_executables:
            if executable not in macho:
                raise ValueError('bundle executable is not Mach-O: ' + executable)
        main_exe = app_root + '/' + main['CFBundleExecutable']
        if 0x0100000C not in macho.get(main_exe, []):
            raise ValueError('main executable lacks arm64')
    with path.open('rb') as stream:
        digest = hashlib.file_digest(stream, 'sha256').hexdigest()
    return {'valid_unsigned_structure': True, 'sha256': digest, 'size_bytes': path.stat().st_size, 'main_bundle_id': bundle_id, 'display_name': main.get('CFBundleDisplayName'), 'extensions': sorted(extensions, key=lambda item: item['bundle_id']), 'macho_files_checked': len(macho), 'code_signatures': 0, 'embedded_profiles': 0, 'runtime_functionality_tested': False}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--ipa', type=Path, required=True)
    parser.add_argument('--bundle-id', required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = validate(args.ipa, args.bundle_id)
    except (ValueError, OSError, KeyError, zipfile.BadZipFile, plistlib.InvalidFileException, struct.error) as error:
        raise SystemExit('IPA validation failed: ' + str(error)) from error
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, indent=2, ensure_ascii=False) + '\n')
    print('Unsigned IPA structure validated: six extensions, arm64, executable modes, no profiles or Mach-O signatures.')


if __name__ == '__main__':
    main()
