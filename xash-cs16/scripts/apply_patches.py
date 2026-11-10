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


GLYPHS_OLD = """void CFontManager::UploadTextureForFont(CBaseFont *font)
{
	// upload only latin needed for english and cyrillic needed for russian
	// maybe it would be extended someday...

	charRange_t range[] =
	{
	{ 0x0021, 0x007E, NULL, 0 }, // ascii printable range
	{ 0x00C0, 0x00FF, NULL, 0 }, // latin-1 supplement (letters only)
	{ 0x0100, 0x017F, NULL, 0 }, // latin extended a
	{ 0x0400, 0x045F, NULL, 0 }, // cyrillic range
	{ 0, 0, table_cp1251, V_ARRAYSIZE( table_cp1251 ) }, // cp1251
	};

	font->UploadGlyphsForRanges( range, V_ARRAYSIZE( range ) );
}"""

GLYPHS_NEW = """#include "menu_glyphs.inc"

void CFontManager::UploadTextureForFont(CBaseFont *font)
{
	// Latin and Cyrillic stay in every face. Menu CJK is baked only into the
	// plain faces: the blurred copies are the English glow and are not used
	// once the labels are real strings.
	charRange_t range[] =
	{
	{ 0x0021, 0x007E, NULL, 0 }, // ascii printable range
	{ 0x00C0, 0x00FF, NULL, 0 }, // latin-1 supplement (letters only)
	{ 0x0100, 0x017F, NULL, 0 }, // latin extended a
	{ 0x0400, 0x045F, NULL, 0 }, // cyrillic range
	{ 0, 0, table_cp1251, V_ARRAYSIZE( table_cp1251 ) }, // cp1251
	{ 0, 0, NULL, 0 }, // optional menu CJK, filled below
	};
	int count = (int)(sizeof( range ) / sizeof( range[0] )) - 1;

	if( font->m_iBlur == 0 )
	{
		range[count].sequence = kMenuGlyphs;
		range[count].size = V_ARRAYSIZE( kMenuGlyphs );
		count++;
	}

	font->UploadGlyphsForRanges( range, count );
}"""

FS_DECL_OLD = """bool FileSystem_Init();
void FileSystem_Shutdown();"""

FS_DECL_NEW = """bool FileSystem_Init();
void FileSystem_Shutdown();
// Null-safe existence check. iOS has no filesystem_stdio dylib.
bool FileSystem_Exists(const char *filename);"""

FS_IMPL_OLD = """void FileSystem_Shutdown()
{
	if (g_pFileSystemModule)
	{
		Sys_UnloadModule(g_pFileSystemModule);
		g_pFileSystemModule = nullptr;
	}
}"""

FS_INIT_OLD = """bool FileSystem_Init()
{
	g_pFileSystemModule = Sys_LoadModule(STDIO_FILESYSTEM_LIB);
	if (!g_pFileSystemModule)
	{
		return false;
	}

	// Get FileSystem interface
	CreateInterfaceFn filesystemFactoryFn = Sys_GetFactory(g_pFileSystemModule);
	if (!filesystemFactoryFn)
	{
		Sys_Error("Unable to get filesystem factory.");
	}

	g_pFileSystem = (IFileSystem *)filesystemFactoryFn(FILESYSTEM_INTERFACE_VERSION, nullptr);
	if (!g_pFileSystem)
	{
		Sys_Error("Can not retrive filesystem interface version '" FILESYSTEM_INTERFACE_VERSION "'.");
	}

	return true;
}"""

FS_INIT_NEW = """bool FileSystem_Init()
{
	// ios-v5: do not dlopen filesystem_stdio. The working directory is the
	// Documents folder, so the copy inside the .app is missed and this
	// pointer stays null. If a copy does load, its GoldSrc search path was
	// never mounted and FileExists still faults at address 0. Callers ask
	// the engine, which already has the game files open.
	g_pFileSystem = nullptr;
	g_pFileSystemModule = nullptr;
	return false;
}"""

