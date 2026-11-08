#!/usr/bin/env python3
"""Apply the iOS library-name and bundle-load patches to pinned upstream trees."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

LIBRARY_OLD = """if(XASH_ANDROID)
	set(BUILDOS "android")
elseif(XASH_WIN32 OR XASH_LINUX OR XASH_APPLE)
	set(BUILDOS "") # no prefix for default OS"""

LIBRARY_NEW = """# iOS matches XASH_APPLE, so an unpatched file emits macOS names such as
# client_arm64.dylib. Xash on iOS only loads the ios postfix (client_ios_arm64).
if(XASH_IOS OR CMAKE_SYSTEM_NAME STREQUAL "iOS")
	set(BUILDOS "ios")
elseif(XASH_ANDROID)
	set(BUILDOS "android")
elseif(XASH_WIN32 OR XASH_LINUX OR XASH_APPLE)
	set(BUILDOS "") # no prefix for default OS"""

LAUNCH_OLD = '[textField setText:@"-dev 2 -log"];'
LAUNCH_NEW = '[textField setText:@"-game cstrike -dll @yapb"];'

YAPB_INCLUDE_OLD = "#include <yapb.h>\n"
YAPB_INCLUDE_NEW = """#include <yapb.h>
#if defined(__APPLE__)
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#endif
"""

YAPB_ANCHOR_OLD = "bool Game::LoadCsBinary () {\n"
YAPB_ANCHOR_NEW = """#if defined(__APPLE__)
// dladdr needs a real address in this image. iOS rejects dylibs that were
// copied into Documents, so YaPB has to open the signed sibling inside the .app.
static void YapbModuleAnchor() {}
#endif

bool Game::LoadCsBinary () {
"""

YAPB_LOAD_OLD = """    if (path.empty ()) {
      path = ystl::strings.join_path (modname, "dlls", lib) + kLibrarySuffix;

      // if we can't read file, skip it
      if (!ystl::plat.file_exists (path.chars ())) {
        continue;
      }
    }"""

YAPB_LOAD_NEW = """    if (path.empty ()) {
      path = ystl::strings.join_path (modname, "dlls", lib) + kLibrarySuffix;

      // if we can't read file, skip it
      if (!ystl::plat.file_exists (path.chars ())) {
#if defined(__APPLE__)
        Dl_info info {};
        ystl::String bundledName = lib + kLibrarySuffix;
        char bundled[1024];
        const char *image = nullptr;
        const char *slash = nullptr;
        if (dladdr (reinterpret_cast<const void *> (&YapbModuleAnchor), &info) != 0)
          image = info.dli_fname;
        if (image != nullptr)
          slash = strrchr (image, '/');
        if (slash != nullptr) {
          const int dirlen = static_cast<int> (slash - image);
          snprintf (bundled, sizeof (bundled), "%.*s/%s", dirlen, image, bundledName.chars ());
          if (ystl::plat.file_exists (bundled))
            path = ystl::String (bundled);
          else
            continue;
        } else {
          continue;
        }
#else
        continue;
#endif
      }
    }"""


def replace_once(path: Path, old: str, new: str, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text:
        print(f"already patched: {path} ({label})")
        return
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{path}: expected 1 {label} site, found {count}")
    path.write_text(text.replace(old, new, 1), encoding="utf-8")
    print(f"patched: {path} ({label})")


def patch_library_naming(path: Path) -> None:
    if not path.is_file():
        raise SystemExit(f"missing LibraryNaming.cmake: {path}")
    replace_once(path, LIBRARY_OLD, LIBRARY_NEW, "iOS library postfix")


def patch_tree(xash: Path, cs16: Path) -> None:
    launch = xash / "engine/platform/ios/launchdialog.m"
    if not launch.is_file():
        raise SystemExit(f"missing launch dialog: {launch}")
    replace_once(launch, LAUNCH_OLD, LAUNCH_NEW, "default launch args")

    naming = [
        cs16 / "cmake/LibraryNaming.cmake",
        cs16 / "3rdparty/ReGameDLL_CS/regamedll/cmake/LibraryNaming.cmake",
    ]
    for path in naming:
        patch_library_naming(path)

    engine = cs16 / "3rdparty/yapb/src/engine.cpp"
    if not engine.is_file():
        raise SystemExit(f"missing YaPB engine.cpp (init submodules first): {engine}")
    replace_once(engine, YAPB_INCLUDE_OLD, YAPB_INCLUDE_NEW, "YaPB Apple headers")
    replace_once(engine, YAPB_ANCHOR_OLD, YAPB_ANCHOR_NEW, "YaPB image anchor")
    replace_once(engine, YAPB_LOAD_OLD, YAPB_LOAD_NEW, "YaPB bundle gamedll lookup")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xash", type=Path, required=True)
    parser.add_argument("--cs16", type=Path, required=True)
    args = parser.parse_args()
    patch_tree(args.xash, args.cs16)
    return 0


if __name__ == "__main__":
    sys.exit(main())
