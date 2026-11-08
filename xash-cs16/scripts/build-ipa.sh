#!/usr/bin/env bash
# Build an ad-hoc-signed Xash3D FWGS + CS 1.6 iOS arm64 IPA.
# Steam game assets are not downloaded or packaged. Resign with 全能签 before installing.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
WORK="${WORK_DIR:-${RUNNER_TEMP:-/tmp}/xash-cs16-ios-build}"
DIST="${DIST_DIR:-$ROOT/dist}"

XASH_REF="${XASH_REF:-e9b94dc1a89bcd8867e2d16b37cd6f1cbd4dbd1c}"
CS16_REF="${CS16_REF:-8ae1ebe2764c016669d381591ea778c7c9e86f51}"
HLSDK_REF="${HLSDK_REF:-7ec223cfd29e0c20d8e52927dcc3d0c27d9ca7ac}"
SDL_REF="${SDL_REF:-cee83f2d9a916e9de30c5712e798541fdc134b06}"
FREETYPE_REF="${FREETYPE_REF:-c4a3c188e82bc5b457390a87630ac782316421a1}"

XASH_URL="${XASH_URL:-https://github.com/FWGS/xash3d-fwgs.git}"
CS16_URL="${CS16_URL:-https://github.com/FWGS/cs16-client.git}"
HLSDK_URL="${HLSDK_URL:-https://github.com/FWGS/hlsdk-portable.git}"
SDL_URL="${SDL_URL:-https://github.com/libsdl-org/SDL.git}"
FREETYPE_URL="${FREETYPE_URL:-https://github.com/freetype/freetype.git}"

export COPYFILE_DISABLE=1
export GIT_TERMINAL_PROMPT=0

log() { printf '\n==> %s\n' "$*"; }

fetch_pin() {
	local url="$1" dest="$2" rev="$3" with_submodules="${4:-}"
	rm -rf "$dest"
	git init "$dest"
	git -C "$dest" remote add origin "$url"
	if ! git -C "$dest" fetch --depth 1 origin "$rev"; then
		log "shallow fetch of $rev failed; fetching the commit without a depth limit"
		git -C "$dest" fetch origin "$rev"
	fi
	git -C "$dest" checkout --detach FETCH_HEAD
	if [[ "$with_submodules" == "submodules" ]]; then
		git -C "$dest" submodule update --init --recursive
	fi
}

require_cmd() {
	if ! command -v "$1" >/dev/null 2>&1; then
		echo "missing required command: $1" >&2
		exit 1
	fi
}

log "toolchains"
require_cmd git
require_cmd python3
require_cmd cmake
require_cmd xcodebuild
require_cmd codesign
require_cmd zip
xcodebuild -version
xcrun --sdk iphoneos --show-sdk-path
SDK="$(xcrun --sdk iphoneos --show-sdk-path)"
JOBS="$(sysctl -n hw.ncpu)"

mkdir -p "$WORK" "$DIST"

log "SDL2.framework ($SDL_REF)"
fetch_pin "$SDL_URL" "$WORK/SDL" "$SDL_REF"
SDL_BUILD="$WORK/SDL/ios-build"
rm -rf "$SDL_BUILD"
xcodebuild \
	-project "$WORK/SDL/Xcode/SDL/SDL.xcodeproj" \
	-target Framework-iOS \
	-configuration Release \
	-sdk iphoneos \
	ARCHS=arm64 \
	ONLY_ACTIVE_ARCH=NO \
	CODE_SIGNING_ALLOWED=NO \
	CODE_SIGNING_REQUIRED=NO \
	BUILD_DIR="$SDL_BUILD"
SDL_FRAMEWORK="$SDL_BUILD/Release-iphoneos/SDL2.framework"
if [[ ! -d "$SDL_FRAMEWORK" ]]; then
	echo "SDL2.framework was not produced at $SDL_FRAMEWORK" >&2
	find "$SDL_BUILD" -name 'SDL2.framework' -maxdepth 4 -print >&2 || true
	exit 1
fi

log "sources"
fetch_pin "$XASH_URL" "$WORK/xash3d-fwgs" "$XASH_REF" submodules
fetch_pin "$CS16_URL" "$WORK/cs16-client" "$CS16_REF" submodules
fetch_pin "$HLSDK_URL" "$WORK/hlsdk-portable" "$HLSDK_REF" submodules
# nanogl is marked update=none, but the iOS GLES renderer will not configure without it.
git -C "$WORK/xash3d-fwgs" submodule update --init --checkout 3rdparty/nanogl
if [[ ! -d "$WORK/xash3d-fwgs/3rdparty/freetype/freetype/src" ]]; then
	log "FreeType ($FREETYPE_REF)"
	fetch_pin "$FREETYPE_URL" "$WORK/xash3d-fwgs/3rdparty/freetype/freetype" "$FREETYPE_REF"
