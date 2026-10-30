#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM="${1:?Usage: build_mlkit_vendor.sh <upstream-root>}"
APP_ROOT="$UPSTREAM/Telegram/Telegram-iOS"
POD_DIR="${RUNNER_TEMP:-/tmp}/cue-mlkit-pods"
DERIVED="${RUNNER_TEMP:-/tmp}/cue-mlkit-derived"
VENDOR="$UPSTREAM/submodules/CueChatAutomation/MLKitVendor"
PRODUCTS="$POD_DIR/build/Release-iphoneos"

if ! command -v pod >/dev/null 2>&1; then
  sudo gem install cocoapods --no-document
fi

rm -rf "$POD_DIR" "$DERIVED" "$VENDOR"
mkdir -p "$POD_DIR" "$APP_ROOT/Resources"
cp "$ROOT/third_party/mlkit/Podfile" "$POD_DIR/Podfile"

pod install --project-directory="$POD_DIR" --silent
if [[ -f "$POD_DIR/Podfile.lock" ]]; then
  cp "$POD_DIR/Podfile.lock" "${RUNNER_TEMP:-/tmp}/MLKit-Podfile.lock"
fi
xcodebuild \
  -project "$POD_DIR/Pods/Pods.xcodeproj" \
  -scheme Pods-CueMLKit \
  -configuration Release \
  -sdk iphoneos \
  -arch arm64 \
  -derivedDataPath "$DERIVED" \
  CODE_SIGNING_ALLOWED=NO

if [[ ! -d "$PRODUCTS" && -d "$DERIVED/Build/Products/Release-iphoneos" ]]; then
  PRODUCTS="$DERIVED/Build/Products/Release-iphoneos"
fi
if [[ ! -d "$PRODUCTS" ]]; then
  echo "CocoaPods did not produce Release-iphoneos products at $PRODUCTS" >&2
  exit 1
fi
mkdir -p "$VENDOR/Frameworks"

python3 - "$PRODUCTS" "$VENDOR" "$APP_ROOT/Resources" "$POD_DIR/Pods" <<'PY'
import json
import plistlib
import re
import shutil
import sys
from pathlib import Path

products = Path(sys.argv[1])
vendor = Path(sys.argv[2])
resources = Path(sys.argv[3])
pods = Path(sys.argv[4])
framework_candidates = {}

def add_framework(path: Path, priority: int, from_xcframework: bool = False) -> None:
    if not path.is_dir() or (not from_xcframework and any(parent.suffix == ".xcframework" for parent in path.parents)):
        return
    name = path.name[:-len(".framework")]
    current = framework_candidates.get(name)
    if current is None or priority < current[0]:
        framework_candidates[name] = (priority, path)

for path in products.glob("*.framework"):
    add_framework(path, 0)
if pods.is_dir():
    for path in pods.rglob("*.framework"):
        add_framework(path, 1)

for root, priority in ((products, 0), (pods, 1)):
    if not root.is_dir():
        continue
    for xcframework in root.rglob("*.xcframework"):
        info_path = xcframework / "Info.plist"
        try:
            info = plistlib.loads(info_path.read_bytes())
        except (OSError, plistlib.InvalidFileException):
            continue
        for library in info.get("AvailableLibraries", []):
            if library.get("SupportedPlatform") != "ios" or library.get("SupportedPlatformVariant") == "simulator":
                continue
            if "arm64" not in library.get("SupportedArchitectures", []):
                continue
            library_path = xcframework / library.get("LibraryIdentifier", "") / library.get("LibraryPath", "")
            if library_path.suffix == ".framework":
                add_framework(library_path, priority, from_xcframework=True)

frameworks = [value[1] for _, value in sorted(framework_candidates.items())]
if not frameworks:
    raise SystemExit(f"No built or vendored iOS frameworks found under {products} or {pods}")

def target_name(name: str) -> str:
    value = re.sub(r"[^A-Za-z0-9_.-]", "_", name)
    if not value or not re.match(r"[A-Za-z0-9_].*", value):
        value = "F_" + value
    return value

entries = []
for source in frameworks:
    name = source.name[:-len(".framework")]
    target = target_name(name)
    destination = vendor / "Frameworks" / source.name
    shutil.copytree(source, destination, symlinks=True)
    entries.append({"name": name, "target": target})

bundle_candidates = {}
for root, priority in ((products, 0), (pods, 1)):
    if root.is_dir():
        for path in root.rglob("*.bundle"):
            if path.is_dir() and (path.name not in bundle_candidates or priority < bundle_candidates[path.name][0]):
                bundle_candidates[path.name] = (priority, path)
bundles = [value[1] for _, value in sorted(bundle_candidates.items())]
for source in bundles:
    destination = resources / source.name
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(source, destination, symlinks=True)

notice_sections = []
if pods.is_dir():
    for notice in sorted(pods.rglob("NOTICES")):
        if notice.is_file():
            try:
                body = notice.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            notice_sections.append(f"===== {notice.relative_to(pods)} =====\n{body}")
if notice_sections:
    (resources / "CueMLKitNotices.txt").write_text("\n\n".join(notice_sections), encoding="utf-8")

rule_lines = [
    'load("@build_bazel_rules_apple//apple:apple.bzl", "apple_static_framework_import")',
    "",
]
for entry in entries:
    rule_lines.extend([
        "apple_static_framework_import(",
        f'    name = "{entry["target"]}",',
        f'    framework_imports = glob(["Frameworks/{entry["name"]}.framework/**"]),',
        '    sdk_frameworks = ["Accelerate", "CoreGraphics", "CoreTelephony", "Foundation", "LocalAuthentication", "NaturalLanguage", "Security", "SystemConfiguration", "UIKit"],',
        '    sdk_dylibs = ["c++", "iconv", "sqlite3", "z"],',
        '    visibility = ["//visibility:public"],',
        ")",
        "",
    ])
(vendor / "BUILD").write_text("\n".join(rule_lines), encoding="utf-8")
(vendor / "targets.json").write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
print(f"Built and staged {len(entries)} ML Kit/CocoaPods frameworks and {len(bundles)} resource bundles.")
PY
