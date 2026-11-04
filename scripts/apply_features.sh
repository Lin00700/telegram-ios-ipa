#!/usr/bin/env bash
# Feature overlay on top of a pinned Telegram-iOS checkout.
# Called only when INK_STAGE=features. Each step fails closed if upstream drifts.
set -euo pipefail

UPSTREAM="${1:?upstream checkout}"
ROOT="${2:?repo root}"
APP_ROOT="$UPSTREAM/Telegram/Telegram-iOS"

mkdir -p "$APP_ROOT/Resources"
cp "$ROOT/assets/cf-inkwash-global.png" "$APP_ROOT/Resources/ChatWallpaperBuiltin0.png"

python3 "$ROOT/scripts/apply_inkwash_theme.py" --upstream "$UPSTREAM"
python3 "$ROOT/scripts/apply_inkwash_components.py" --upstream "$UPSTREAM"
python3 "$ROOT/scripts/apply_global_wallpaper.py" --upstream "$UPSTREAM"
python3 "$ROOT/scripts/apply_ink_features.py" --upstream "$UPSTREAM" --repo-root "$ROOT"
