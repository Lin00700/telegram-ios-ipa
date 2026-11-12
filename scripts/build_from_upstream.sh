#!/usr/bin/env bash
# Build an unsigned Telegram iOS IPA from a recursive upstream checkout.
# INK_STAGE=baseline  — upstream sources, resign compatibility only
# INK_STAGE=features  — baseline plus the 水墨增强 overlay
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
UPSTREAM="${UPSTREAM_DIR:-$ROOT/upstream}"
APP_ROOT="$UPSTREAM/Telegram/Telegram-iOS"
CONFIG="${RUNNER_TEMP:-/tmp}/telegram-build-config.json"
BUILD_ARTIFACTS="${RUNNER_TEMP:-/tmp}/telegram-build-artifacts"
OUTPUT="$ROOT/artifacts"
STAGE="${INK_STAGE:-baseline}"
APP_DISPLAY_NAME="${APP_DISPLAY_NAME:-水墨}"
BUILD_NUMBER="${BUILD_NUMBER:-0}"

: "${APP_BUNDLE_ID:?Missing APP_BUNDLE_ID}"

if [[ ! -d "$UPSTREAM/.git" || ! -f "$UPSTREAM/.gitmodules" ]]; then
  echo "Expected a recursive checkout of TelegramMessenger/Telegram-iOS at $UPSTREAM" >&2
  exit 1
fi

if [[ -z "${TG_API_ID:-}" || -z "${TG_API_HASH:-}" ]]; then
  echo "ERROR: GitHub Actions secrets TG_API_ID and TG_API_HASH are not configured." >&2
  echo "ERROR: Continuing with compile-only placeholders. This IPA cannot log in to Telegram." >&2
  unset TG_API_ID TG_API_HASH
fi

# Upstream embeds absolute source paths in the binary. Keep them stable.
CANONICAL="/Users/Shared/telegram-ios"
if [[ "$(uname -s)" == "Darwin" ]]; then
  sudo rm -rf "$CANONICAL"
  sudo mkdir -p "$(dirname "$CANONICAL")"
  sudo ditto "$UPSTREAM" "$CANONICAL"
  sudo chown -R "$(id -un)" "$CANONICAL"
  UPSTREAM="$CANONICAL"
  APP_ROOT="$UPSTREAM/Telegram/Telegram-iOS"
fi

python3 "$ROOT/scripts/apply_resign_compat.py" --upstream "$UPSTREAM"

if [[ "$STAGE" == "features" ]]; then
  bash "$ROOT/scripts/apply_features.sh" "$UPSTREAM" "$ROOT"
elif [[ "$STAGE" != "baseline" ]]; then
  echo "Unknown INK_STAGE: $STAGE" >&2
  exit 1
fi

python3 "$ROOT/scripts/apply_branding.py" \
  --app-root "$APP_ROOT" \
  --display-name "$APP_DISPLAY_NAME" \
  --icon "$ROOT/assets/unofficial-chat-icon.png"

mkdir -p "$OUTPUT"
python3 "$ROOT/scripts/generate_build_config.py" \
  --template "$UPSTREAM/build-system/template_minimal_development_configuration.json" \
  --output "$CONFIG" \
  --notice "$OUTPUT/credentials-notice.txt" \
  --allow-placeholder

python3 "$ROOT/scripts/enable_unsigned_device_build.py" \
  --make-script "$UPSTREAM/build-system/Make/Make.py" \
  --rules-apple-root "$UPSTREAM/build-system/bazel-rules/rules_apple"

rm -rf "$BUILD_ARTIFACTS"
mkdir -p "$BUILD_ARTIFACTS"

cd "$UPSTREAM"
python3 -u build-system/Make/Make.py \
  --cacheDir="${HOME}/telegram-bazel-cache" \
  build \
  --configurationPath="$CONFIG" \
  --xcodeManagedCodesigning \
  --disableProvisioningProfiles \
  --configuration=release_arm64 \
  --buildNumber="$BUILD_NUMBER" \
  --outputBuildArtifactsPath="$BUILD_ARTIFACTS"

python3 "$ROOT/scripts/package_unsigned_ipa.py" \
  --input-ipa "$BUILD_ARTIFACTS/Telegram.ipa" \
  --output-ipa "$OUTPUT/Shuimo-unsigned.ipa" \
  --base-bundle-id "$APP_BUNDLE_ID" \
  --bundle-id "$APP_BUNDLE_ID" \
  --display-name "$APP_DISPLAY_NAME" \
  --contents-report "$OUTPUT/ipa-contents.json"

python3 "$ROOT/scripts/validate_unsigned_ipa.py" \
  --ipa "$OUTPUT/Shuimo-unsigned.ipa" \
  --bundle-id "$APP_BUNDLE_ID" \
  --report "$OUTPUT/unsigned-ipa-validation.json"

python3 "$ROOT/scripts/write_install_report.py" \
  --contents "$OUTPUT/ipa-contents.json" \
  --validation "$OUTPUT/unsigned-ipa-validation.json" \
  --notice "$OUTPUT/credentials-notice.txt" \
  --stage "$STAGE" \
  --output "$OUTPUT/INSTALL.md"
