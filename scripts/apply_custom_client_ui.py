#!/usr/bin/env python3
"""Apply Cue personal-client UI policy to the pinned Telegram iOS checkout.

This overlay changes presentation and purchase-entry availability only. It does
not alter account.isPremium, Telegram API responses, server-side entitlement or
posting checks, or bypass any paid feature restriction.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

EXPECTED_SHA = "fb0e62ba8a147f0821da6aa63c09da7d79a10111"


def require_replace(text: str, old: str, new: str, expected: int, label: str) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{label}: expected {expected} match(es), found {count}")
    return text.replace(old, new)


def replace_region(text: str, start: str, end: str, rules: list[tuple[str, str, int]], label: str) -> str:
    a = text.find(start)
    b = text.find(end, a + len(start)) if a >= 0 else -1
    if a < 0 or b < 0:
        raise RuntimeError(f"{label}: region boundary not found")
    region = text[a:b]
    for old, new, count in rules:
        region = require_replace(region, old, new, count, f"{label}: {old.strip()}")
    return text[:a] + region + text[b:]


def write_if_changed(path: Path, text: str) -> None:
    path.write_text(text)


def apply_warm_theme(root: Path) -> None:
    path = root / "submodules/TelegramPresentationData/Sources/DefaultDayPresentationTheme.swift"
    text = path.read_text()
    marker = "// CUE_CF_ASSISTANT_WARM_THEME_V1"
    if marker in text:
        return
    text = require_replace(
        text,
        "public let defaultDayAccentColor = UIColor(rgb: 0x0088ff)",
        marker + "\npublic let defaultDayAccentColor = UIColor(rgb: 0xA64038)",
        1,
        "warm accent",
    )
    text = replace_region(
        text,
        "let rootNavigationBar = PresentationThemeRootNavigationBar(",
        "\n    let rootTabBar =",
        [
            ("primaryTextColor: UIColor(rgb: 0x000000)", "primaryTextColor: UIColor(rgb: 0x26221D)", 1),
            ("secondaryTextColor: UIColor(rgb: 0x787878)", "secondaryTextColor: UIColor(rgb: 0x756E64)", 1),
            ("controlColor: UIColor(rgb: 0x7e8791)", "controlColor: UIColor(rgb: 0x756E64)", 1),
            ("blurredBackgroundColor: UIColor(rgb: 0xf2f2f2, alpha: 0.9)", "blurredBackgroundColor: UIColor(rgb: 0xF5F2E9, alpha: 0.94)", 1),
            ("opaqueBackgroundColor: UIColor(rgb: 0xf7f7f7).mixedWith(.white, alpha: 0.14)", "opaqueBackgroundColor: UIColor(rgb: 0xF5F2E9)", 1),
            ("separatorColor: UIColor(rgb: 0xc8c7cc)", "separatorColor: UIColor(rgb: 0xE3DED1)", 1),
            ("badgeBackgroundColor: UIColor(rgb: 0xff3b30)", "badgeBackgroundColor: UIColor(rgb: 0xA64038)", 1),
            ("badgeStrokeColor: UIColor(rgb: 0xff3b30)", "badgeStrokeColor: UIColor(rgb: 0xA64038)", 1),
        ],
        "root navigation bar",
    )
    text = replace_region(
        text,
        "let rootTabBar = PresentationThemeRootTabBar(",
        "\n    let navigationSearchBar =",
        [
            ("separatorColor: UIColor(rgb: 0xb2b2b2)", "separatorColor: UIColor(rgb: 0xE3DED1)", 1),
            ("iconColor: UIColor(rgb: 0x959595)", "iconColor: UIColor(rgb: 0x756E64)", 1),
            ("textColor: UIColor(rgb: 0x000000, alpha: 0.8)", "textColor: UIColor(rgb: 0x26221D, alpha: 0.9)", 1),
            ("badgeBackgroundColor: UIColor(rgb: 0xff3b30)", "badgeBackgroundColor: UIColor(rgb: 0xA64038)", 1),
            ("badgeStrokeColor: UIColor(rgb: 0xff3b30)", "badgeStrokeColor: UIColor(rgb: 0xA64038)", 1),
        ],
        "root tab bar",
    )
    text = replace_region(
        text,
        "let navigationSearchBar = PresentationThemeNavigationSearchBar(",
        "\n    let rootController =",
        [
            ("backgroundColor: UIColor(rgb: 0xffffff)", "backgroundColor: UIColor(rgb: 0xF8F6EF)", 1),
            ("inputFillColor: UIColor(rgb: 0x000000, alpha: 0.06)", "inputFillColor: UIColor(rgb: 0xEDE9DE)", 1),
            ("inputTextColor: UIColor(rgb: 0x000000)", "inputTextColor: UIColor(rgb: 0x26221D)", 1),
            ("separatorColor: UIColor(rgb: 0xc8c7cc)", "separatorColor: UIColor(rgb: 0xE3DED1)", 1),
        ],
        "navigation search bar",
    )
    text = replace_region(
        text,
        "let list = PresentationThemeList(",
        "\n    let chatList =",
        [
            ("blocksBackgroundColor: UIColor(rgb: 0xefeff4)", "blocksBackgroundColor: UIColor(rgb: 0xF5F2E9)", 1),
            ("modalBlocksBackgroundColor: UIColor(rgb: 0xefeff4)", "modalBlocksBackgroundColor: UIColor(rgb: 0xF5F2E9)", 1),
            ("itemPrimaryTextColor: UIColor(rgb: 0x000000)", "itemPrimaryTextColor: UIColor(rgb: 0x26221D)", 1),
            ("itemSecondaryTextColor: UIColor(rgb: 0x8e8e93)", "itemSecondaryTextColor: UIColor(rgb: 0x756E64)", 1),
            ("itemBlocksBackgroundColor: UIColor(rgb: 0xffffff)", "itemBlocksBackgroundColor: UIColor(rgb: 0xFBF9F1)", 1),
            ("itemModalBlocksBackgroundColor: UIColor(rgb: 0xffffff)", "itemModalBlocksBackgroundColor: UIColor(rgb: 0xFBF9F1)", 1),
            ("itemHighlightedBackgroundColor: UIColor(rgb: 0xe5e5ea)", "itemHighlightedBackgroundColor: UIColor(rgb: 0xEFE9DE)", 1),
            ("itemBlocksSeparatorColor: UIColor(rgb: 0xc8c7cc)", "itemBlocksSeparatorColor: UIColor(rgb: 0xE3DED1)", 1),
            ("itemPlainSeparatorColor: UIColor(rgb: 0xc8c7cc)", "itemPlainSeparatorColor: UIColor(rgb: 0xE3DED1)", 1),
            ("sectionHeaderTextColor: UIColor(rgb: 0x6d6d72)", "sectionHeaderTextColor: UIColor(rgb: 0x756E64)", 1),
        ],
        "settings list palette",
    )
    text = replace_region(
        text,
        "let chatList = PresentationThemeChatList(",
        "\n    let bubbleStrokeColor:",
        [
            ("pinnedItemBackgroundColor: UIColor(rgb: 0xf7f7f7)", "pinnedItemBackgroundColor: UIColor(rgb: 0xF5F2E9)", 1),
            ("itemHighlightedBackgroundColor: UIColor(rgb: 0xe5e5ea)", "itemHighlightedBackgroundColor: UIColor(rgb: 0xEFE9DE)", 1),
            ("pinnedItemHighlightedBackgroundColor: UIColor(rgb: 0xe5e5ea)", "pinnedItemHighlightedBackgroundColor: UIColor(rgb: 0xEFE9DE)", 1),
            ("itemSelectedBackgroundColor: UIColor(rgb: 0xe9f0fa)", "itemSelectedBackgroundColor: UIColor(rgb: 0xF3E6E1)", 1),
            ("titleColor: UIColor(rgb: 0x000000)", "titleColor: UIColor(rgb: 0x26221D)", 1),
            ("messageDraftTextColor: UIColor(rgb: 0xdd4b39)", "messageDraftTextColor: UIColor(rgb: 0xA64038)", 1),
        ],
        "chat list palette",
    )

    message_start = text.find("let message = PresentationThemeChatMessage(")
    message_end = text.find("\n    let serviceMessage", message_start + 1)
    if message_start < 0 or message_end < 0:
        raise RuntimeError("chat bubble palette: message region boundary not found")
    message = text[message_start:message_end]
    outgoing_start = message.find("outgoing: PresentationThemePartedColors(")
    if outgoing_start < 0:
        raise RuntimeError("chat bubble palette: outgoing region not found")
    outgoing_end = message.find("\n        freeform: PresentationThemeBubbleColor(", outgoing_start)
    if outgoing_end < 0:
        raise RuntimeError("chat bubble palette: outgoing region end not found")
    incoming, outgoing = message[:outgoing_start], message[outgoing_start:outgoing_end]
    message_tail = message[outgoing_end:]
    for old, new, count in [
        ("fill: [UIColor(rgb: 0xffffff)]", "fill: [UIColor(rgb: 0xFDFBF5)]", 2),
        ("highlightedFill: UIColor(rgb: 0xd9f4ff)", "highlightedFill: UIColor(rgb: 0xEFE9DE)", 2),
        ("primaryTextColor: UIColor(rgb: 0x000000)", "primaryTextColor: UIColor(rgb: 0x26221D)", 1),
        ("secondaryTextColor: UIColor(rgb: 0x77828C, alpha: 1.0)", "secondaryTextColor: UIColor(rgb: 0x756E64, alpha: 1.0)", 1),
        ("linkTextColor: UIColor(rgb: 0x004bad)", "linkTextColor: UIColor(rgb: 0xA64038)", 1),
        ("fileTitleColor: UIColor(rgb: 0x0b8bed)", "fileTitleColor: UIColor(rgb: 0xA64038)", 1),
    ]:
        incoming = require_replace(incoming, old, new, count, f"incoming bubble: {old}")
    for old, new, count in [
        ("fill: [UIColor(rgb: 0xe1ffc7)]", "fill: [UIColor(rgb: 0xF3E6DA)]", 2),
        ("highlightedFill: UIColor(rgb: 0xbaff93)", "highlightedFill: UIColor(rgb: 0xEBD6C8)", 2),
        ("secondaryTextColor: UIColor(rgb: 0x008c09, alpha: 0.8)", "secondaryTextColor: UIColor(rgb: 0x75433B, alpha: 0.9)", 1),
        ("linkTextColor: UIColor(rgb: 0x004bad)", "linkTextColor: UIColor(rgb: 0xA64038)", 1),
        ("accentTextColor: UIColor(rgb: 0x00a700)", "accentTextColor: UIColor(rgb: 0xA64038)", 1),
        ("accentControlColor: UIColor(rgb: 0x3fc33b)", "accentControlColor: UIColor(rgb: 0xA64038)", 1),
        ("mediaActiveControlColor: UIColor(rgb: 0x3fc33b)", "mediaActiveControlColor: UIColor(rgb: 0xA64038)", 1),
        ("pendingActivityColor: UIColor(rgb: 0x42b649)", "pendingActivityColor: UIColor(rgb: 0xA64038)", 1),
        ("fileTitleColor: UIColor(rgb: 0x3faa3c)", "fileTitleColor: UIColor(rgb: 0xA64038)", 1),
    ]:
        outgoing = require_replace(outgoing, old, new, count, f"outgoing bubble: {old}")
    message = incoming + outgoing + message_tail
    text = text[:message_start] + message + text[message_end:]
    text = require_replace(
        text,
        "defaultWallpaper: day ? .color(0xffffff) : defaultPatternWallpaper,",
        "defaultWallpaper: day ? .builtin(WallpaperSettings()) : defaultPatternWallpaper,",
        1,
        "default global ink-wash wallpaper",
    )
    write_if_changed(path, text)

    dark_theme_path = root / "submodules/TelegramPresentationData/Sources/DefaultDarkPresentationTheme.swift"
    dark_theme_text = dark_theme_path.read_text()
    if "CUE_DARK_GLOBAL_INKWASH_WALLPAPER_V1" not in dark_theme_text:
        dark_theme_text = require_replace(
            dark_theme_text,
            "let defaultPatternWallpaper: TelegramWallpaper = defaultBuiltinWallpaper(data: .default, colors: defaultDarkWallpaperGradientColors.map(\\.rgb), intensity: -34)",
            "// CUE_DARK_GLOBAL_INKWASH_WALLPAPER_V1\n    let defaultPatternWallpaper: TelegramWallpaper = .builtin(WallpaperSettings())",
            1,
            "default dark global ink-wash wallpaper",
        )
        write_if_changed(dark_theme_path, dark_theme_text)

    background_path = root / "submodules/TelegramPresentationData/Sources/ChatControllerBackgroundNode.swift"
    background_text = background_path.read_text()
    if "CUE_GLOBAL_INKWASH_WALLPAPER_V1" not in background_text:
        background_text = require_replace(
            background_text,
            'if let filePath = getAppBundle().path(forResource: "ChatWallpaperBuiltin0", ofType: "jpg") {',
            'if let filePath = getAppBundle().path(forResource: "ChatWallpaperBuiltin0", ofType: "png") ?? getAppBundle().path(forResource: "ChatWallpaperBuiltin0", ofType: "jpg") {',
            2,
            "global bundled ink-wash resource",
        )
        background_text = require_replace(
            background_text,
            "public func chatControllerBackgroundImage(",
            "// CUE_GLOBAL_INKWASH_WALLPAPER_V1: bundled PNG takes precedence for the shared light-theme wallpaper.\npublic func chatControllerBackgroundImage(",
            1,
            "global wallpaper marker",
        )
        write_if_changed(background_path, background_text)

    wallpaper_node_path = root / "submodules/WallpaperBackgroundNode/Sources/WallpaperBackgroundNode.swift"
    wallpaper_node_text = wallpaper_node_path.read_text()
    if "CUE_DARK_WALLPAPER_OVERLAY_V1" not in wallpaper_node_text:
        wallpaper_node_text = require_replace(
            wallpaper_node_text,
            "                if !file.isPattern {\n                    intensity = file.settings.intensity\n                }\n            default:",
            "                if !file.isPattern {\n                    intensity = file.settings.intensity\n                }\n            case .builtin(_):\n                // CUE_DARK_WALLPAPER_OVERLAY_V1\n                dimAlpha = 0.46\n            default:",
            1,
            "dark ink-wash contrast overlay",
        )
        write_if_changed(wallpaper_node_path, wallpaper_node_text)


def apply_monetization_policy(root: Path) -> None:
    premium_path = root / "submodules/AccountContext/Sources/Premium.swift"
    text = premium_path.read_text()
    if "// CUE_LOCAL_MONETIZATION_POLICY_V1" not in text:
        text = require_replace(
            text,
            "public struct PremiumConfiguration {",
            "public struct PremiumConfiguration {\n    // CUE_LOCAL_MONETIZATION_POLICY_V1: hides purchase UI only; server entitlements remain authoritative.",
            1,
            "Premium configuration marker",
        )
        text = require_replace(text, "isPremiumDisabled: false,", "isPremiumDisabled: true,", 1, "Premium default UI gate")
        start = text.find("public static func with(appConfiguration: AppConfiguration) -> PremiumConfiguration {")
        end = text.find("\n    }\n}", start)
        if start < 0 or end < 0:
            raise RuntimeError("PremiumConfiguration.with boundary not found")
        region = text[start:end]
        rules = [
            ('isPremiumDisabled: data["premium_purchase_blocked"] as? Bool ?? defaultValue.isPremiumDisabled,', 'isPremiumDisabled: true,'),
            ('areStarsDisabled: data["stars_purchase_blocked"] as? Bool ?? defaultValue.areStarsDisabled,', 'areStarsDisabled: true,'),
            ('subscriptionManagementUrl: data["premium_manage_subscription_url"] as? String ?? "",', 'subscriptionManagementUrl: "",'),
            ('showPremiumGiftInAttachMenu: data["premium_gift_attach_menu_icon"] as? Bool ?? defaultValue.showPremiumGiftInAttachMenu,', 'showPremiumGiftInAttachMenu: false,'),
            ('showPremiumGiftInTextField: data["premium_gift_text_field_icon"] as? Bool ?? defaultValue.showPremiumGiftInTextField,', 'showPremiumGiftInTextField: false,'),
            ('giveawayGiftsPurchaseAvailable: data["giveaway_gifts_purchase_available"] as? Bool ?? defaultValue.giveawayGiftsPurchaseAvailable,', 'giveawayGiftsPurchaseAvailable: false,'),
            ('starsGiftsPurchaseAvailable: data["stars_gifts_enabled"] as? Bool ?? defaultValue.starsGiftsPurchaseAvailable,', 'starsGiftsPurchaseAvailable: false,'),
            ('starGiftsPurchaseBlocked: data["stargifts_blocked"] as? Bool ?? defaultValue.starGiftsPurchaseBlocked,', 'starGiftsPurchaseBlocked: true,'),
        ]
        for old, new in rules:
            region = require_replace(region, old, new, 1, "Premium local UI policy")
        text = text[:start] + region + text[end:]
        write_if_changed(premium_path, text)

    wallet_path = root / "submodules/WalletContext/Sources/WalletContext.swift"
    text = wallet_path.read_text()
    if "// CUE_LOCAL_WALLET_UI_DISABLED_V1" not in text:
        text = require_replace(
            text,
            '        let isAvailable = appConfiguration.data?["wallet_available"] as? Bool ?? self.defaultValue.isAvailable',
            '        // CUE_LOCAL_WALLET_UI_DISABLED_V1: this client hides wallet UI; no wallet or account state is modified.\n        let isAvailable = false',
            1,
            "Wallet UI policy",
        )
        write_if_changed(wallet_path, text)

    items_path = root / "submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoSettingsItems.swift"
    text = items_path.read_text()
    if "// CUE_REMOVE_MONETIZATION_ENTRIES_V1" not in text:
        start = text.find("func settingsItems(")
        end = text.find("\nfunc settingsEditingItems(", start)
        if start < 0 or end < 0:
            raise RuntimeError("settingsItems function boundary not found")
        region = text[start:end]
        region = require_replace(
            region,
            "if settings.premiumGracePeriod {",
            "if settings.premiumGracePeriod && !PremiumConfiguration.with(appConfiguration: context.currentAppConfiguration.with { $0 }).isPremiumDisabled {",
            1,
            "subscription renewal prompt",
        )
        region = require_replace(
            region,
            "    var result: [(AnyHashable, [PeerInfoScreenItem])] = []",
            "    // CUE_REMOVE_MONETIZATION_ENTRIES_V1: hide Stars, Premium, Business, gifts and wallet rows.\n    items[.wallet] = []\n    items[.payment] = []\n\n    var result: [(AnyHashable, [PeerInfoScreenItem])] = []",
            1,
            "settings payment sections",
        )
        text = text[:start] + region + text[end:]
        write_if_changed(items_path, text)

    search_path = root / "submodules/SettingsUI/Sources/Search/SettingsSearchableItems.swift"
    text = search_path.read_text()
    if "// CUE_HIDE_PAID_SETTINGS_SEARCH_V1" not in text:
        start = text.find("private func premiumSearchableItems(context: AccountContext) -> [SettingsSearchableItem] {")
        end = text.find("\nprivate func myProfileSearchableItems(context: AccountContext)", start)
        if start < 0 or end < 0:
            raise RuntimeError("premiumSearchableItems function boundary not found")
        text = text[:start] + "private func premiumSearchableItems(context: AccountContext) -> [SettingsSearchableItem] {\n    // CUE_HIDE_PAID_SETTINGS_SEARCH_V1\n    return []\n}\n" + text[end:]
        write_if_changed(search_path, text)

    intro_path = root / "submodules/PremiumUI/Sources/PremiumIntroScreen.swift"
    text = intro_path.read_text()
    if "// CUE_DISABLE_STOREKIT_PURCHASES_V1" not in text:
        text = require_replace(
            text,
            "        var inAppPurchaseManager: InAppPurchaseManager? {\n            switch self {\n            case let .accountContext(context):\n                return context.inAppPurchaseManager\n            case let .sharedContext(_, _, inAppPurchaseManager):\n                return inAppPurchaseManager\n            }\n        }",
            "        // CUE_DISABLE_STOREKIT_PURCHASES_V1: no StoreKit manager is supplied to premium paywall UI.\n        var inAppPurchaseManager: InAppPurchaseManager? {\n            return nil\n        }",
            1,
            "Premium StoreKit purchase context",
        )
        write_if_changed(intro_path, text)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", required=True, type=Path)
    args = parser.parse_args()
    root = args.upstream.resolve()
    actual_sha = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if actual_sha != EXPECTED_SHA:
        raise SystemExit(f"Expected Telegram upstream {EXPECTED_SHA}, found {actual_sha}")
    apply_warm_theme(root)
    apply_monetization_policy(root)
    print("Applied warm CF-inspired theme and local monetization-UI suppression; server entitlement code was not modified.")


if __name__ == "__main__":
    main()