fi

log "iOS library names, bundle gamedll lookup, CS launch args"
python3 "$ROOT/scripts/apply_patches.py" --xash "$WORK/xash3d-fwgs" --cs16 "$WORK/cs16-client"

XASH_SRC="$WORK/xash3d-fwgs"
log "configure and build engine"
cp -R "$SDL_FRAMEWORK" "$XASH_SRC/SDL2.framework"
(
	cd "$XASH_SRC"
	chmod +x ./waf
	./waf configure --ios --enable-bundled-deps --disable-werror -T release --sdl2="$XASH_SRC/SDL2.framework"
	./waf build -j"$JOBS"
)

log "Half-Life client/server libs"
LIBSDIR="$XASH_SRC/build/ios/libs"
mkdir -p "$LIBSDIR"
cmake -S "$WORK/hlsdk-portable" -B "$WORK/hlsdk-build" \
	-DCMAKE_SYSTEM_NAME=iOS \
	-DCMAKE_OSX_ARCHITECTURES=arm64 \
	-DCMAKE_OSX_SYSROOT="$SDK" \
	-DCMAKE_OSX_DEPLOYMENT_TARGET=12.0 \
	-DCMAKE_BUILD_TYPE=Debug \
	-D64BIT=ON \
	-DGAMEDIR=valve \
	-DCMAKE_INSTALL_PREFIX="$LIBSDIR"
cmake --build "$WORK/hlsdk-build" --config Debug --target install -j"$JOBS"

log "cs16-client"
cmake -S "$WORK/cs16-client" -B "$WORK/cs16-build" \
	-DCMAKE_SYSTEM_NAME=iOS \
	-DCMAKE_OSX_ARCHITECTURES=arm64 \
	-DCMAKE_OSX_SYSROOT="$SDK" \
	-DCMAKE_OSX_DEPLOYMENT_TARGET=12.0 \
	-DCMAKE_BUILD_TYPE=Debug \
	-DMAC=0 \
	-DXASH_COMPAT=ON \
	-DMAINUI_USE_STB=ON \
	-DGAME_DIR=cstrike \
	-DGAMEDIR=cstrike \
	-DCLIENT_INSTALL_DIR=cl_dlls \
	-DSERVER_INSTALL_DIR=dlls \
	-DYAPB_WITH_TLS=OFF \
	-DYAPB_LTO=OFF
cmake --build "$WORK/cs16-build" --config Debug -j"$JOBS"
cmake --install "$WORK/cs16-build" --prefix "$LIBSDIR"

log "installed libraries"
find "$LIBSDIR" -type f \( -name '*.dylib' -o -name '*.pk3' \) -print | sort

CS_DLLS="$LIBSDIR/cstrike/dlls"
if [[ -f "$CS_DLLS/cs_ios_arm64.dylib" ]]; then
	cp -f "$CS_DLLS/cs_ios_arm64.dylib" "$CS_DLLS/cs_arm64.dylib"
elif [[ -f "$CS_DLLS/cs_arm64.dylib" ]]; then
	cp -f "$CS_DLLS/cs_arm64.dylib" "$CS_DLLS/cs_ios_arm64.dylib"
else
	echo "cs server library was not installed into $CS_DLLS" >&2
	exit 1
fi
for required in \
	"$LIBSDIR/cstrike/cl_dlls/client_ios_arm64.dylib" \
	"$LIBSDIR/cstrike/cl_dlls/menu_ios_arm64.dylib" \
	"$LIBSDIR/cstrike/dlls/yapb_ios_arm64.dylib" \
	"$LIBSDIR/cstrike/dlls/cs_ios_arm64.dylib" \
	"$LIBSDIR/cstrike/dlls/cs_arm64.dylib" \
	"$LIBSDIR/cstrike/extras.pk3" \
	"$LIBSDIR/valve/cl_dlls/client_ios_arm64.dylib" \
	"$LIBSDIR/valve/dlls/hl_ios_arm64.dylib"