FS_IMPL_NEW = """void FileSystem_Shutdown()
{
	if (g_pFileSystemModule)
	{
		Sys_UnloadModule(g_pFileSystemModule);
		g_pFileSystemModule = nullptr;
	}
}

bool FileSystem_Exists(const char *filename)
{
	char fixed[260];
	size_t i;

	if (!filename || !filename[0])
		return false;

	// Never call g_pFileSystem. A non-null pointer here is still the
	// unmounted GoldSrc interface, and the virtual call is signal 11 at 0x0.
	for (i = 0; filename[i] && i + 1 < sizeof(fixed); ++i)
		fixed[i] = (filename[i] == '\\\\') ? '/' : filename[i];
	fixed[i] = '\\0';

	if (g_engfuncs.pfnGetFileSize)
		return g_engfuncs.pfnGetFileSize(fixed) >= 0;

	if (g_engfuncs.pfnLoadFileForMe && g_engfuncs.pfnFreeFile)
	{
		int length = 0;
		void *buf = g_engfuncs.pfnLoadFileForMe(fixed, &length);
		if (!buf)
			return false;
		g_engfuncs.pfnFreeFile(buf);
		return true;
	}

	return false;
}"""

GIVEFN_OLD = """	Q_memcpy(&g_engfuncs, pEnginefuncsTable, sizeof(enginefuncs_t));
	gpGlobals = pGlobals;

	FileSystem_Init();
}"""

GIVEFN_NEW = """	Q_memcpy(&g_engfuncs, pEnginefuncsTable, sizeof(enginefuncs_t));
	gpGlobals = pGlobals;

	FileSystem_Init();
	if (g_engfuncs.pfnServerPrint)
		g_engfuncs.pfnServerPrint("CS iOS v7: server library ready\\n");
}"""

RANDOMIZE_OLD = """void BotPhrase::Randomize()
{
	for (size_t i = 0; i < m_voiceBank.size(); i++)
	{
#ifdef __APPLE__
		std::random_device rd {};
		std::mt19937 mt {rd()};

		std::shuffle(m_voiceBank[i]->begin(), m_voiceBank[i]->end(), mt);
#else
		std::random_shuffle(m_voiceBank[i]->begin(), m_voiceBank[i]->end());
#endif
	}
}"""

RANDOMIZE_NEW = """void BotPhrase::Randomize()
{
	// ios-v5: std::random_device is the Apple-only shuffle used when a
	// listen server restarts the round, immediately after the map loads.
	// Shuffle with the engine RNG instead.
	for (size_t i = 0; i < m_voiceBank.size(); i++)
	{
		BotSpeakableVector *bank = m_voiceBank[i];
		size_t n;

		if (!bank)
			continue;
		n = bank->size();
		while (n > 1)
		{
			size_t j = (size_t)RANDOM_LONG(0, (int)n - 1);
			BotSpeakable *swap;

			n--;
			if (j > n)
				j = n;
			swap = (*bank)[n];
			(*bank)[n] = (*bank)[j];
			(*bank)[j] = swap;
		}
	}
}"""

WAVE_BOT_OLD = "speak->m_duration = (double)GET_APPROX_WAVE_PLAY_LEN(compositeFilename) / 1000.0f;"
WAVE_BOT_NEW = """speak->m_duration = 1.0f;
			if (g_engfuncs.pfnGetApproxWavePlayLen)
				speak->m_duration = (double)g_engfuncs.pfnGetApproxWavePlayLen(compositeFilename) / 1000.0f;"""

WAVE_HOSTAGE_OLD = "chatter->file[chatter->count].duration = (double)GET_APPROX_WAVE_PLAY_LEN(actualFilename) / 1000.0;"
WAVE_HOSTAGE_NEW = """chatter->file[chatter->count].duration = 1.0;
	if (g_engfuncs.pfnGetApproxWavePlayLen)
		chatter->file[chatter->count].duration = (double)g_engfuncs.pfnGetApproxWavePlayLen(actualFilename) / 1000.0;"""

