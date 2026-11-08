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

LAUNCH_LANG_OLD = """\t\tif (ret && ( settings.magic == SETTINGS_MAGIC ))
\t\t{
\t\t\t[textField setText:@(settings.args)];
\t\t}
\t\telse
\t\t{
\t\t\t[textField setText:@"-dev 2 -log"];
\t\t}"""

LAUNCH_LANG_NEW = """\t\tif (ret && ( settings.magic == SETTINGS_MAGIC ))
\t\t{
\t\t\t[textField setText:IOS_WithSystemLanguage( @(settings.args) )];
\t\t}
\t\telse
\t\t{
\t\t\t[textField setText:IOS_WithSystemLanguage( @"-game cstrike -dll @yapb" )];
\t\t}"""

LAUNCH_HELPER_OLD = "void IOS_LaunchDialog( void )\n{"
LAUNCH_HELPER_NEW = """// Chinese phones get -language schinese (traditional: tchinese) in the
// launch box. -language english stays English. The engine already mounts
// <gamedir>_<language>/ when that flag is present.
static NSString *IOS_WithSystemLanguage( NSString *options )
{
	NSString *pref;
	NSString *lang = nil;

	if( options == nil )
		options = @"";
	if( [options rangeOfString:@"-language"].location != NSNotFound )
		return options;

	pref = [NSLocale preferredLanguages].firstObject;
	if( [pref hasPrefix:@"zh-Hant"] || [pref hasPrefix:@"zh-TW"] || [pref hasPrefix:@"zh-HK"] || [pref hasPrefix:@"zh-MO"] )
		lang = @"tchinese";
	else if( [pref hasPrefix:@"zh"] )
		lang = @"schinese";

	if( lang == nil )
		return options;
	if( options.length == 0 )
		return [NSString stringWithFormat:@"-language %@", lang];
	return [options stringByAppendingFormat:@" -language %@", lang];
}

void IOS_LaunchDialog( void )
{"""

VIDMODE_OLD = """\t\twidth = DEFAULT_MODE_WIDTH;
\t\theight = DEFAULT_MODE_HEIGHT;
#endif
\t}

#if XASH_MOBILE_PLATFORM"""

VIDMODE_NEW = """\t\twidth = DEFAULT_MODE_WIDTH;
\t\theight = DEFAULT_MODE_HEIGHT;
#endif
\t}

#if XASH_IOS
\t// The window is the display. A width/height saved by a build that iOS
\t// letterboxed at the legacy 3:2 size must not stick.
\t{
\t\tSDL_DisplayMode desktop;

\t\tif( SDL_GetDesktopDisplayMode( 0, &desktop ) == 0
\t\t\t&& desktop.w >= VID_MIN_WIDTH && desktop.h >= VID_MIN_HEIGHT )
\t\t{
\t\t\twidth = desktop.w;
\t\t\theight = desktop.h;
\t\t\tif( height > width )
\t\t\t{
\t\t\t\tint swap = width;
\t\t\t\twidth = height;
\t\t\t\theight = swap;
\t\t\t}
\t\t}
\t}
#endif

#if XASH_MOBILE_PLATFORM"""

HINT_OLD = """\tSDL_SetHint( SDL_HINT_ANDROID_BLOCK_ON_PAUSE, "0" );
\tSDL_SetHint( SDL_HINT_ANDROID_BLOCK_ON_PAUSE_PAUSEAUDIO, "0" );"""

HINT_NEW = """\tSDL_SetHint( SDL_HINT_ANDROID_BLOCK_ON_PAUSE, "0" );
\tSDL_SetHint( SDL_HINT_ANDROID_BLOCK_ON_PAUSE_PAUSEAUDIO, "0" );
#if XASH_IOS
\t// Game pixels cover the screen. Touch buttons still use the safe area.
\tSDL_SetHint( SDL_HINT_IOS_HIDE_HOME_INDICATOR, "2" );
#endif"""

FONT_OLD = """bool CFontManager::FindFontDataFile( const char *name, int tall, int weight, int flags, char *dataFile, size_t dataFileChars )
{
\tif( !strcmp( name, "Trebuchet MS" ))"""

FONT_NEW = """bool CFontManager::FindFontDataFile( const char *name, int tall, int weight, int flags, char *dataFile, size_t dataFileChars )
{
\t// User-supplied TrueType face on the game path:
\t// cstrike/gfx/fonts/chinese.ttf or valve/gfx/fonts/chinese.ttf.
\tif( EngFuncs::FileExists( "gfx/fonts/chinese.ttf", false ))
\t{
\t\tQ_strncpy( dataFile, "gfx/fonts/chinese.ttf", dataFileChars );
\t\treturn true;
\t}

\tif( !strcmp( name, "Trebuchet MS" ))"""

PICBUTTON_TEXT_OLD = "\tuiStatic.renderPicbuttonText = gMenu.m_gameinfo.flags & GFL_RENDER_PICBUTTON_TEXT;"

