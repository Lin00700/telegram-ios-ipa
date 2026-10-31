import importlib.util
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("runtime_overlay", ROOT / "scripts/apply_runtime_features.py")
OVERLAY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(OVERLAY)


class ZipArchiveLinkageTests(unittest.TestCase):
    def test_internal_helper_is_local_and_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "third-party/ZipArchive/Sources/SSZipArchive.m"
            source.parent.mkdir(parents=True)
            source.write_text(
                "// Fixture\nint _zipOpenEntry(int value);\n"
                "int call(void) { return _zipOpenEntry(1); }\n"
                "int _zipOpenEntry(int value) { return value; }\n",
                encoding="utf-8",
            )
            OVERLAY.patch_ziparchive_linkage(root)
            patched = source.read_text(encoding="utf-8")
            self.assertEqual(patched.count("\nstatic int _zipOpenEntry("), 2)
            self.assertIn("return _zipOpenEntry(1)", patched)
            OVERLAY.patch_ziparchive_linkage(root)
            self.assertEqual(source.read_text(encoding="utf-8"), patched)

    def test_source_drift_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "third-party/ZipArchive/Sources/SSZipArchive.m"
            source.parent.mkdir(parents=True)
            source.write_text("// Unexpected upstream content\n", encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "expected 2 source occurrence"):
                OVERLAY.patch_ziparchive_linkage(root)


if __name__ == "__main__":
    unittest.main()