CRASH_VER_OLD = """	int len = Q_snprintf( crash_message, sizeof( crash_message ), "Ver: " XASH_ENGINE_NAME " " XASH_VERSION " (build %i-%s-%s, %s-%s)\\n",
		Q_buildnum(), g_buildcommit, g_buildbranch, Q_buildos(), Q_buildarch() );"""

CRASH_VER_NEW = """	int len = Q_snprintf( crash_message, sizeof( crash_message ), "Ver: " XASH_ENGINE_NAME " " XASH_VERSION " (build %i-%s-%s, %s-%s) ios-v7\\n",
		Q_buildnum(), g_buildcommit, g_buildbranch, Q_buildos(), Q_buildarch() );"""

CRASH_BT_OLD = """	ssize_t unused = write( STDERR_FILENO, crash_message, len );"""

CRASH_BT_NEW = """#if XASH_APPLE
	{
		struct ios_bt frames = { 0 };
		_Unwind_Backtrace( IOS_CrashUnwind, &frames );
		for( int i = 0; i < frames.n && len < (int)sizeof( crash_message ) - 128; i++ )
		{
			Dl_info info;
			const char *sym = "?";
			const char *mod = "";
			const char *base;
			int wrote;

			memset( &info, 0, sizeof( info ));
			if( dladdr( frames.pc[i], &info ))
			{
				if( info.dli_sname )
					sym = info.dli_sname;
				if( info.dli_fname )
				{
					mod = info.dli_fname;
					base = strrchr( mod, '/' );
					if( base && base[1] )
						mod = base + 1;
				}
			}
			wrote = Q_snprintf( crash_message + len, sizeof( crash_message ) - len,
				"%2d: %p %s (%s)\\n", i, frames.pc[i], sym, mod );
			if( wrote < 0 || len + wrote >= (int)sizeof( crash_message ))
				break;
			len += wrote;
		}
	}
#endif
	ssize_t unused = write( STDERR_FILENO, crash_message, len );"""

CRASH_SETUP_OLD = """#if HAVE_LIBBACKTRACE
	have_libbacktrace = Sys_SetupLibbacktrace( argv0 );
#endif // HAVE_LIBBACKTRACE"""

CRASH_SETUP_NEW = """#if HAVE_LIBBACKTRACE && !XASH_APPLE
	have_libbacktrace = Sys_SetupLibbacktrace( argv0 );
#endif // HAVE_LIBBACKTRACE && !XASH_APPLE"""

CRASH_HELPER_OLD = """static qboolean have_libbacktrace = false;
static char crash_message[8192];"""

CRASH_HELPER_NEW = """static qboolean have_libbacktrace = false;
static char crash_message[8192];

#if XASH_APPLE
#include <unwind.h>
#include <dlfcn.h>
#include <string.h>
struct ios_bt { void *pc[24]; int n; };
static _Unwind_Reason_Code IOS_CrashUnwind( struct _Unwind_Context *ctx, void *arg )
{
	struct ios_bt *bt = arg;
	if( bt->n < 24 )
		bt->pc[bt->n++] = (void *)_Unwind_GetIP( ctx );
	return _URC_NO_REASON;
}
#endif"""

STB_NULL_OLD = """	buf = stbtt_GetCodepointBitmap( &m_fontInfo, scale, scale, ch, &bm_width, &bm_rows, &bm_left, &bm_top );

	// see where we should start rendering
	const int pushDown = m_iAscent + bm_top;"""

STB_NULL_NEW = """	buf = stbtt_GetCodepointBitmap( &m_fontInfo, scale, scale, ch, &bm_width, &bm_rows, &bm_left, &bm_top );
	// Missing glyphs and spaces return NULL. Reading buf[0] was the signal 11 at 0x0.
	if( !buf || bm_width <= 0 || bm_rows <= 0 )
	{
		if( buf )
			stbtt_FreeBitmap( buf, m_fontInfo.userdata );
		drawSize.w = m_iBlur * 2 + m_iOutlineSize * 2;
		if( drawSize.w < 1 )
			drawSize.w = 1;
		drawSize.h = drawSize.w;
		return;
	}

	// see where we should start rendering
	const int pushDown = m_iAscent + bm_top;"""