do
	if [[ ! -f "$required" ]]; then
		echo "missing built library: $required" >&2
		exit 1
	fi
	if [[ "$required" == *.dylib ]]; then
		lipo -info "$required"
	fi
done

log "assemble .app"
APP="$XASH_SRC/build/ios/Payload/xash3d.app"
rm -rf "$XASH_SRC/build/ios/Payload"
mkdir -p "$APP"
cp -R "$LIBSDIR"/. "$APP"/
cp -R "$SDL_FRAMEWORK" "$APP/SDL2.framework"
(
	cd "$XASH_SRC"
	./waf install --destdir="$APP"
)
cp "$XASH_SRC/engine/platform/ios/bundle/Info.plist" "$APP/Info.plist"
if plutil -extract UILaunchStoryboardName raw "$APP/Info.plist" >/dev/null 2>&1; then
	plutil -remove UILaunchStoryboardName "$APP/Info.plist"
fi

log "sign nested code, then the app"
sign_one() {
	codesign --force --sign - --timestamp=none "$1"
}
while IFS= read -r -d '' bin; do
	install_name_tool -id "@rpath/$(basename "$bin")" "$bin" || true
	sign_one "$bin"
done < <(find "$APP" -type f \( -name '*.dylib' -o -name '*.so' \) -print0)
if [[ -d "$APP/SDL2.framework" ]]; then
	sign_one "$APP/SDL2.framework"
fi
ENT="$XASH_SRC/engine/platform/ios/bundle/entitlements.plist"
if ! codesign --force --sign - --timestamp=none --entitlements "$ENT" "$APP"; then
	log "upstream entitlements rejected for ad-hoc sign; signing without a team id"
	MIN="$WORK/adhoc.entitlements"
	cat >"$MIN" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
	<key>get-task-allow</key>
	<false/>
</dict></plist>
EOF
	codesign --force --sign - --timestamp=none --entitlements "$MIN" "$APP"
fi
codesign --verify --verbose=2 "$APP"

log "package IPA"
IPA="$DIST/xash3d-fwgs-cs16-ios-arm64.ipa"
DYLIBS="$DIST/xash3d-fwgs-cs16-ios-arm64-dylibs.zip"
rm -f "$IPA" "$DYLIBS"
(
	cd "$XASH_SRC/build/ios"
	zip -qr -X "$IPA" Payload -x '*.DS_Store'
)
(
	cd "$LIBSDIR"
	zip -qr -X "$DYLIBS" cstrike -x '*.DS_Store'
)

python3 - "$IPA" "$XASH_REF" "$CS16_REF" "$HLSDK_REF" "$SDL_REF" "$FREETYPE_REF" "$DIST/build-manifest.json" <<'PY'
import json, sys
from pathlib import Path
ipa, xash, cs16, hlsdk, sdl, freetype, manifest = sys.argv[1:]
Path(manifest).write_text(json.dumps({
    "ipa": Path(ipa).name,
    "xash3d_fwgs": xash,
    "cs16_client": cs16,
    "hlsdk_portable_mobile_hacks": hlsdk,
    "sdl2": sdl,
    "freetype": freetype,
    "launch": "-game cstrike -dll @yapb",
    "game_data_included": False,
}, indent=2) + "\n")
PY

python3 - "$IPA" <<'PY'
import sys, zipfile
ipa = zipfile.ZipFile(sys.argv[1])
names = ipa.namelist()
need = [
    "cstrike/cl_dlls/client_ios_arm64.dylib",
    "cstrike/cl_dlls/menu_ios_arm64.dylib",
    "cstrike/dlls/yapb_ios_arm64.dylib",
    "cstrike/dlls/cs_ios_arm64.dylib",
    "cstrike/dlls/cs_arm64.dylib",
    "cstrike/extras.pk3",
    "valve/cl_dlls/client_ios_arm64.dylib",
    "valve/dlls/hl_ios_arm64.dylib",
    "xash",
]
missing = [rel for rel in need if not any(n.endswith("/" + rel) for n in names)]
banned = [n for n in names if n.lower().endswith(".bsp") or n.lower().endswith(".dll")]
if missing or banned:
    print("MISSING", missing)
    print("BANNED", banned[:20])
    raise SystemExit(1)
print("IPA contains the CS libraries and no Valve maps or original dlls")
for n in sorted(names):
    if n.endswith(".dylib") or n.endswith("/xash") or n.endswith(".pk3"):
        print(n)
PY

log "done: $IPA"
ls -lh "$IPA" "$DYLIBS"
