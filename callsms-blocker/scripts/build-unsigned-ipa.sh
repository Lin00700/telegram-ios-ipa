#!/usr/bin/env bash
# Build an unsigned arm64 IPA. 全能签 re-signs the main app and both extensions.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${WORK_DIR:-${RUNNER_TEMP:-/tmp}/callsms-blocker-build}"
DIST="${DIST_DIR:-$ROOT/dist}"
DERIVED="$WORK/DerivedData"

export COPYFILE_DISABLE=1

log() { printf '\n==> %s\n' "$*"; }

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "missing required command: $1" >&2
    exit 1
  fi
}

require_cmd python3
require_cmd xcodebuild
require_cmd codesign
require_cmd ditto
require_cmd plutil
require_cmd shasum

log "Xcode"
xcodebuild -version
xcrun --sdk iphoneos --show-sdk-path

log "bundle identity"
python3 "$ROOT/scripts/apply_build_config.py"

mkdir -p "$DIST"
rm -rf "$DERIVED"

log "logic tests"
xcodebuild test \
  -project "$ROOT/CallSMSBlocker.xcodeproj" \
  -scheme CallSMSLogicTests \
  -destination 'platform=macOS' \
  -derivedDataPath "$DERIVED/tests" \
  CODE_SIGNING_ALLOWED=NO \
  CODE_SIGNING_REQUIRED=NO \
  CODE_SIGN_IDENTITY=""

log "unsigned device build"
xcodebuild build \
  -project "$ROOT/CallSMSBlocker.xcodeproj" \
  -scheme CallSMSBlocker \
  -configuration Release \
  -sdk iphoneos \
  -destination 'generic/platform=iOS' \
  -derivedDataPath "$DERIVED/app" \
  CODE_SIGNING_ALLOWED=NO \
  CODE_SIGNING_REQUIRED=NO \
  CODE_SIGN_IDENTITY="" \
  DEVELOPMENT_TEAM="" \
  AD_HOC_CODE_SIGNING_ALLOWED=YES \
  ONLY_ACTIVE_ARCH=NO \
  ARCHS=arm64 \
  VALIDATE_PRODUCT=NO

APP="$(find "$DERIVED/app/Build/Products/Release-iphoneos" -maxdepth 1 -type d -name 'CallSMSBlocker.app' -print -quit)"
if [[ -z "$APP" || ! -d "$APP" ]]; then
  echo "CallSMSBlocker.app was not produced" >&2
  find "$DERIVED/app/Build/Products" -maxdepth 3 -type d -name '*.app' -print >&2 || true
  exit 1
fi

for extension in MessageFilter.appex CallDirectory.appex; do
  if [[ ! -d "$APP/PlugIns/$extension" ]]; then
    echo "missing embedded extension: PlugIns/$extension" >&2
    find "$APP" -maxdepth 3 -type d -print >&2
    exit 1
  fi
done

log "strip signatures"
while IFS= read -r bundle; do
  codesign --remove-signature "$bundle" >/dev/null 2>&1 || true
  rm -rf "$bundle/_CodeSignature"
  rm -f "$bundle/embedded.mobileprovision"
done < <(find "$APP" -depth -type d \( -name '*.app' -o -name '*.appex' -o -name '*.framework' \))
find "$APP" -name 'embedded.mobileprovision' -delete

if codesign -dv "$APP" >/dev/null 2>&1; then
  echo "the app is still signed after stripping" >&2
  exit 1
fi
if find "$APP" -type d -name '_CodeSignature' | grep -q .; then
  echo "a _CodeSignature directory remains" >&2
  exit 1
fi

log "package IPA"
STAGE="$WORK/stage"
rm -rf "$STAGE"
mkdir -p "$STAGE/Payload"
cp -R "$APP" "$STAGE/Payload/CallSMSBlocker.app"
IPA="$DIST/CallSMSBlocker-unsigned.ipa"
rm -f "$IPA"
ditto -c -k --sequesterRsrc --keepParent "$STAGE/Payload" "$IPA"