SOLID_OLD = "\telse if( !uiStatic.lowmemory )"
SOLID_NEW = """\t// Chinese labels use the plain face. Blur faces are not given CJK glyphs.
	else if( !uiStatic.lowmemory && !uiStatic.renderPicbuttonText )"""

# CHudMOTD::Draw reads m_szMOTD.Access(), which is NULL after Clear().
# MsgFunc used to Reset() an HTML motd and then still set HUD_DRAW.
MOTD_CVAR_OLD = """\tif( cl_hide_motd->value )
\t\treturn 1;"""

MOTD_CVAR_NEW = """\tif( cl_hide_motd && cl_hide_motd->value )
\t\treturn 1;"""

MOTD_HIDE_OLD = """\tif( cl_hide_motd->value )
\t{
\t\tReset();
\t\treturn 1;
\t}"""

MOTD_HIDE_NEW = """\t// Access() is NULL once the text is cleared. A missing cvar is the same
\t// class of read: the first match frame faults at address 0.
\tif( !cl_hide_motd || cl_hide_motd->value || !m_szMOTD.Access() )
\t{
\t\tReset();
\t\treturn 1;
\t}

\t// Filled rectangle plus glyph drawing. A null engine call is signal 11 at 0x0.
\tif( !gEngfuncs.pfnFillRGBA || !gEngfuncs.pfnFillRGBABlend || !gEngfuncs.pfnDrawCharacter )
\t{
\t\tReset();
\t\treturn 1;
\t}"""

MOTD_WHILE_OLD = "\twhile ( *ch )"
MOTD_WHILE_NEW = "\twhile ( ch && *ch )"

MOTD_NL_OLD = "\t\tif ( *ch == '\\n' )"
MOTD_NL_NEW = "\t\tif ( ch && *ch == '\\n' )"

MOTD_HTML_OLD = """\t// we still don't support html tags in motd :(
\tif( strcasestr( m_szMOTD.String(), "<!DOCTYPE HTML>" ) )
\t{
\t\tReset();
\t\tignoreThisMotd = true;
\t}

\tif ( is_finished )
\t{
\t\tint length = 0;
\t\t
\t\tm_iMaxLength = 0;
\t\tm_iFlags |= HUD_DRAW;


\t\tfor ( const char *sz = m_szMOTD.String(); *sz != 0; sz++ )  // count the number of lines in the MOTD
\t\t{
\t\t\tif ( *sz == '\\n' )
\t\t\t{
\t\t\t\tm_iLines++;
\t\t\t\tif( length > m_iMaxLength )
\t\t\t\t{
\t\t\t\t\tm_iMaxLength = length;
\t\t\t\t\tlength = 0;
\t\t\t\t}
\t\t\t}
\t\t\tlength++;
\t\t}
\t\t
\t\tm_iLines++;
\t\tif( length > m_iMaxLength )
\t\t{
\t\t\tm_iMaxLength = length;
\t\t\tlength = 0;
\t\t}
\t\tm_bShow = true;
\t}"""

MOTD_HTML_NEW = """\t// motd.txt shipped with CS is HTML. This panel can only draw plain text.
\t// Reset() frees the buffer (Access() becomes NULL). The old code then
\t// fell through and, on the last chunk, turned drawing back on. The next
\t// frame read that NULL pointer: signal 11 at 0x0 in CHudMOTD::Draw.
\t{
\t\tconst char *motd = m_szMOTD.String();
\t\tif( !motd[0]
\t\t\t|| strcasestr( motd, "<!doctype" )
\t\t\t|| strcasestr( motd, "<html" )
\t\t\t|| strcasestr( motd, "<head" )
\t\t\t|| strcasestr( motd, "<body" ) )
\t\t{
\t\t\tReset();
\t\t\tignoreThisMotd = true;
\t\t\treturn 1;
\t\t}
\t}

\tif ( is_finished && m_szMOTD.Access() )
\t{
\t\tint length = 0;

\t\tm_iMaxLength = 0;
\t\tm_iFlags |= HUD_DRAW;

\t\tfor ( const char *sz = m_szMOTD.String(); *sz != 0; sz++ )  // count the number of lines in the MOTD
\t\t{
\t\t\tif ( *sz == '\\n' )
\t\t\t{
\t\t\t\tm_iLines++;
\t\t\t\tif( length > m_iMaxLength )
\t\t\t\t{
\t\t\t\t\tm_iMaxLength = length;
\t\t\t\t\tlength = 0;
\t\t\t\t}
\t\t\t}
\t\t\tlength++;
\t\t}

\t\tm_iLines++;
\t\tif( length > m_iMaxLength )
\t\t{
\t\t\tm_iMaxLength = length;
\t\t\tlength = 0;
\t\t}
\t\tm_bShow = true;
\t}"""