PICBUTTON_TEXT_NEW = """\tuiStatic.renderPicbuttonText = gMenu.m_gameinfo.flags & GFL_RENDER_PICBUTTON_TEXT;
\t// Main-menu labels are English bitmaps from the game files. A CJK face
\t// cannot retint those pictures, so draw the localized strings instead.
\tif( EngFuncs::FileExists( "gfx/fonts/chinese.ttf", false ))
\t\tuiStatic.renderPicbuttonText = true;"""

STATUS_OLD = """\t\tint\tr, g, b;

\t\tUnpackRGB( r, g, b, uiColorHelp );
\t\tEngFuncs::DrawSetTextColor( r, g, b );
\t\tEngFuncs::DrawConsoleString( coord, szStatusText );"""

STATUS_NEW = """\t\tif( uiStatic.renderPicbuttonText )
\t\t{
\t\t\tint charH = (int)( UI_SMALL_CHAR_HEIGHT * uiStatic.scaleY );
\t\t\tSize area( 4096, charH + 8 );

\t\t\tif( charH < 1 )
\t\t\t\tcharH = UI_SMALL_CHAR_HEIGHT;
\t\t\t// Console glyphs have no CJK. The menu face does when chinese.ttf is present.
\t\t\tUI_DrawString( uiStatic.hSmallFont, coord, area, szStatusText, uiColorHelp, charH, QM_LEFT, ETF_NOSIZELIMIT | ETF_FORCECOL );
\t\t}
\t\telse
\t\t{
\t\t\tint\tr, g, b;

\t\t\tUnpackRGB( r, g, b, uiColorHelp );
\t\t\tEngFuncs::DrawSetTextColor( r, g, b );
\t\t\tEngFuncs::DrawConsoleString( coord, szStatusText );
\t\t}"""

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

YAPB_PROC_OLD = """set(_PROC "${CMAKE_SYSTEM_PROCESSOR}")
if(_PROC MATCHES "^(arm64|ARM64)$")
  set(_PROC "aarch64")
endif()"""

YAPB_PROC_NEW = """set(_PROC "${CMAKE_SYSTEM_PROCESSOR}")
# The iOS toolchain still reports the Mac host processor. That selects x86
# march/SSE flags and a macOS deployment target, which cannot link an arm64 device dylib.
if(CMAKE_SYSTEM_NAME STREQUAL "iOS")
  set(_PROC "aarch64")
elseif(_PROC MATCHES "^(arm64|ARM64)$")
  set(_PROC "aarch64")
endif()"""

YAPB_WERROR_OLD = """  if(NOT VITA AND NOT CMAKE_SYSTEM_NAME MATCHES "Emscripten")
    list(APPEND _strict_cflags -Wall -Wextra -Wpedantic -Werror)
  endif()"""

YAPB_WERROR_NEW = """  if(NOT VITA AND NOT CMAKE_SYSTEM_NAME MATCHES "Emscripten" AND NOT CMAKE_SYSTEM_NAME STREQUAL "iOS")
    list(APPEND _strict_cflags -Wall -Wextra -Wpedantic -Werror)
  endif()"""

YAPB_APPLE_OLD = """  elseif(APPLE)
    if(IS_ZIG)"""

YAPB_APPLE_NEW = """  elseif(APPLE AND NOT CMAKE_SYSTEM_NAME STREQUAL "iOS")
    if(IS_ZIG)"""

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
    replace_once(launch, LAUNCH_HELPER_OLD, LAUNCH_HELPER_NEW, "system language launch args")
    replace_once(launch, LAUNCH_LANG_OLD, LAUNCH_LANG_NEW, "default launch args and system language")

    vid = xash / "engine/platform/sdl2/vid_sdl2.c"
    sys_sdl = xash / "engine/platform/sdl2/sys_sdl2.c"
    replace_once(vid, VIDMODE_OLD, VIDMODE_NEW, "iOS native video size")
    replace_once(sys_sdl, HINT_OLD, HINT_NEW, "iOS home indicator hint")

    mainui = cs16 / "3rdparty/mainui_cpp"
    replace_once(mainui / "font/FontManager.cpp", FONT_OLD, FONT_NEW, "user CJK menu font")
    replace_once(mainui / "BaseMenu.cpp", PICBUTTON_TEXT_OLD, PICBUTTON_TEXT_NEW, "text menu buttons when a CJK font is present")
    replace_once(mainui / "controls/PicButton.cpp", STATUS_OLD, STATUS_NEW, "menu status text through the vector font")

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
    replace_once(cs16 / "3rdparty/yapb/CMakeLists.txt", YAPB_PROC_OLD, YAPB_PROC_NEW, "YaPB iOS architecture")
    flags = cs16 / "3rdparty/yapb/cmake/YapbFlags.cmake"
    replace_once(flags, YAPB_WERROR_OLD, YAPB_WERROR_NEW, "YaPB iOS warnings")
    replace_once(flags, YAPB_APPLE_OLD, YAPB_APPLE_NEW, "YaPB iOS deployment target")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--xash", type=Path, required=True)
    parser.add_argument("--cs16", type=Path, required=True)
    args = parser.parse_args()
    patch_tree(args.xash, args.cs16)
    return 0


if __name__ == "__main__":
    sys.exit(main())
