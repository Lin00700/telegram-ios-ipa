#!/usr/bin/env python3
"""Apply a coherent ink-wash palette across Telegram's shared UI themes.

The patch deliberately changes shared PresentationTheme components rather than
only the app icon or chat wallpaper. It does not alter Telegram behavior or
server-side entitlement checks.
"""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

EXPECTED_SHA = "fb0e62ba8a147f0821da6aa63c09da7d79a10111"
DAY_MARKER = "CUE_CF_INKWASH_THEME_V2"
DARK_MARKER = "CUE_CF_DARK_INKWASH_THEME_V2"


def replace_exact(text: str, old: str, new: str, label: str) -> str:
    if old in text:
        return text.replace(old, new)
    if new in text:
        return text
    raise RuntimeError(f"{label}: expected source fragment is absent")


def patch_region(text: str, start: str, end: str, rules: list[tuple[str, str]], label: str) -> str:
    a = text.find(start)
    b = text.find(end, a + len(start)) if a >= 0 else -1
    if a < 0 or b < 0:
        raise RuntimeError(f"{label}: region boundary not found")
    region = text[a:b]
    for old, new in rules:
        region = replace_exact(region, old, new, f"{label}: {old.strip()}")
    return text[:a] + region + text[b:]


def patch_day_theme(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if DAY_MARKER in text:
        return

    text = replace_exact(
        text,
        "    let intro = PresentationThemeIntro(",
        f"    // {DAY_MARKER}: global paper, ink, cinnabar and muted-jade palette.\n    let intro = PresentationThemeIntro(",
        "day theme version marker",
    )
    blocks = [
        ("    let intro = PresentationThemeIntro(", "\n    let passcode =", [
            ("primaryTextColor: UIColor(rgb: 0x000000)", "primaryTextColor: UIColor(rgb: 0x26221D)"),
            ("disabledTextColor: UIColor(rgb: 0xd0d0d0)", "disabledTextColor: UIColor(rgb: 0xB8B0A3)"),
            ("startButtonColor: UIColor(rgb: 0x2ca5e0)", "startButtonColor: UIColor(rgb: 0xA64038)"),
            ("dotColor: UIColor(rgb: 0xd9d9d9)", "dotColor: UIColor(rgb: 0xD8D0C2)"),
        ]),
        ("    let passcode = PresentationThemePasscode(", "\n    let rootNavigationBar =", [
            ("topColor: UIColor(rgb: 0x46739e)", "topColor: UIColor(rgb: 0x7D8A7B)"),
            ("bottomColor: UIColor(rgb: 0x2a5982)", "bottomColor: UIColor(rgb: 0x394541)"),
        ]),
        ("    let rootNavigationBar = PresentationThemeRootNavigationBar(", "\n    let rootTabBar =", [
            ("disabledButtonColor: UIColor(rgb: 0xd0d0d0)", "disabledButtonColor: UIColor(rgb: 0xB8B0A3)"),
            ("segmentedBackgroundColor: UIColor(rgb: 0x000000, alpha: 0.06)", "segmentedBackgroundColor: UIColor(rgb: 0xEDE8DC)"),
            ("segmentedTextColor: UIColor(rgb: 0x000000)", "segmentedTextColor: UIColor(rgb: 0x26221D)"),
            ("segmentedDividerColor: UIColor(rgb: 0xd6d6dc)", "segmentedDividerColor: UIColor(rgb: 0xE3DED1)"),
            ("clearButtonBackgroundColor: UIColor(rgb: 0xE3E3E3, alpha: 0.78)", "clearButtonBackgroundColor: UIColor(rgb: 0xE3DED1, alpha: 0.78)"),
            ("clearButtonForegroundColor: UIColor(rgb: 0x7f7f7f)", "clearButtonForegroundColor: UIColor(rgb: 0x756E64)"),
        ]),
        ("    let navigationSearchBar = PresentationThemeNavigationSearchBar(", "\n    let rootController =", [
            ("inputPlaceholderTextColor: UIColor(rgb: 0x8e8e93)", "inputPlaceholderTextColor: UIColor(rgb: 0x938B7F)"),
            ("inputIconColor: UIColor(rgb: 0x8e8e93)", "inputIconColor: UIColor(rgb: 0x756E64)"),
            ("inputClearButtonColor: UIColor(rgb: 0x7b7b81)", "inputClearButtonColor: UIColor(rgb: 0x756E64)"),
        ]),
        ("    let switchColors = PresentationThemeSwitch(", "\n    let list =", [
            ("frameColor: UIColor(rgb: 0xe9e9ea)", "frameColor: UIColor(rgb: 0xE3DED1)"),
            ("handleColor: UIColor(rgb: 0xffffff)", "handleColor: UIColor(rgb: 0xFBF9F1)"),
            ("contentColor: UIColor(rgb: 0x35c759)", "contentColor: UIColor(rgb: 0x7A8B7B)"),
            ("positiveColor: UIColor(rgb: 0x00c900)", "positiveColor: UIColor(rgb: 0x6F8575)"),
            ("negativeColor: UIColor(rgb: 0xff3b30)", "negativeColor: UIColor(rgb: 0xA64038)"),
        ]),
        ("    let list = PresentationThemeList(", "\n    let chatList =", [
            ("plainBackgroundColor: UIColor(rgb: 0xffffff)", "plainBackgroundColor: UIColor(rgb: 0xF8F6EF)"),
            ("modalPlainBackgroundColor: UIColor(rgb: 0xffffff)", "modalPlainBackgroundColor: UIColor(rgb: 0xF8F6EF)"),
            ("itemDisabledTextColor: UIColor(rgb: 0x8e8e93)", "itemDisabledTextColor: UIColor(rgb: 0x938B7F)"),
            ("itemHighlightedColor: UIColor(rgb: 0x00b12c)", "itemHighlightedColor: UIColor(rgb: 0xA64038)"),
            ("itemDestructiveColor: UIColor(rgb: 0xff3b30)", "itemDestructiveColor: UIColor(rgb: 0x9F3C34)"),
            ("itemPlaceholderTextColor: UIColor(rgb: 0xc8c8ce)", "itemPlaceholderTextColor: UIColor(rgb: 0xB8B0A3)"),
            ("disclosureArrowColor: UIColor(rgb: 0xbab9be)", "disclosureArrowColor: UIColor(rgb: 0x9A9286)"),
            ("freeTextColor: UIColor(rgb: 0x6d6d72)", "freeTextColor: UIColor(rgb: 0x756E64)"),
            ("freeTextErrorColor: UIColor(rgb: 0xcf3030)", "freeTextErrorColor: UIColor(rgb: 0xB34439)"),
            ("freeTextSuccessColor: UIColor(rgb: 0x26972c)", "freeTextSuccessColor: UIColor(rgb: 0x6F8575)"),
            ("freeMonoIconColor: UIColor(rgb: 0x7e7e87)", "freeMonoIconColor: UIColor(rgb: 0x756E64)"),
            ("fillColor: UIColor(rgb: 0x4892f2)", "fillColor: UIColor(rgb: 0x738578)"),
            ("fillColor: UIColor(rgb: 0xf09a37)", "fillColor: UIColor(rgb: 0xB18B58)"),
            ("fillColor: UIColor(rgb: 0xff3824)", "fillColor: UIColor(rgb: 0x9F3C34)"),
            ("fillColor: UIColor(rgb: 0x00c900)", "fillColor: UIColor(rgb: 0x6F8575)"),
            ("fillColor: UIColor(rgb: 0xff9500)", "fillColor: UIColor(rgb: 0xB18B58)"),
            ("fillColor: UIColor(rgb: 0xbcbcc3)", "fillColor: UIColor(rgb: 0xB8B0A3)"),
            ("strokeColor: UIColor(rgb: 0xc7c7cc)", "strokeColor: UIColor(rgb: 0xB8B0A3)"),
            ("controlSecondaryColor: UIColor(rgb: 0xdedede)", "controlSecondaryColor: UIColor(rgb: 0xD8D0C2)"),
            ("backgroundColor: UIColor(rgb: 0xd6d6dc)", "backgroundColor: UIColor(rgb: 0xEDE8DC)"),
            ("strokeColor: UIColor(rgb: 0xd6d6dc)", "strokeColor: UIColor(rgb: 0xE3DED1)"),
            ("placeholderColor: UIColor(rgb: 0x96979d)", "placeholderColor: UIColor(rgb: 0x938B7F)"),
            ("primaryColor: UIColor(rgb: 0x000000)", "primaryColor: UIColor(rgb: 0x26221D)"),
            ("controlColor: UIColor(rgb: 0x96979d)", "controlColor: UIColor(rgb: 0x756E64)"),
            ("backgroundColor: UIColor(rgb: 0xe9e9e9)", "backgroundColor: UIColor(rgb: 0xF4F0E5)"),
            ("strokeColor: UIColor(rgb: 0xe9e9e9)", "strokeColor: UIColor(rgb: 0xE3DED1)"),
            ("placeholderColor: UIColor(rgb: 0x8e8d92)", "placeholderColor: UIColor(rgb: 0x938B7F)"),
            ("controlColor: UIColor(rgb: 0xbcbcc0)", "controlColor: UIColor(rgb: 0x9A9286)"),
            ("mediaPlaceholderColor: UIColor(rgb: 0xEFEFF4)", "mediaPlaceholderColor: UIColor(rgb: 0xF0ECE2)"),
            ("pageIndicatorInactiveColor: UIColor(rgb: 0xe3e3e7)", "pageIndicatorInactiveColor: UIColor(rgb: 0xD8D0C2)"),
            ("PresentationThemeItemBarChart(color1: defaultDayAccentColor, color2: UIColor(rgb: 0xc8c7cc), color3: UIColor(rgb: 0xf2f1f7))", "PresentationThemeItemBarChart(color1: defaultDayAccentColor, color2: UIColor(rgb: 0xB8B0A3), color3: UIColor(rgb: 0xF0ECE2))"),
            ("backgroundColor: UIColor(rgb: 0xf2f2f7)", "backgroundColor: UIColor(rgb: 0xF0ECE2)"),
            ("strokeColor: UIColor(rgb: 0xf2f2f7)", "strokeColor: UIColor(rgb: 0xE3DED1)"),
            ("placeholderColor: UIColor(rgb: 0xb6b6bb)", "placeholderColor: UIColor(rgb: 0x938B7F)"),
            ("controlColor: UIColor(rgb: 0xb6b6bb)", "controlColor: UIColor(rgb: 0x9A9286)"),
        ]),
        ("    let chatList = PresentationThemeChatList(", "\n    let bubbleStrokeColor", [
            ("backgroundColor: UIColor(rgb: 0xffffff)", "backgroundColor: UIColor(rgb: 0xF0ECE2)"),
            ("itemSeparatorColor: UIColor(rgb: 0xc8c7cc)", "itemSeparatorColor: UIColor(rgb: 0xE3DED1)"),
            ("itemBackgroundColor: UIColor(rgb: 0xffffff)", "itemBackgroundColor: UIColor(rgb: 0xFBF9F1)"),
            ("secretTitleColor: UIColor(rgb: 0x00b12c)", "secretTitleColor: UIColor(rgb: 0x6F8575)"),
            ("dateTextColor: UIColor(rgb: 0x8e8e93)", "dateTextColor: UIColor(rgb: 0x756E64)"),
            ("authorNameColor: UIColor(rgb: 0x000000)", "authorNameColor: UIColor(rgb: 0x26221D)"),
            ("messageTextColor: UIColor(rgb: 0x8e8e93)", "messageTextColor: UIColor(rgb: 0x756E64)"),
            ("messageHighlightedTextColor: UIColor(rgb: 0x000000)", "messageHighlightedTextColor: UIColor(rgb: 0x26221D)"),
            ("checkmarkColor: day ? defaultDayAccentColor : UIColor(rgb: 0x21c004)", "checkmarkColor: day ? defaultDayAccentColor : UIColor(rgb: 0x6F8575)"),
            ("pendingIndicatorColor: UIColor(rgb: 0x8e8e93)", "pendingIndicatorColor: UIColor(rgb: 0x938B7F)"),
            ("failedFillColor: UIColor(rgb: 0xff3b30)", "failedFillColor: UIColor(rgb: 0x9F3C34)"),
            ("muteIconColor: UIColor(rgb: 0xa7a7ad)", "muteIconColor: UIColor(rgb: 0xA79F92)"),
            ("unreadBadgeInactiveBackgroundColor: UIColor(rgb: 0xb6b6bb)", "unreadBadgeInactiveBackgroundColor: UIColor(rgb: 0xAAA293)"),
            ("reactionBadgeActiveBackgroundColor: UIColor(rgb: 0xFF2D55)", "reactionBadgeActiveBackgroundColor: UIColor(rgb: 0xA64038)"),
            ("pinnedBadgeColor: UIColor(rgb: 0xb6b6bb)", "pinnedBadgeColor: UIColor(rgb: 0x9A9286)"),
            ("pinnedSearchBarColor: UIColor(rgb: 0xe5e5e5)", "pinnedSearchBarColor: UIColor(rgb: 0xEDE8DC)"),
            ("regularSearchBarColor: UIColor(rgb: 0xe9e9e9)", "regularSearchBarColor: UIColor(rgb: 0xF4F0E5)"),
            ("sectionHeaderFillColor: .white", "sectionHeaderFillColor: UIColor(rgb: 0xF5F2E9)"),
            ("secretIconColor: UIColor(rgb: 0x00b12c)", "secretIconColor: UIColor(rgb: 0x6F8575)"),
            ("topColor: UIColor(rgb: 0x72d5fd)", "topColor: UIColor(rgb: 0x839284)"),
            ("bottomColor: UIColor(rgb: 0x2a9ef1)", "bottomColor: UIColor(rgb: 0x60776E)"),
            ("topColor: UIColor(rgb: 0xdedee5)", "topColor: UIColor(rgb: 0xD8D0C2)"),
            ("bottomColor: UIColor(rgb: 0xc5c6cc)", "bottomColor: UIColor(rgb: 0xB8B0A3)"),
            ("onlineDotColor: UIColor(rgb: 0x4cc91f)", "onlineDotColor: UIColor(rgb: 0x6F8575)"),
            ("topColor: UIColor(rgb: 0x34C76F)", "topColor: UIColor(rgb: 0x829183)"),
            ("bottomColor: UIColor(rgb: 0x3DA1FD)", "bottomColor: UIColor(rgb: 0xA64038)"),
            ("topColor: UIColor(rgb: 0x7CD636)", "topColor: UIColor(rgb: 0xA58B5E)"),
            ("bottomColor: UIColor(rgb: 0x26B470)", "bottomColor: UIColor(rgb: 0x6F8575)"),
        ]),
        ("    let serviceMessageDay = PresentationThemeServiceMessage(", "\n    let inputPanelMediaRecordingControl =", [
            ("fill: UIColor(rgb: 0xffffff, alpha: 0.8)", "fill: UIColor(rgb: 0xF0ECE2, alpha: 0.88)"),
            ("primaryText: UIColor(rgb: 0x8d8e93)", "primaryText: UIColor(rgb: 0x756E64)"),
            ("linkHighlight: UIColor(rgb: 0x748391, alpha: 0.25)", "linkHighlight: UIColor(rgb: 0xA64038, alpha: 0.18)"),
            ("dateFillStatic: UIColor(rgb: 0xffffff, alpha: 0.8)", "dateFillStatic: UIColor(rgb: 0xF0ECE2, alpha: 0.88)"),
            ("dateFillFloating: UIColor(rgb: 0xffffff, alpha: 0.8)", "dateFillFloating: UIColor(rgb: 0xF0ECE2, alpha: 0.88)"),
            ("unreadBarFillColor: UIColor(rgb: 0xffffff)", "unreadBarFillColor: UIColor(rgb: 0xF5F2E9)"),
            ("unreadBarStrokeColor: UIColor(rgb: 0xffffff)", "unreadBarStrokeColor: UIColor(rgb: 0xD8D0C2)"),
            ("unreadBarTextColor: UIColor(rgb: 0x8d8e93)", "unreadBarTextColor: UIColor(rgb: 0x756E64)"),
        ]),
        ("    let inputPanel = PresentationThemeChatInputPanel(", "\n    let inputMediaPanel =", [
            ("panelBackgroundColorNoWallpaper: UIColor(rgb: 0xffffff)", "panelBackgroundColorNoWallpaper: UIColor(rgb: 0xF5F2E9)"),
            ("panelSeparatorColor: UIColor(rgb: 0xbec2c6)", "panelSeparatorColor: UIColor(rgb: 0xE3DED1)"),
            ("panelControlColor: UIColor(rgb: 0x000000, alpha: 1.0)", "panelControlColor: UIColor(rgb: 0x26221D, alpha: 1.0)"),
            ("inputBackgroundColor: UIColor(white: 1.0, alpha: 0.8)", "inputBackgroundColor: UIColor(rgb: 0xFBF9F1, alpha: 0.94)"),
            ("inputStrokeColor: UIColor(rgb: 0x000000, alpha: 0.1)", "inputStrokeColor: UIColor(rgb: 0xB8B0A3, alpha: 0.4)"),
            ("inputPlaceholderColor: UIColor(rgb: 0x000000, alpha: 0.4)", "inputPlaceholderColor: UIColor(rgb: 0x756E64, alpha: 0.75)"),
            ("inputTextColor: UIColor(rgb: 0x000000)", "inputTextColor: UIColor(rgb: 0x26221D)"),
            ("inputControlColor: UIColor(rgb: 0x000000, alpha: 0.5)", "inputControlColor: UIColor(rgb: 0x756E64, alpha: 0.8)"),
            ("primaryTextColor: UIColor(rgb: 0x000000, alpha: 1.0)", "primaryTextColor: UIColor(rgb: 0x26221D, alpha: 1.0)"),
            ("secondaryTextColor: UIColor(rgb: 0x202020, alpha: 0.6)", "secondaryTextColor: UIColor(rgb: 0x756E64, alpha: 0.8)"),
        ]),
        ("    let inputMediaPanel = PresentationThemeInputMediaPanel(", "\n    let inputButtonPanel =", [
            ("panelSeparatorColor: UIColor(rgb: 0xbec2c6)", "panelSeparatorColor: UIColor(rgb: 0xE3DED1)"),
            ("panelIconColor: UIColor(rgb: 0x858e99)", "panelIconColor: UIColor(rgb: 0x756E64)"),
            ("panelHighlightedIconBackgroundColor: UIColor(rgb: 0x858e99, alpha: 0.2)", "panelHighlightedIconBackgroundColor: UIColor(rgb: 0xA64038, alpha: 0.14)"),
            ("panelHighlightedIconColor: UIColor(rgb: 0x4D5561)", "panelHighlightedIconColor: UIColor(rgb: 0xA64038)"),
            ("stickersBackgroundColor: UIColor(rgb: 0xe8ebf0)", "stickersBackgroundColor: UIColor(rgb: 0xF0ECE2)"),
            ("stickersSectionTextColor: UIColor(rgb: 0x9099a2)", "stickersSectionTextColor: UIColor(rgb: 0x756E64)"),
            ("stickersSearchBackgroundColor: UIColor(rgb: 0xd9dbe1)", "stickersSearchBackgroundColor: UIColor(rgb: 0xE3DED1)"),
            ("stickersSearchPlaceholderColor: UIColor(rgb: 0x8e8e93)", "stickersSearchPlaceholderColor: UIColor(rgb: 0x938B7F)"),
            ("stickersSearchPrimaryColor: UIColor(rgb: 0x000000)", "stickersSearchPrimaryColor: UIColor(rgb: 0x26221D)"),
            ("stickersSearchControlColor: UIColor(rgb: 0x8e8e93)", "stickersSearchControlColor: UIColor(rgb: 0x756E64)"),
            ("gifsBackgroundColor: UIColor(rgb: 0xffffff)", "gifsBackgroundColor: UIColor(rgb: 0xF8F6EF)"),
            ("backgroundColor: UIColor(rgb: 0xffffff, alpha: 0.7)", "backgroundColor: UIColor(rgb: 0xF5F2E9, alpha: 0.94)"),
        ]),
        ("    let inputButtonPanel = PresentationThemeInputButtonPanel(", "\n    let historyNavigation =", [
            ("panelSeparatorColor: UIColor(rgb: 0xb2b2b2)", "panelSeparatorColor: UIColor(rgb: 0xD8D0C2)"),
            ("panelBackgroundColor: UIColor(rgb: 0xdddfd7, alpha: 0.8)", "panelBackgroundColor: UIColor(rgb: 0xF0ECE2, alpha: 0.94)"),
            ("buttonStrokeColor: UIColor(rgb: 0x353535, alpha: 0.2)", "buttonStrokeColor: UIColor(rgb: 0xB8B0A3, alpha: 0.4)"),
            ("buttonHighlightedFillColor: UIColor(rgb: 0xa8b3c0)", "buttonHighlightedFillColor: UIColor(rgb: 0xE3DED1)"),
            ("buttonHighlightedStrokeColor: UIColor(rgb: 0xc3c7c9)", "buttonHighlightedStrokeColor: UIColor(rgb: 0xB8B0A3)"),
            ("buttonTextColor: UIColor(rgb: 0x000000)", "buttonTextColor: UIColor(rgb: 0x26221D)"),
        ]),
        ("    let actionSheet = PresentationThemeActionSheet(", "\n    let contextMenu =", [
            ("opaqueItemBackgroundColor: UIColor(rgb: 0xffffff)", "opaqueItemBackgroundColor: UIColor(rgb: 0xFBF9F1)"),
            ("itemBackgroundColor: UIColor(white: 1.0, alpha: 0.8)", "itemBackgroundColor: UIColor(rgb: 0xFBF9F1, alpha: 0.96)"),
            ("opaqueItemHighlightedBackgroundColor: UIColor(white: 0.9, alpha: 1.0)", "opaqueItemHighlightedBackgroundColor: UIColor(rgb: 0xEDE8DC)"),
            ("itemHighlightedBackgroundColor: UIColor(white: 0.9, alpha: 0.7)", "itemHighlightedBackgroundColor: UIColor(rgb: 0xEDE8DC, alpha: 0.82)"),
            ("opaqueItemSeparatorColor: UIColor(white: 0.9, alpha: 1.0)", "opaqueItemSeparatorColor: UIColor(rgb: 0xE3DED1)"),
            ("destructiveActionTextColor: UIColor(rgb: 0xff3b30)", "destructiveActionTextColor: UIColor(rgb: 0x9F3C34)"),
            ("disabledActionTextColor: UIColor(rgb: 0xb3b3b3)", "disabledActionTextColor: UIColor(rgb: 0xB8B0A3)"),
            ("primaryTextColor: UIColor(rgb: 0x000000)", "primaryTextColor: UIColor(rgb: 0x26221D)"),
            ("secondaryTextColor: UIColor(rgb: 0x8e8e93)", "secondaryTextColor: UIColor(rgb: 0x756E64)"),
            ("inputHollowBackgroundColor: UIColor(rgb: 0xffffff)", "inputHollowBackgroundColor: UIColor(rgb: 0xFBF9F1)"),
            ("inputBorderColor: UIColor(rgb: 0xe4e4e6)", "inputBorderColor: UIColor(rgb: 0xD8D0C2)"),
            ("inputPlaceholderColor: UIColor(rgb: 0x8e8d92)", "inputPlaceholderColor: UIColor(rgb: 0x938B7F)"),
            ("inputTextColor: UIColor(rgb: 0x000000)", "inputTextColor: UIColor(rgb: 0x26221D)"),
        ]),
        ("    let contextMenu = PresentationThemeContextMenu(", "\n    let inAppNotification =", [
            ("backgroundColor: UIColor(rgb: 0xf9f9f9, alpha: 0.78)", "backgroundColor: UIColor(rgb: 0xF5F2E9, alpha: 0.96)"),
            ("itemSeparatorColor: UIColor(rgb: 0x3c3c43, alpha: 0.2)", "itemSeparatorColor: UIColor(rgb: 0x8F877A, alpha: 0.18)"),
            ("sectionSeparatorColor: UIColor(rgb: 0x8a8a8a, alpha: 0.2)", "sectionSeparatorColor: UIColor(rgb: 0x8F877A, alpha: 0.2)"),
            ("itemHighlightedBackgroundColor: UIColor(rgb: 0x3c3c43, alpha: 0.2)", "itemHighlightedBackgroundColor: UIColor(rgb: 0xA64038, alpha: 0.12)"),
            ("primaryColor: UIColor(rgb: 0x000000)", "primaryColor: UIColor(rgb: 0x26221D)"),
            ("secondaryColor: UIColor(rgb: 0x000000, alpha: 0.5)", "secondaryColor: UIColor(rgb: 0x756E64, alpha: 0.8)"),
            ("destructiveColor: UIColor(rgb: 0xff3b30)", "destructiveColor: UIColor(rgb: 0x9F3C34)"),
            ("badgeInactiveFillColor: UIColor(rgb: 0xb6b6bb)", "badgeInactiveFillColor: UIColor(rgb: 0xAAA293)"),
        ]),
        ("    let inAppNotification = PresentationThemeInAppNotification(", "\n    let chart =", [
            ("fillColor: UIColor(rgb: 0xffffff)", "fillColor: UIColor(rgb: 0xF5F2E9)"),
            ("primaryTextColor: UIColor(rgb: 0x000000)", "primaryTextColor: UIColor(rgb: 0x26221D)"),
            ("backgroundColor: UIColor(rgb: 0xffffff)", "backgroundColor: UIColor(rgb: 0xF5F2E9)"),
            ("controlColor: UIColor(rgb: 0x7e8791)", "controlColor: UIColor(rgb: 0x756E64)"),
            ("separatorColor: UIColor(rgb: 0xc8c7cc)", "separatorColor: UIColor(rgb: 0xD8D0C2)"),
        ]),
        ("    let chart = PresentationThemeChart(", "\n    return PresentationTheme(", [
            ("labelsColor: UIColor(rgb: 0x252529, alpha: 0.5)", "labelsColor: UIColor(rgb: 0x756E64, alpha: 0.75)"),
            ("helperLinesColor: UIColor(rgb: 0x182d3b, alpha: 0.3)", "helperLinesColor: UIColor(rgb: 0x8F877A, alpha: 0.22)"),
            ("strongLinesColor: UIColor(rgb: 0x182d3b, alpha: 0.3)", "strongLinesColor: UIColor(rgb: 0x8F877A, alpha: 0.28)"),
            ("detailsViewColor: UIColor(rgb: 0xf5f5fb)", "detailsViewColor: UIColor(rgb: 0xF0ECE2)"),
            ("rangeViewFrameColor: UIColor(rgb: 0xcad4de)", "rangeViewFrameColor: UIColor(rgb: 0xD8D0C2)"),
        ]),
    ]
    for start, end, rules in blocks:
        text = patch_region(text, start, end, rules, f"day theme {start.strip()}")

    # The stock day appearance uses messageDay, not the alternate message block
    # patched by the earlier palette overlay; recolor the live bubbles explicitly.
    text = patch_region(text, "    let messageDay = PresentationThemeChatMessage(", "\n    let serviceMessage =", [
        ("fill: [UIColor(rgb: 0xffffff)]", "fill: [UIColor(rgb: 0xFDFBF5)]"),
        ("highlightedFill: UIColor(rgb: 0xdadade)", "highlightedFill: UIColor(rgb: 0xEFE9DE)"),
        ("stroke: UIColor(rgb: 0xffffff)", "stroke: UIColor(rgb: 0xE3DED1)"),
        ("fill: [UIColor(rgb: 0xf1f1f4)]", "fill: [UIColor(rgb: 0xF4F0E5)]"),
        ("stroke: UIColor(rgb: 0xf1f1f4)", "stroke: UIColor(rgb: 0xE3DED1)"),
        ("primaryTextColor: UIColor(rgb: 0x000000)", "primaryTextColor: UIColor(rgb: 0x26221D)"),
        ("secondaryTextColor: UIColor(rgb: 0x525252, alpha: 0.6)", "secondaryTextColor: UIColor(rgb: 0x756E64, alpha: 0.88)"),
        ("linkTextColor: UIColor(rgb: 0x004bad)", "linkTextColor: UIColor(rgb: 0xA64038)"),
        ("textHighlightColor: UIColor(rgb: 0xffc738)", "textHighlightColor: UIColor(rgb: 0xE7D6B5)"),
        ("fill: [UIColor(rgb: 0x57b2e0), defaultDayAccentColor]", "fill: [UIColor(rgb: 0xB86454), UIColor(rgb: 0xA64038)]"),
        ("highlightedFill: UIColor(rgb: 0x57b2e0).withMultipliedBrightnessBy(0.7)", "highlightedFill: UIColor(rgb: 0x91463C).withMultipliedBrightnessBy(0.88)"),
        ("mediaPlaceholderColor: UIColor(rgb: 0x0077d9)", "mediaPlaceholderColor: UIColor(rgb: 0xA64038)"),
        ("infoPrimaryTextColor: UIColor(rgb: 0x000000)", "infoPrimaryTextColor: UIColor(rgb: 0x26221D)"),
        ("infoLinkTextColor: UIColor(rgb: 0x004bad)", "infoLinkTextColor: UIColor(rgb: 0xA64038)"),
        ("fill: [UIColor(rgb: 0xe5e5ea)]", "fill: [UIColor(rgb: 0xF0ECE2)]"),
        ("stroke: UIColor(rgb: 0xe5e5ea)", "stroke: UIColor(rgb: 0xE3DED1)"),
    ], "day messageDay live bubbles")
    path.write_text(text, encoding="utf-8")


def patch_dark_theme(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if DARK_MARKER in text:
        return
    text = replace_exact(
        text,
        "    let rootNavigationBar = PresentationThemeRootNavigationBar(",
        f"    // {DARK_MARKER}: deep ink, warm paper text and muted cinnabar accents.\n    let rootNavigationBar = PresentationThemeRootNavigationBar(",
        "dark theme version marker",
    )
    blocks = [
        ("public let defaultDarkWallpaperGradientColors: [UIColor] = [", "\n]", [
            ("UIColor(rgb: 0x598bf6)", "UIColor(rgb: 0x758478)"),
            ("UIColor(rgb: 0x7a5eef)", "UIColor(rgb: 0x4B5A52)"),
            ("UIColor(rgb: 0xd67cff)", "UIColor(rgb: 0xA66A5D)"),
            ("UIColor(rgb: 0xf38b58)", "UIColor(rgb: 0x8A574A)"),
        ]),
        ("    let rootNavigationBar = PresentationThemeRootNavigationBar(", "\n    let rootTabBar =", [
            ("buttonColor: UIColor(rgb: 0xffffff)", "buttonColor: UIColor(rgb: 0xB96E60)"),
            ("primaryTextColor: UIColor(rgb: 0xffffff)", "primaryTextColor: UIColor(rgb: 0xEEE7D7)"),
            ("secondaryTextColor: UIColor(rgb: 0xffffff, alpha: 0.5)", "secondaryTextColor: UIColor(rgb: 0xB7AFA0, alpha: 0.8)"),
            ("controlColor: UIColor(rgb: 0x767676)", "controlColor: UIColor(rgb: 0xA79F92)"),
            ("accentTextColor: UIColor(rgb: 0xffffff)", "accentTextColor: UIColor(rgb: 0xB96E60)"),
            ("blurredBackgroundColor: UIColor(rgb: 0x1d1d1d, alpha: 0.9)", "blurredBackgroundColor: UIColor(rgb: 0x1B201E, alpha: 0.94)"),
            ("UIColor(rgb: 0x1d1d1d).mixedWith(UIColor(rgb: 0x000000), alpha: 0.1)", "UIColor(rgb: 0x1B201E)"),
            ("separatorColor: UIColor(rgb: 0x545458, alpha: 0.55)", "separatorColor: UIColor(rgb: 0x414A44, alpha: 0.8)"),
            ("badgeBackgroundColor:  UIColor(rgb: 0xffffff)", "badgeBackgroundColor:  UIColor(rgb: 0xA64038)"),
            ("badgeStrokeColor: UIColor(rgb: 0x1c1c1d)", "badgeStrokeColor: UIColor(rgb: 0x1B201E)"),
            ("badgeTextColor:  UIColor(rgb: 0x000000)", "badgeTextColor:  UIColor(rgb: 0xF5F2E9)"),
            ("segmentedBackgroundColor: UIColor(rgb: 0xffffff, alpha: 0.11)", "segmentedBackgroundColor: UIColor(rgb: 0xEEE7D7, alpha: 0.08)"),
            ("segmentedForegroundColor: UIColor(rgb: 0xffffff, alpha: 0.36)", "segmentedForegroundColor: UIColor(rgb: 0xA64038, alpha: 0.45)"),
            ("segmentedTextColor: UIColor(rgb: 0xffffff)", "segmentedTextColor: UIColor(rgb: 0xEEE7D7)"),
            ("segmentedDividerColor: UIColor(rgb: 0x505155)", "segmentedDividerColor: UIColor(rgb: 0x414A44)"),
            ("clearButtonBackgroundColor: UIColor(rgb: 0xffffff, alpha: 0.1)", "clearButtonBackgroundColor: UIColor(rgb: 0xEEE7D7, alpha: 0.08)"),
            ("clearButtonForegroundColor: UIColor(rgb: 0xffffff)", "clearButtonForegroundColor: UIColor(rgb: 0xEEE7D7)"),
        ]),
        ("    let rootTabBar = PresentationThemeRootTabBar(", "\n    let navigationSearchBar =", [
            ("separatorColor: UIColor(rgb: 0x545458, alpha: 0.55)", "separatorColor: UIColor(rgb: 0x414A44, alpha: 0.8)"),
            ("iconColor: UIColor(rgb: 0xffffff)", "iconColor: UIColor(rgb: 0xB7AFA0)"),
            ("selectedIconColor: UIColor(rgb: 0xffffff)", "selectedIconColor: UIColor(rgb: 0xB96E60)"),
            ("textColor: UIColor(rgb: 0xffffff)", "textColor: UIColor(rgb: 0xB7AFA0)"),
            ("selectedTextColor: UIColor(rgb: 0xffffff)", "selectedTextColor: UIColor(rgb: 0xB96E60)"),
            ("badgeBackgroundColor:  UIColor(rgb: 0xffffff)", "badgeBackgroundColor:  UIColor(rgb: 0xA64038)"),
            ("badgeStrokeColor: UIColor(rgb: 0x1c1c1d)", "badgeStrokeColor: UIColor(rgb: 0x1B201E)"),
            ("badgeTextColor:  UIColor(rgb: 0x000000)", "badgeTextColor:  UIColor(rgb: 0xF5F2E9)"),
        ]),
        ("    let navigationSearchBar = PresentationThemeNavigationSearchBar(", "\n    let intro =", [
            ("backgroundColor: UIColor(rgb: 0x1c1c1d)", "backgroundColor: UIColor(rgb: 0x1B201E)"),
            ("accentColor: UIColor(rgb: 0xffffff)", "accentColor: UIColor(rgb: 0xB96E60)"),
            ("inputFillColor: UIColor(white: 1.0, alpha: 0.1)", "inputFillColor: UIColor(rgb: 0xEEE7D7, alpha: 0.08)"),
            ("inputTextColor: UIColor(rgb: 0xffffff)", "inputTextColor: UIColor(rgb: 0xEEE7D7)"),
            ("inputPlaceholderTextColor: UIColor(rgb: 0x8f8f8f)", "inputPlaceholderTextColor: UIColor(rgb: 0xA79F92)"),
            ("inputIconColor: UIColor(rgb: 0x8f8f8f)", "inputIconColor: UIColor(rgb: 0xA79F92)"),
            ("inputClearButtonColor: UIColor(rgb: 0x8f8f8f)", "inputClearButtonColor: UIColor(rgb: 0xA79F92)"),
            ("separatorColor: UIColor(rgb: 0x545458, alpha: 0.55)", "separatorColor: UIColor(rgb: 0x414A44, alpha: 0.8)"),
        ]),
        ("    let intro = PresentationThemeIntro(", "\n    let passcode =", [
            ("primaryTextColor: UIColor(rgb: 0xffffff)", "primaryTextColor: UIColor(rgb: 0xEEE7D7)"),
            ("accentTextColor: UIColor(rgb: 0xffffff)", "accentTextColor: UIColor(rgb: 0xB96E60)"),
            ("startButtonColor: UIColor(rgb: 0xffffff)", "startButtonColor: UIColor(rgb: 0xB96E60)"),
            ("dotColor: UIColor(rgb: 0x5e5e5e)", "dotColor: UIColor(rgb: 0x6D756E)"),
        ]),
        ("    let passcode = PresentationThemePasscode(", "\n    let rootController =", [
            ("topColor: UIColor(rgb: 0x000000)", "topColor: UIColor(rgb: 0x141816)"),
            ("bottomColor: UIColor(rgb: 0x000000)", "bottomColor: UIColor(rgb: 0x222824)"),
            ("buttonColor: UIColor(rgb: 0x1c1c1d)", "buttonColor: UIColor(rgb: 0x242B26)"),
        ]),
        ("    let switchColors = PresentationThemeSwitch(", "\n    let list =", [
            ("frameColor: UIColor(rgb: 0x39393d)", "frameColor: UIColor(rgb: 0x424A44)"),
            ("handleColor: UIColor(rgb: 0x121212)", "handleColor: UIColor(rgb: 0xEEE7D7)"),
            ("contentColor: UIColor(rgb: 0x67ce67)", "contentColor: UIColor(rgb: 0x819281)"),
            ("positiveColor: UIColor(rgb: 0x08a723)", "positiveColor: UIColor(rgb: 0x718675)"),
            ("negativeColor: UIColor(rgb: 0xeb5545)", "negativeColor: UIColor(rgb: 0xA64038)"),
        ]),
        ("    let list = PresentationThemeList(", "\n    let chatList =", [
            ("blocksBackgroundColor: UIColor(rgb: 0x000000)", "blocksBackgroundColor: UIColor(rgb: 0x141816)"),
            ("modalBlocksBackgroundColor: UIColor(rgb: 0x1c1c1d)", "modalBlocksBackgroundColor: UIColor(rgb: 0x202622)"),
            ("plainBackgroundColor: UIColor(rgb: 0x000000)", "plainBackgroundColor: UIColor(rgb: 0x141816)"),
            ("modalPlainBackgroundColor: UIColor(rgb: 0x1c1c1d)", "modalPlainBackgroundColor: UIColor(rgb: 0x202622)"),
            ("itemPrimaryTextColor: UIColor(rgb: 0xffffff)", "itemPrimaryTextColor: UIColor(rgb: 0xEEE7D7)"),
            ("itemSecondaryTextColor: UIColor(rgb: 0x98989e)", "itemSecondaryTextColor: UIColor(rgb: 0xB2A99A)"),
            ("itemDisabledTextColor: UIColor(rgb: 0x8f8f8f)", "itemDisabledTextColor: UIColor(rgb: 0x8E887D)"),
            ("itemAccentColor: UIColor(rgb: 0xffffff)", "itemAccentColor: UIColor(rgb: 0xB96E60)"),
            ("itemHighlightedColor: UIColor(rgb: 0x28b772)", "itemHighlightedColor: UIColor(rgb: 0x839183)"),
            ("itemDestructiveColor: UIColor(rgb: 0xeb5545)", "itemDestructiveColor: UIColor(rgb: 0xA64038)"),
            ("itemPlaceholderTextColor: UIColor(rgb: 0x4d4d4d)", "itemPlaceholderTextColor: UIColor(rgb: 0x68716A)"),
            ("itemBlocksBackgroundColor: UIColor(rgb: 0x1c1c1d)", "itemBlocksBackgroundColor: UIColor(rgb: 0x202622)"),
            ("itemModalBlocksBackgroundColor: UIColor(rgb: 0x2c2c2e)", "itemModalBlocksBackgroundColor: UIColor(rgb: 0x2A312C)"),
            ("itemHighlightedBackgroundColor: UIColor(rgb: 0x313135)", "itemHighlightedBackgroundColor: UIColor(rgb: 0x343C36)"),
            ("itemBlocksSeparatorColor: UIColor(rgb: 0x545458, alpha: 0.55)", "itemBlocksSeparatorColor: UIColor(rgb: 0x414A44, alpha: 0.8)"),
            ("itemPlainSeparatorColor: UIColor(rgb: 0x545458, alpha: 0.55)", "itemPlainSeparatorColor: UIColor(rgb: 0x414A44, alpha: 0.8)"),
            ("sectionHeaderTextColor: UIColor(rgb: 0x8d8e93)", "sectionHeaderTextColor: UIColor(rgb: 0xA79F92)"),
            ("freeTextColor: UIColor(rgb: 0x8d8e93)", "freeTextColor: UIColor(rgb: 0xA79F92)"),
            ("freeTextSuccessColor: UIColor(rgb: 0x30cf30)", "freeTextSuccessColor: UIColor(rgb: 0x839183)"),
            ("freeInputField: PresentationInputFieldTheme(\n            backgroundColor: UIColor(rgb: 0x272728)", "freeInputField: PresentationInputFieldTheme(\n            backgroundColor: UIColor(rgb: 0x242B26)"),
            ("freePlainInputField: PresentationInputFieldTheme(\n            backgroundColor: UIColor(rgb: 0x272728)", "freePlainInputField: PresentationInputFieldTheme(\n            backgroundColor: UIColor(rgb: 0x242B26)"),
            ("mediaPlaceholderColor: UIColor(rgb: 0xffffff).mixedWith(UIColor(rgb: 0x1c1c1d), alpha: 0.9)", "mediaPlaceholderColor: UIColor(rgb: 0xEEE7D7).mixedWith(UIColor(rgb: 0x202622), alpha: 0.9)"),
            ("itemInputField: PresentationInputFieldTheme(backgroundColor: UIColor(rgb: 0x0f0f0f), strokeColor: UIColor(rgb: 0x0f0f0f)", "itemInputField: PresentationInputFieldTheme(backgroundColor: UIColor(rgb: 0x202622), strokeColor: UIColor(rgb: 0x202622)"),
        ]),
        ("    let chatList = PresentationThemeChatList(", "\n    let incomingBubbleAlpha", [
            ("backgroundColor: UIColor(rgb: 0x000000)", "backgroundColor: UIColor(rgb: 0x141816)"),
            ("itemBackgroundColor: UIColor(rgb: 0x000000)", "itemBackgroundColor: UIColor(rgb: 0x141816)"),
            ("pinnedItemBackgroundColor: UIColor(rgb: 0x1c1c1d)", "pinnedItemBackgroundColor: UIColor(rgb: 0x202622)"),
            ("itemHighlightedBackgroundColor: UIColor(rgb: 0x121212)", "itemHighlightedBackgroundColor: UIColor(rgb: 0x29302B)"),
            ("pinnedItemHighlightedBackgroundColor: UIColor(rgb: 0x2b2b2c)", "pinnedItemHighlightedBackgroundColor: UIColor(rgb: 0x343C36)"),
            ("itemSelectedBackgroundColor: UIColor(rgb: 0x191919)", "itemSelectedBackgroundColor: UIColor(rgb: 0x343C36)"),
            ("titleColor: UIColor(rgb: 0xffffff)", "titleColor: UIColor(rgb: 0xEEE7D7)"),
            ("secretTitleColor: UIColor(rgb: 0x00b12c)", "secretTitleColor: UIColor(rgb: 0x839183)"),
            ("dateTextColor: UIColor(rgb: 0x8d8e93)", "dateTextColor: UIColor(rgb: 0xA79F92)"),
            ("authorNameColor: UIColor(rgb: 0xffffff)", "authorNameColor: UIColor(rgb: 0xEEE7D7)"),
            ("messageTextColor: UIColor(rgb: 0x8d8e93)", "messageTextColor: UIColor(rgb: 0xB2A99A)"),
            ("messageHighlightedTextColor: UIColor(rgb: 0xffffff)", "messageHighlightedTextColor: UIColor(rgb: 0xEEE7D7)"),
            ("messageDraftTextColor: UIColor(rgb: 0xdd4b39)", "messageDraftTextColor: UIColor(rgb: 0xC16D5F)"),
            ("checkmarkColor: UIColor(rgb: 0xffffff)", "checkmarkColor: UIColor(rgb: 0xB96E60)"),
            ("failedFillColor: UIColor(rgb: 0xeb5545)", "failedFillColor: UIColor(rgb: 0xA64038)"),
            ("unreadBadgeActiveBackgroundColor: UIColor(rgb: 0xffffff)", "unreadBadgeActiveBackgroundColor: UIColor(rgb: 0xA64038)"),
            ("unreadBadgeActiveTextColor: UIColor(rgb: 0x000000)", "unreadBadgeActiveTextColor: UIColor(rgb: 0xF5F2E9)"),
            ("reactionBadgeActiveBackgroundColor: UIColor(rgb: 0xFF2D55)", "reactionBadgeActiveBackgroundColor: UIColor(rgb: 0xA64038)"),
            ("pinnedSearchBarColor: UIColor(rgb: 0x272728)", "pinnedSearchBarColor: UIColor(rgb: 0x242B26)"),
            ("regularSearchBarColor: UIColor(rgb: 0x272728)", "regularSearchBarColor: UIColor(rgb: 0x242B26)"),
            ("sectionHeaderFillColor: .black", "sectionHeaderFillColor: UIColor(rgb: 0x202622)"),
            ("sectionHeaderTextColor: UIColor(rgb: 0x8d8e93)", "sectionHeaderTextColor: UIColor(rgb: 0xA79F92)"),
            ("verifiedIconFillColor: UIColor(rgb: 0xffffff)", "verifiedIconFillColor: UIColor(rgb: 0xB96E60)"),
            ("verifiedIconForegroundColor:  UIColor(rgb: 0x000000)", "verifiedIconForegroundColor:  UIColor(rgb: 0xF5F2E9)"),
            ("secretIconColor: UIColor(rgb: 0x00b12c)", "secretIconColor: UIColor(rgb: 0x839183)"),
            ("onlineDotColor: UIColor(rgb: 0x4cc91f)", "onlineDotColor: UIColor(rgb: 0x839183)"),
        ]),
        ("    let message = PresentationThemeChatMessage(", "\n    let serviceMessage =", [
            ("fill: [UIColor(rgb: 0x1D1D1D, alpha: incomingBubbleAlpha)]", "fill: [UIColor(rgb: 0x252C27, alpha: incomingBubbleAlpha)]"),
            ("fill: [UIColor(rgb: 0x61BCF9), UIColor(rgb: 0x0088ff)]", "fill: [UIColor(rgb: 0xA85B4E), UIColor(rgb: 0x7F463E)]"),
            ("highlightedFill: UIColor(rgb: 0x61BCF9)", "highlightedFill: UIColor(rgb: 0xB96E60)"),
            ("fill: [UIColor(rgb: 0x1f1f1f)]", "fill: [UIColor(rgb: 0x202622)]"),
            ("highlightedFill: UIColor(rgb: 0x2a2a2a)", "highlightedFill: UIColor(rgb: 0x343C36)"),
            ("stroke: UIColor(rgb: 0x1f1f1f)", "stroke: UIColor(rgb: 0x202622)"),
        ]),
        ("    let serviceMessage = PresentationThemeServiceMessage(", "\n    let inputPanelMediaRecordingControl =", [
            ("fill: UIColor(rgb: 0x1f1f1f, alpha: 1.0)", "fill: UIColor(rgb: 0x202622, alpha: 0.96)"),
            ("unreadBarFillColor: UIColor(rgb: 0x1b1b1b)", "unreadBarFillColor: UIColor(rgb: 0x29302B)"),
            ("unreadBarStrokeColor: UIColor(rgb: 0x1b1b1b)", "unreadBarStrokeColor: UIColor(rgb: 0x414A44)"),
        ]),
        ("    let inputPanel = PresentationThemeChatInputPanel(", "\n    let inputMediaBackgroundColor =", [
            ("panelBackgroundColorNoWallpaper: UIColor(rgb: 0x000000)", "panelBackgroundColorNoWallpaper: UIColor(rgb: 0x141816)"),
            ("panelSeparatorColor: UIColor(rgb: 0x545458, alpha: 0.55)", "panelSeparatorColor: UIColor(rgb: 0x414A44, alpha: 0.8)"),
            ("panelControlAccentColor: UIColor(rgb: 0xffffff)", "panelControlAccentColor: UIColor(rgb: 0xB96E60)"),
            ("inputBackgroundColor: UIColor(rgb: 0xffffff, alpha: 0.14).blitOver(.black, alpha: 1.0).withAlphaComponent(0.95)", "inputBackgroundColor: UIColor(rgb: 0xEEE7D7, alpha: 0.10).blitOver(UIColor(rgb: 0x141816), alpha: 1.0).withAlphaComponent(0.96)"),
            ("inputTextColor: UIColor(rgb: 0xffffff)", "inputTextColor: UIColor(rgb: 0xEEE7D7)"),
            ("actionControlFillColor: UIColor(rgb: 0xffffff)", "actionControlFillColor: UIColor(rgb: 0xB96E60)"),
            ("actionControlForegroundColor:  UIColor(rgb: 0x000000)", "actionControlForegroundColor:  UIColor(rgb: 0xF5F2E9)"),
            ("mediaRecordingDotColor: UIColor(rgb: 0xeb5545)", "mediaRecordingDotColor: UIColor(rgb: 0xA64038)"),
        ]),
        ("    let actionSheet = PresentationThemeActionSheet(", "\n    let contextMenu =", [
            ("opaqueItemBackgroundColor: UIColor(rgb: 0x1c1c1d)", "opaqueItemBackgroundColor: UIColor(rgb: 0x202622)"),
            ("itemBackgroundColor: UIColor(rgb: 0x1c1c1d, alpha: 0.8)", "itemBackgroundColor: UIColor(rgb: 0x202622, alpha: 0.96)"),
            ("opaqueItemHighlightedBackgroundColor: UIColor(white: 0.0, alpha: 1.0)", "opaqueItemHighlightedBackgroundColor: UIColor(rgb: 0x343C36)"),
            ("itemHighlightedBackgroundColor: UIColor(rgb: 0x000000, alpha: 0.5)", "itemHighlightedBackgroundColor: UIColor(rgb: 0x343C36, alpha: 0.9)"),
            ("opaqueItemSeparatorColor: UIColor(rgb: 0x545458, alpha: 0.55)", "opaqueItemSeparatorColor: UIColor(rgb: 0x414A44, alpha: 0.8)"),
            ("standardActionTextColor: UIColor(rgb: 0xffffff)", "standardActionTextColor: UIColor(rgb: 0xB96E60)"),
            ("destructiveActionTextColor: UIColor(rgb: 0xeb5545)", "destructiveActionTextColor: UIColor(rgb: 0xA64038)"),
            ("disabledActionTextColor: UIColor(rgb: 0x4d4d4d)", "disabledActionTextColor: UIColor(rgb: 0x777E77)"),
            ("primaryTextColor: UIColor(rgb: 0xffffff)", "primaryTextColor: UIColor(rgb: 0xEEE7D7)"),
            ("secondaryTextColor: UIColor(rgb: 0x5e5e5e)", "secondaryTextColor: UIColor(rgb: 0xB7AFA0)"),
            ("controlAccentColor: UIColor(rgb: 0xffffff)", "controlAccentColor: UIColor(rgb: 0xB96E60)"),
            ("inputBackgroundColor: UIColor(rgb: 0x0f0f0f)", "inputBackgroundColor: UIColor(rgb: 0x242B26)"),
            ("inputHollowBackgroundColor: UIColor(rgb: 0x0f0f0f)", "inputHollowBackgroundColor: UIColor(rgb: 0x242B26)"),
            ("inputBorderColor: UIColor(rgb: 0x0f0f0f)", "inputBorderColor: UIColor(rgb: 0x414A44)"),
            ("inputPlaceholderColor: UIColor(rgb: 0x8f8f8f)", "inputPlaceholderColor: UIColor(rgb: 0xA79F92)"),
            ("inputTextColor: UIColor(rgb: 0xffffff)", "inputTextColor: UIColor(rgb: 0xEEE7D7)"),
            ("inputClearButtonColor: UIColor(rgb: 0x8f8f8f)", "inputClearButtonColor: UIColor(rgb: 0xA79F92)"),
            ("checkContentColor:  UIColor(rgb: 0x000000)", "checkContentColor:  UIColor(rgb: 0xF5F2E9)"),
        ]),
        ("    let contextMenu = PresentationThemeContextMenu(", "\n    let inAppNotification =", [
            ("backgroundColor: UIColor(rgb: 0x252525, alpha: 0.78)", "backgroundColor: UIColor(rgb: 0x202622, alpha: 0.96)"),
            ("itemSeparatorColor: UIColor(rgb: 0xffffff, alpha: 0.15)", "itemSeparatorColor: UIColor(rgb: 0x414A44, alpha: 0.8)"),
            ("sectionSeparatorColor: UIColor(rgb: 0x000000, alpha: 0.2)", "sectionSeparatorColor: UIColor(rgb: 0x414A44, alpha: 0.8)"),
            ("itemHighlightedBackgroundColor: UIColor(rgb: 0xffffff, alpha: 0.15)", "itemHighlightedBackgroundColor: UIColor(rgb: 0xB96E60, alpha: 0.18)"),
            ("primaryColor: UIColor(rgb: 0xffffff, alpha: 1.0)", "primaryColor: UIColor(rgb: 0xEEE7D7, alpha: 1.0)"),
            ("secondaryColor: UIColor(rgb: 0xffffff, alpha: 0.5)", "secondaryColor: UIColor(rgb: 0xB7AFA0, alpha: 0.8)"),
            ("destructiveColor: UIColor(rgb: 0xeb5545)", "destructiveColor: UIColor(rgb: 0xA64038)"),
            ("badgeFillColor: UIColor(rgb: 0xffffff)", "badgeFillColor: UIColor(rgb: 0xA64038)"),
            ("badgeForegroundColor: UIColor(rgb: 0x000000)", "badgeForegroundColor: UIColor(rgb: 0xF5F2E9)"),
            ("badgeInactiveFillColor: UIColor(rgb: 0xffffff).withAlphaComponent(0.5)", "badgeInactiveFillColor: UIColor(rgb: 0x545E57)"),
            ("badgeInactiveForegroundColor: UIColor(rgb: 0x000000)", "badgeInactiveForegroundColor: UIColor(rgb: 0xEEE7D7)"),
        ]),
        ("    let inAppNotification = PresentationThemeInAppNotification(", "\n    let chart =", [
            ("fillColor: UIColor(rgb: 0x1c1c1d)", "fillColor: UIColor(rgb: 0x202622)"),
            ("primaryTextColor: UIColor(rgb: 0xffffff)", "primaryTextColor: UIColor(rgb: 0xEEE7D7)"),
            ("backgroundColor: UIColor(rgb: 0x1c1c1d)", "backgroundColor: UIColor(rgb: 0x202622)"),
            ("controlColor: UIColor(rgb: 0xffffff)", "controlColor: UIColor(rgb: 0xB96E60)"),
            ("separatorColor: UIColor(rgb: 0x000000)", "separatorColor: UIColor(rgb: 0x414A44)"),
        ]),
    ]
    for start, end, rules in blocks:
        text = patch_region(text, start, end, rules, f"dark theme {start.strip()}")
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", required=True, type=Path)
    args = parser.parse_args()
    root = args.upstream.resolve()
    actual = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if actual != EXPECTED_SHA:
        raise SystemExit(f"Expected Telegram upstream {EXPECTED_SHA}, found {actual}")
    patch_day_theme(root / "submodules/TelegramPresentationData/Sources/DefaultDayPresentationTheme.swift")
    patch_dark_theme(root / "submodules/TelegramPresentationData/Sources/DefaultDarkPresentationTheme.swift")
    print("Applied the shared ink-wash palette to light and dark client themes.")


if __name__ == "__main__":
    main()
