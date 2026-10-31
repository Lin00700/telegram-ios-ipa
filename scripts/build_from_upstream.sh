#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM="${UPSTREAM_DIR:-$ROOT/upstream}"
APP_ROOT="$UPSTREAM/Telegram/Telegram-iOS"
CONFIG="$RUNNER_TEMP/telegram-build-config.json"
BUILD_ARTIFACTS="$RUNNER_TEMP/telegram-build-artifacts"
OUTPUT="$ROOT/artifacts"

: "${TG_API_ID:?Missing TG_API_ID Actions secret}"
: "${TG_API_HASH:?Missing TG_API_HASH Actions secret}"
: "${APP_BUNDLE_ID:?Missing workflow app_bundle_id input}"
: "${APP_DISPLAY_NAME:=Unofficial Chat}"
: "${BUILD_NUMBER:=$GITHUB_RUN_NUMBER}"

if [[ ! -d "$UPSTREAM/.git" || ! -f "$UPSTREAM/.gitmodules" ]]; then
  echo "Expected a recursive checkout of TelegramMessenger/Telegram-iOS at $UPSTREAM" >&2
  exit 1
fi

# Keep source paths stable: upstream notes that source paths are embedded in the binary.
CANONICAL="/Users/Shared/telegram-ios"
sudo rm -rf "$CANONICAL"
sudo mkdir -p "$(dirname "$CANONICAL")"
sudo ditto "$UPSTREAM" "$CANONICAL"
UPSTREAM="$CANONICAL"
APP_ROOT="$UPSTREAM/Telegram/Telegram-iOS"

python3 "$ROOT/scripts/generate_opencc_t2s_ext.py" \
  "$ROOT/assets/opencc/TSCharacters.txt" "$RUNNER_TEMP/TSCharactersExt.generated.txt"
cmp -s "$RUNNER_TEMP/TSCharactersExt.generated.txt" "$ROOT/assets/opencc/TSCharactersExt.txt"

mkdir -p "$APP_ROOT/Resources"
cp "$ROOT/assets/cf-inkwash-global.png" "$APP_ROOT/Resources/ChatWallpaperBuiltin0.png"
bash "$ROOT/scripts/build_mlkit_vendor.sh" "$UPSTREAM"
python3 "$ROOT/scripts/apply_runtime_features.py" --upstream "$UPSTREAM" --repo-root "$ROOT"
python3 "$ROOT/scripts/apply_custom_client_ui.py" --upstream "$UPSTREAM"
python3 "$ROOT/scripts/apply_inkwash_theme.py" --upstream "$UPSTREAM"
python3 "$ROOT/scripts/apply_global_wallpaper.py" --upstream "$UPSTREAM"

python3 "$ROOT/scripts/apply_branding.py" --app-root "$APP_ROOT" --display-name "$APP_DISPLAY_NAME" --icon "$ROOT/assets/unofficial-chat-icon.png"
python3 "$ROOT/scripts/generate_build_config.py" \
  --template "$UPSTREAM/build-system/template_minimal_development_configuration.json" \
  --upstream-root "$UPSTREAM" \
  --minimum-ios-version "15.5" \
  --output "$CONFIG"
python3 "$ROOT/scripts/enable_unsigned_device_build.py" \
  --make-script "$UPSTREAM/build-system/Make/Make.py" \
  --rules-apple-root "$UPSTREAM/build-system/bazel-rules/rules_apple"

rm -rf "$BUILD_ARTIFACTS" "$OUTPUT"
mkdir -p "$BUILD_ARTIFACTS" "$OUTPUT"
if [[ -f "$RUNNER_TEMP/MLKit-Podfile.lock" ]]; then
  cp "$RUNNER_TEMP/MLKit-Podfile.lock" "$OUTPUT/MLKit-Podfile.lock"
fi

cd "$UPSTREAM"
python3 -u build-system/Make/Make.py \
  --cacheDir="$HOME/telegram-bazel-cache" \
  build \
  --configurationPath="$CONFIG" \
  --xcodeManagedCodesigning \
  --disableProvisioningProfiles \
  --configuration=release_arm64 \
  --buildNumber="$BUILD_NUMBER" \
  --outputBuildArtifactsPath="$BUILD_ARTIFACTS"

python3 "$ROOT/scripts/package_unsigned_ipa.py" \
  --input-ipa "$BUILD_ARTIFACTS/Telegram.ipa" \
  --output-ipa "$OUTPUT/UnofficialChat-unsigned.ipa" \
  --extra-resources "$UPSTREAM/submodules/CueChatAutomation/MLKitVendor/Resources" \
  --base-bundle-id "$APP_BUNDLE_ID" \
  --bundle-id "$APP_BUNDLE_ID" \
  --display-name "$APP_DISPLAY_NAME"

python3 "$ROOT/scripts/validate_unsigned_ipa.py" \
  --ipa "$OUTPUT/UnofficialChat-unsigned.ipa" \
  --bundle-id "$APP_BUNDLE_ID" \
  --report "$OUTPUT/unsigned-ipa-validation.json"
