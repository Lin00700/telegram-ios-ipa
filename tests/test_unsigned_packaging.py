import importlib.util
import io
import os
import plistlib
import stat
import struct
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


validator = load('validate_unsigned_ipa')
packager = load('package_unsigned_ipa')
BUNDLE_ID = 'com.example.unofficialchat'


def macho(signed=False):
    header = struct.pack('<IIIIIIII', 0xFEEDFACF, 0x0100000C, 0, 2, int(signed), 16 if signed else 0, 0, 0)
    return header + (struct.pack('<IIII', 0x1D, 16, 0, 0) if signed else b'')


def add(archive, name, data, mode=0o644):
    info = zipfile.ZipInfo(name)
    info.create_system = 3
    info.external_attr = (stat.S_IFREG | mode) << 16
    archive.writestr(info, data)


def fixture(path, *, signed=False, mode=0o755, missing=False, profile=False):
    with zipfile.ZipFile(path, 'w') as archive:
        app = 'Payload/Example.app'
        main = {'CFBundleIdentifier': BUNDLE_ID, 'CFBundlePackageType': 'APPL', 'CFBundleExecutable': 'Example', 'CFBundleDisplayName': 'Unofficial Chat'}
        add(archive, app + '/Info.plist', plistlib.dumps(main))
        add(archive, app + '/Example', macho(signed), mode)
        suffixes = sorted(validator.EXPECTED_EXTENSIONS)
        for suffix in suffixes[:-1] if missing else suffixes:
            folder = app + '/PlugIns/' + suffix + '.appex'
            data = {'CFBundleIdentifier': BUNDLE_ID + '.' + suffix, 'CFBundleExecutable': suffix, 'NSExtension': {'NSExtensionPointIdentifier': 'com.example.test'}}
            add(archive, folder + '/Info.plist', plistlib.dumps(data))
            add(archive, folder + '/' + suffix, macho(), 0o755)
        if profile:
            add(archive, app + '/embedded.mobileprovision', b'not-a-real-profile')


class UnsignedIPATests(unittest.TestCase):
    def test_structure(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / 'test.ipa'
            fixture(p)
            result = validator.validate(p, BUNDLE_ID)
            self.assertEqual(len(result['extensions']), 6)
            self.assertEqual(result['macho_files_checked'], 7)
            self.assertFalse(result['runtime_functionality_tested'])

    def test_invalid_packages_rejected(self):
        for options in ({'signed': True}, {'mode': 0o644}, {'missing': True}, {'profile': True}):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as d:
                p = Path(d) / 'test.ipa'
                fixture(p, **options)
                with self.assertRaises(ValueError):
                    validator.validate(p, BUNDLE_ID)

    def test_safe_extract_keeps_modes_and_relative_links(self):
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, 'w') as archive:
            add(archive, 'Payload/Test.app/Test', macho(), 0o755)
            link = zipfile.ZipInfo('Payload/Test.app/Alias')
            link.create_system = 3
            link.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(link, 'Test')
        with tempfile.TemporaryDirectory() as d, zipfile.ZipFile(buffer) as archive:
            packager.safe_extract(archive, Path(d))
            self.assertTrue(os.stat(Path(d) / 'Payload/Test.app/Test').st_mode & 0o111)
            self.assertTrue((Path(d) / 'Payload/Test.app/Alias').is_symlink())

    def test_extra_resource_bundles_are_copied_intact(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            staged = root / 'staged'
            app = root / 'Example.app'
            bundle = staged / 'MLKitTranslate_resources.bundle'
            bundle.mkdir(parents=True)
            app.mkdir()
            (bundle / 'Info.plist').write_bytes(plistlib.dumps({'CFBundlePackageType': 'BNDL'}))
            (bundle / 'model.dat').write_bytes(b'local-model-resource')
            (staged / 'CueMLKitNotices.txt').write_text('Third-party notices', encoding='utf-8')
            copied = packager.copy_extra_resources(staged, app)
            self.assertEqual(copied, 2)
            self.assertEqual((app / bundle.name / 'model.dat').read_bytes(), b'local-model-resource')
            self.assertTrue((app / bundle.name / 'Info.plist').is_file())
            self.assertEqual((app / 'CueMLKitNotices.txt').read_text(encoding='utf-8'), 'Third-party notices')

    def test_extra_resource_collision_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            staged = root / 'staged'
            app = root / 'Example.app'
            staged.mkdir()
            app.mkdir()
            (staged / 'Existing.bundle').mkdir()
            (app / 'Existing.bundle').mkdir()
            with self.assertRaises(SystemExit):
                packager.copy_extra_resources(staged, app)

    def test_unsafe_extraction_rejected(self):
        for name, target in (('../escape', None), ('Payload/link', '../../../escape')):
            with self.subTest(name=name), tempfile.TemporaryDirectory() as d:
                buffer = io.BytesIO()
                with zipfile.ZipFile(buffer, 'w') as archive:
                    if target:
                        info = zipfile.ZipInfo(name)
                        info.create_system = 3
                        info.external_attr = (stat.S_IFLNK | 0o777) << 16
                        archive.writestr(info, target)
                    else:
                        add(archive, name, b'bad')
                with zipfile.ZipFile(buffer) as archive, self.assertRaises(SystemExit):
                    packager.safe_extract(archive, Path(d))


if __name__ == '__main__':
    unittest.main()
