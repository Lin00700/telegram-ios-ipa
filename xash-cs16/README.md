# Xash3D FWGS + CS 1.6 for iOS

Build scripts for a self-signed iPhone IPA of [Xash3D FWGS](https://github.com/FWGS/xash3d-fwgs) with the open-source [cs16-client](https://github.com/FWGS/cs16-client) libraries (client, menu, ReGameDLL, and YaPB).

This repository does **not** contain Counter-Strike or Half-Life game data, and the IPA does not either. Copy `valve` and `cstrike` from your own Steam install after you sign and install the app. Chinese steps for 全能签 are in [INSTALL.md](INSTALL.md).

The engine on iOS loads `client_ios_arm64.dylib`, `menu_ios_arm64.dylib`, and `yapb_ios_arm64.dylib`. Stock cs16-client CMake treats iOS as macOS and emits `*_arm64` names, which the engine will not load. The workflow patches that postfix. YaPB still opens `cs_arm64.dylib`, so the IPA also contains that filename beside `cs_ios_arm64.dylib`. Both copies are inside the `.app` and signed with it. A YaPB patch loads the sibling from the app bundle, because an unsigned copy under Documents usually fails iOS library validation.

First launch fills the engine dialog with `-game cstrike -dll @yapb`.

## Build

GitHub Actions, workflow **Build CS 1.6 iOS IPA**, runner `macos-latest`. The artifact is `xash3d-fwgs-cs16-ios-arm64.ipa` plus `xash3d-fwgs-cs16-ios-arm64-dylibs.zip`. The signature is ad-hoc. 全能签 replaces it with your own certificate.

Pinned upstream commits are the defaults in `scripts/build-ipa.sh`.

## Upstream

- Engine and iOS packaging: FWGS/xash3d-fwgs `scripts/ios`
- Half-Life libraries: FWGS/hlsdk-portable branch `mobile_hacks`
- CS libraries: FWGS/cs16-client, including YaPB, ReGameDLL_CS, and mainui_cpp
- SDL2 iOS framework

The built app is a derivative of those GPL and other upstream licenses. This packaging repository only holds the workflow, the build script, and the small patches applied at build time.