FILL_OLD = """#define FillRGBA (*gEngfuncs.pfnFillRGBA)
#define FillRGBABlend (*gEngfuncs.pfnFillRGBABlend)"""

FILL_NEW = """// Null engine pointers are signal 11 at 0x0. MOTD, the crosshair, the
// round timer, and the ammo divider all fill rectangles on early frames.
static inline void FillRGBA( int x, int y, int w, int h, int r, int g, int b, int a )
{
\tif( gEngfuncs.pfnFillRGBA )
\t\tgEngfuncs.pfnFillRGBA( x, y, w, h, r, g, b, a );
}
static inline void FillRGBABlend( int x, int y, int w, int h, int r, int g, int b, int a )
{
\tif( gEngfuncs.pfnFillRGBABlend )
\t\tgEngfuncs.pfnFillRGBABlend( x, y, w, h, r, g, b, a );
}"""

DRAWCHAR_OLD = """\t\tint ret;
\t\tif( scale && g_iMobileAPIVersion )
\t\t\tret = gMobileAPI.pfnDrawScaledCharacter( x, y, number, r, g, b, scale ) / gHUD.m_flScale;
\t\telse
\t\t\tret = gEngfuncs.pfnDrawCharacter( x, y, number, r, g, b );
\t\treturn ret;"""

DRAWCHAR_NEW = """\t\tint ret = 0;
\t\tif( scale && g_iMobileAPIVersion )
\t\t{
\t\t\tif( gMobileAPI.pfnDrawScaledCharacter && gHUD.m_flScale != 0.0f )
\t\t\t\tret = gMobileAPI.pfnDrawScaledCharacter( x, y, number, r, g, b, scale ) / gHUD.m_flScale;
\t\t}
\t\telse if( gEngfuncs.pfnDrawCharacter )
\t\t\tret = gEngfuncs.pfnDrawCharacter( x, y, number, r, g, b );
\t\treturn ret;"""

HUDSTR_OLD = """\tchar *szIt = (char *)str;

\tCon_UtfProcessChar( 0 );

\t// draw the string until we hit the null character or a newline character
\tfor ( ; *szIt != 0 && *szIt != '\\n'; szIt++ )"""

HUDSTR_NEW = """\tchar *szIt = (char *)str;

\t// MOTD and center-print pass a missing string through here.
\tif( !szIt )
\t\treturn xpos;

\tCon_UtfProcessChar( 0 );

\t// draw the string until we hit the null character or a newline character
\tfor ( ; *szIt != 0 && *szIt != '\\n'; szIt++ )"""

HUDREV_OLD = """int DrawUtils::DrawHudStringReverse( int xpos, int ypos, int iMinX, const char *szString, int r, int g, int b, float scale )
{
\tint first_xpos = xpos;"""

HUDREV_NEW = """int DrawUtils::DrawHudStringReverse( int xpos, int ypos, int iMinX, const char *szString, int r, int g, int b, float scale )
{
\tif( !szString )
\t\treturn xpos;

\tint first_xpos = xpos;"""

HEALTH_OLD = "\t\tint idx = gEngfuncs.GetLocalPlayer()->index;"
HEALTH_NEW = """\t\t// The suit bit can be set before the local entity exists. index is
\t\t// the first field, so a NULL player is a read at address 0.
\t\tauto player = gEngfuncs.GetLocalPlayer ? gEngfuncs.GetLocalPlayer() : nullptr;
\t\tint idx = player ? player->index : 0;"""

