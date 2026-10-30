import json
import plistlib
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "build_mlkit_vendor.sh"
MARKER = 'python3 - "$PRODUCTS" "$VENDOR" "$VENDOR/Resources" "$POD_DIR/Pods" <<\'PY\'\n'


def collector_source() -> str:
    source = SCRIPT.read_text(encoding="utf-8")
    start = source.index(MARKER) + len(MARKER)
    end = source.index("\nPY\n", start)
    return source[start:end]


class MLKitVendorCollectorTests(unittest.TestCase):
    def test_nested_static_frameworks_are_staged_for_bazel(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            products = root / "products"
            pods = root / "Pods"
            vendor = root / "vendor"
            resources = vendor / "Resources"

            framework_paths = [
                products / "MLKitTranslate.framework",
                products / "GoogleUtilities" / "GoogleUtilities.framework",
                products / "GoogleToolboxForMac" / "GoogleToolboxForMac.framework",
                products / "GTMSessionFetcher" / "GTMSessionFetcher.framework",
                pods / "GoogleDataTransport" / "GoogleDataTransport.framework",
            ]
            for framework in framework_paths:
                framework.mkdir(parents=True)
                (framework / framework.name.removesuffix(".framework")).write_text("fixture", encoding="utf-8")

            xcframework = products / "SplitFixture.xcframework"
            device_framework = xcframework / "ios-arm64" / "SplitFixture.framework"
            device_framework.mkdir(parents=True)
            (device_framework / "SplitFixture").write_text("device slice", encoding="utf-8")
            with (xcframework / "Info.plist").open("wb") as stream:
                plistlib.dump(
                    {
                        "AvailableLibraries": [
                            {
                                "LibraryIdentifier": "ios-arm64",
                                "LibraryPath": "SplitFixture.framework",
                                "SupportedArchitectures": ["arm64"],
                                "SupportedPlatform": "ios",
                            },
                            {
                                "LibraryIdentifier": "ios-arm64-simulator",
                                "LibraryPath": "SplitFixture.framework",
                                "SupportedArchitectures": ["arm64"],
                                "SupportedPlatform": "ios",
                                "SupportedPlatformVariant": "simulator",
                            },
                        ]
                    },
                    stream,
                )

            subprocess.run(
                [
                    sys.executable,
                    "-c",
                    collector_source(),
                    str(products),
                    str(vendor),
                    str(resources),
                    str(pods),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            entries = json.loads((vendor / "targets.json").read_text(encoding="utf-8"))
            names = {entry["name"] for entry in entries}
            expected = {
                "MLKitTranslate",
                "GoogleUtilities",
                "GoogleToolboxForMac",
                "GTMSessionFetcher",
                "GoogleDataTransport",
                "SplitFixture",
            }
            self.assertEqual(names, expected)
            for name in expected:
                self.assertTrue((vendor / "Frameworks" / f"{name}.framework").is_dir())
                self.assertIn(f'name = "{name}"', (vendor / "BUILD").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