python3 - "$ROOT" "$IPA" "$DIST" <<'PY'
import hashlib, json, os, plistlib, sys, zipfile
from pathlib import Path

root, ipa_path, dist = map(Path, sys.argv[1:])
xcconfig = (root / "Config" / "Shared.xcconfig").read_text(encoding="utf-8")
values = {}
for line in xcconfig.splitlines():
    if "=" not in line or line.strip().startswith("//"):
        continue
    key, value = line.split("=", 1)
    values[key.strip()] = value.strip()
bundle = values["APP_BUNDLE_ID"]
group = values["APP_GROUP_ID"]
name = values["APP_DISPLAY_NAME"]

with zipfile.ZipFile(ipa_path) as archive:
    names = archive.namelist()
    def read_plist(suffix):
        matches = [item for item in names if item.endswith(suffix)]
        if len(matches) != 1:
            raise SystemExit(f"expected one {suffix}, found {matches}")
        return plistlib.loads(archive.read(matches[0])), matches[0]

    app_plist, _ = read_plist("Payload/CallSMSBlocker.app/Info.plist")
    message_plist, _ = read_plist("Payload/CallSMSBlocker.app/PlugIns/MessageFilter.appex/Info.plist")
    call_plist, _ = read_plist("Payload/CallSMSBlocker.app/PlugIns/CallDirectory.appex/Info.plist")

problems = []
if app_plist.get("CFBundleIdentifier") != bundle:
    problems.append(f"app bundle id is {app_plist.get('CFBundleIdentifier')}")
if app_plist.get("CFBundleDisplayName") != name:
    problems.append("display name was not substituted")
if app_plist.get("AppGroupIdentifier") != group:
    problems.append("app group was not substituted")
message_ext = message_plist.get("NSExtension", {})
call_ext = call_plist.get("NSExtension", {})
if message_ext.get("NSExtensionPointIdentifier") != "com.apple.identitylookup.message-filter":
    problems.append("message filter extension point is wrong")
if call_ext.get("NSExtensionPointIdentifier") != "com.apple.callkit.call-directory":
    problems.append("call directory extension point is wrong")
if "ILMessageFilterExtensionNetworkURL" in message_ext.get("NSExtensionAttributes", {}):
    problems.append("message filter declares a network URL")
if any(item.endswith("_CodeSignature/") or item.endswith("embedded.mobileprovision") for item in names):
    problems.append("signature material remains in the IPA")
if problems:
    raise SystemExit("\n".join(problems))

digest = hashlib.sha256(ipa_path.read_bytes()).hexdigest()
(dist / "CallSMSBlocker-unsigned.ipa.sha256").write_text(f"{digest}  CallSMSBlocker-unsigned.ipa\n", encoding="utf-8")
install = (root / "INSTALL.md").read_text(encoding="utf-8")
install = install.replace("com.lin00700.callsmsblocker", bundle).replace("来电短信过滤", name)
(dist / "INSTALL.md").write_text(install, encoding="utf-8")
entitlements = dist / "entitlements"
entitlements.mkdir(exist_ok=True)
entitlement = {
    "com.apple.security.application-groups": [group],
}
for filename in ("CallSMSBlocker.entitlements", "MessageFilter.entitlements", "CallDirectory.entitlements"):
    with (entitlements / filename).open("wb") as handle:
        plistlib.dump(entitlement, handle, fmt=plistlib.FMT_XML)
report = {
    "ipa": ipa_path.name,
    "sha256": digest,
    "bundle_id": bundle,
    "display_name": name,
    "app_group": group,
    "extensions": [
        "PlugIns/MessageFilter.appex",
        "PlugIns/CallDirectory.appex",
    ],
    "unsigned": True,
    "deployment_target": "16.0",
    "network": False,
}
(dist / "build-validation.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(report, ensure_ascii=False, indent=2))
PY

log "done"
ls -lh "$IPA" "$DIST/CallSMSBlocker-unsigned.ipa.sha256" "$DIST/INSTALL.md"