RADAR_OLD = """\tif( bUseRenderAPI )
\t{
\t\tgEngfuncs.pTriAPI->RenderMode( kRenderTransAdd );"""

RADAR_NEW = """\tif( bUseRenderAPI && gEngfuncs.pTriAPI )
\t{
\t\tgEngfuncs.pTriAPI->RenderMode( kRenderTransAdd );"""

RADAR_TEX_OLD = """\tgRenderAPI.GL_Bind( 0, texHandle );

\t// gEngfuncs.pTriAPI->Begin( TRI_QUADS );

\tgEngfuncs.pTriAPI->Color4ub( r, g, b, a );"""

RADAR_TEX_NEW = """\tif( !gEngfuncs.pTriAPI || !gRenderAPI.GL_Bind )
\t\treturn;

\tgRenderAPI.GL_Bind( 0, texHandle );

\t// gEngfuncs.pTriAPI->Begin( TRI_QUADS );

\tgEngfuncs.pTriAPI->Color4ub( r, g, b, a );"""

QUAD_OLD = """\t// REMOVE WHEN NANOGL BUG WILL BE FIXED
\tgEngfuncs.pTriAPI->Begin( TRI_QUADS );
\t// REMOVE WHEN NANOGL BUG WILL BE FIXED"""

QUAD_NEW = """\tif( !gEngfuncs.pTriAPI || !gEngfuncs.pTriAPI->Begin )
\t\treturn;

\t// REMOVE WHEN NANOGL BUG WILL BE FIXED
\tgEngfuncs.pTriAPI->Begin( TRI_QUADS );
\t// REMOVE WHEN NANOGL BUG WILL BE FIXED"""

CHARSET_OLD = """\tif( !stricmp( con_charset->string, "cp1251" ))
\t{
\t\tg_codepage = 1251;
\t}
\telse if( !stricmp( con_charset->string, "cp1252" ))
\t{
\t\tg_codepage = 1252;
\t}
\telse
\t{
\t\tg_codepage = 0;
\t}

\tg_accept_utf8 = !stricmp( cl_charset->string, "utf-8" );"""

CHARSET_NEW = """\tconst char *con_name = (con_charset && con_charset->string) ? con_charset->string : "";
\tconst char *cl_name = (cl_charset && cl_charset->string) ? cl_charset->string : "";

\tif( !stricmp( con_name, "cp1251" ))
\t{
\t\tg_codepage = 1251;
\t}
\telse if( !stricmp( con_name, "cp1252" ))
\t{
\t\tg_codepage = 1252;
\t}
\telse
\t{
\t\tg_codepage = 0;
\t}

\tg_accept_utf8 = !stricmp( cl_name, "utf-8" );"""


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
    glyphs = Path(__file__).resolve().parents[1] / "fonts" / "menu_glyphs.inc"
    (mainui / "font" / "menu_glyphs.inc").write_text(glyphs.read_text(encoding="utf-8"), encoding="utf-8")
    replace_once(mainui / "font/FontManager.cpp", GLYPHS_OLD, GLYPHS_NEW, "bake menu CJK glyphs")
    replace_once(mainui / "font/StbFont.cpp", STB_NULL_OLD, STB_NULL_NEW, "null glyph bitmap")
    replace_once(mainui / "BaseMenu.cpp", PICBUTTON_TEXT_OLD, PICBUTTON_TEXT_NEW, "text menu buttons when a CJK font is present")
    replace_once(mainui / "controls/PicButton.cpp", STATUS_OLD, STATUS_NEW, "menu status text through the vector font")
    replace_once(mainui / "controls/PicButton.cpp", SOLID_OLD, SOLID_NEW, "solid CJK menu labels")

    motd = cs16 / "cl_dll/hud/MOTD.cpp"
    replace_once(motd, MOTD_CVAR_OLD, MOTD_CVAR_NEW, "motd hide cvar")
    replace_once(motd, MOTD_HIDE_OLD, MOTD_HIDE_NEW, "motd null text and missing draw calls")
    replace_once(motd, MOTD_WHILE_OLD, MOTD_WHILE_NEW, "motd walk stops on a null buffer")
    replace_once(motd, MOTD_NL_OLD, MOTD_NL_NEW, "motd newline restore")
    replace_once(motd, MOTD_HTML_OLD, MOTD_HTML_NEW, "motd html does not enable drawing")
    replace_once(cs16 / "cl_dll/cl_util.h", FILL_OLD, FILL_NEW, "null-safe rectangle fill")
    replace_once(cs16 / "cl_dll/include/draw_util.h", DRAWCHAR_OLD, DRAWCHAR_NEW, "null-safe glyph draw")
    replace_once(cs16 / "cl_dll/draw_util.cpp", HUDSTR_OLD, HUDSTR_NEW, "null hud string")
    replace_once(cs16 / "cl_dll/draw_util.cpp", HUDREV_OLD, HUDREV_NEW, "null reversed hud string")
    replace_once(cs16 / "cl_dll/draw_util.cpp", QUAD_OLD, QUAD_NEW, "null triangle api quad")
    replace_once(cs16 / "cl_dll/health.cpp", HEALTH_OLD, HEALTH_NEW, "null local player on the health bar")
    replace_once(cs16 / "cl_dll/hud/radar.cpp", RADAR_OLD, RADAR_NEW, "null triangle api on the radar")
    replace_once(cs16 / "cl_dll/hud/radar.cpp", RADAR_TEX_OLD, RADAR_TEX_NEW, "null radar texture draw")
    replace_once(cs16 / "cl_dll/hud_redraw.cpp", CHARSET_OLD, CHARSET_NEW, "null charset cvar on the first frame")

    regamedll = cs16 / "3rdparty/ReGameDLL_CS/regamedll"
    replace_once(regamedll / "public/FileSystem.h", FS_DECL_OLD, FS_DECL_NEW, "engine file exists declaration")
    replace_once(regamedll / "public/FileSystem.cpp", FS_INIT_OLD, FS_INIT_NEW, "do not load filesystem_stdio")
    replace_once(regamedll / "public/FileSystem.cpp", FS_IMPL_OLD, FS_IMPL_NEW, "engine file exists when filesystem_stdio is absent")
    replace_once(regamedll / "dlls/h_export.cpp", GIVEFN_OLD, GIVEFN_NEW, "ios-v7 server ready log")
    replace_once(regamedll / "dlls/hostage/hostage.cpp", "g_pFileSystem->FileExists(model)", "FileSystem_Exists(model)", "hostage model exists")
    replace_once(regamedll / "dlls/hostage/hostage.cpp", "g_pFileSystem->FileExists(actualFilename)", "FileSystem_Exists(actualFilename)", "hostage chatter exists")
    replace_once(regamedll / "dlls/hostage/hostage.cpp", WAVE_HOSTAGE_OLD, WAVE_HOSTAGE_NEW, "hostage wave length")
    replace_once(regamedll / "dlls/bot/cs_bot_chatter.cpp", "g_pFileSystem->FileExists(filePath)", "FileSystem_Exists(filePath)", "bot chatter exists")
    replace_once(regamedll / "dlls/bot/cs_bot_chatter.cpp", WAVE_BOT_OLD, WAVE_BOT_NEW, "bot wave length")
    replace_once(regamedll / "dlls/bot/cs_bot_chatter.cpp", RANDOMIZE_OLD, RANDOMIZE_NEW, "bot phrase shuffle")

    crash = xash / "engine/platform/posix/crash_posix.c"
    replace_once(crash, CRASH_HELPER_OLD, CRASH_HELPER_NEW, "ios crash frame buffer")
    replace_once(crash, CRASH_VER_OLD, CRASH_VER_NEW, "ios-v7 crash version")
    replace_once(crash, CRASH_BT_OLD, CRASH_BT_NEW, "ios crash frames")
    replace_once(crash, CRASH_SETUP_OLD, CRASH_SETUP_NEW, "skip dwarf-only backtrace on iOS")

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
