#!/usr/bin/env python3
"""Apply component-level ink-wash styling beyond palette and wallpaper changes."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path

EXPECTED_SHA = "fb0e62ba8a147f0821da6aa63c09da7d79a10111"


def replace_exact(text: str, old: str, new: str, label: str, expected: int = 1) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{label}: expected {expected} match(es), found {count}")
    return text.replace(old, new, expected)


def patch_settings_icon_catalog(root: Path) -> None:
    path = root / "submodules/TelegramPresentationData/Sources/Resources/PresentationResourcesSettings.swift"
    text = path.read_text(encoding="utf-8")
    marker = "// CUE_INKWASH_SETTINGS_ICON_CATALOG_V1"
    if marker in text:
        return

    text = replace_exact(
        text,
        "context.setFillColor(UIColor.white.cgColor)\n                context.fill(imageRect)",
        "context.setFillColor(UIColor(rgb: 0x3D342B).cgColor)\n                context.fill(imageRect)",
        "Settings icon ink glyph",
    )
    text = replace_exact(
        text,
        "                context.restoreGState()\n            }\n            \n            let outerPath = UIBezierPath(rect: CGRect(origin: .zero, size: size))",
        "                context.restoreGState()\n                context.setFillColor(UIColor(rgb: 0xA64038).cgColor)\n                context.fillEllipse(in: CGRect(x: size.width - 6.5, y: size.height - 6.5, width: 4.0, height: 4.0))\n            }\n            \n            let outerPath = UIBezierPath(rect: CGRect(origin: .zero, size: size))",
        "Settings icon cinnabar seal",
    )

    palette = [
        ("let colorRed = UIColor(rgb: 0xFF453A)", "let colorRed = UIColor(rgb: 0xE7E0D2)"),
        ("let colorGreen = UIColor(rgb: 0x34C759)", "let colorGreen = UIColor(rgb: 0xE7E0D2)"),
        ("let colorBlue = UIColor(rgb: 0x0a84ff)", "let colorBlue = UIColor(rgb: 0xE7E0D2)"),
        ("let colorLightBlue = UIColor(rgb: 0x32ADE6)", "let colorLightBlue = UIColor(rgb: 0xE7E0D2)"),
        ("let colorTeal = UIColor(rgb: 0x00c7be)", "let colorTeal = UIColor(rgb: 0xE7E0D2)"),
        ("let colorOrange = UIColor(rgb: 0xFF9F0A)", "let colorOrange = UIColor(rgb: 0xE7E0D2)"),
        ("let colorPurple = UIColor(rgb: 0xAF52DE)", "let colorPurple = UIColor(rgb: 0xE7E0D2)"),
        ("let colorGray = UIColor(rgb: 0x8E8E93)", "let colorGray = UIColor(rgb: 0xE7E0D2)"),
        ("let colorViolet = UIColor(rgb: 0x5E5CE6)", "let colorViolet = UIColor(rgb: 0xE7E0D2)"),
        (
            'public static let business = renderSettingsIcon(name: "Item List/Icons/Business", backgroundColors: [UIColor(rgb: 0xA95CE3), UIColor(rgb: 0xF16B80)])',
            'public static let business = renderSettingsIcon(name: "Item List/Icons/Business", backgroundColors: [UIColor(rgb: 0xE7E0D2)])',
        ),
    ]
    for old, new in palette:
        text = replace_exact(text, old, new, f"Settings icon paper palette: {old}")
    text = replace_exact(
        text,
        "let colorRed = UIColor(rgb: 0xE7E0D2)",
        marker + "\nlet colorRed = UIColor(rgb: 0xE7E0D2)",
        "Settings icon style marker",
    )
    path.write_text(text, encoding="utf-8")


def patch_peer_info_cards(root: Path) -> None:
    path = root / "submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoScreenItemSectionContainerNode.swift"
    text = path.read_text(encoding="utf-8")
    marker = "// CUE_INKWASH_PAPER_SECTION_CARD_V1"
    if marker in text:
        return
    anchor = "        self.backgroundNode.backgroundColor = presentationData.theme.list.itemBlocksBackgroundColor\n"
    addition = '''        // CUE_INKWASH_PAPER_SECTION_CARD_V1: outlined paper panels for shared PeerInfo groups.
        self.backgroundNode.layer.cornerRadius = 16.0
        self.backgroundNode.layer.borderWidth = 1.0 / UIScreen.main.scale
        self.backgroundNode.layer.borderColor = (presentationData.theme.overallDarkAppearance ? UIColor(rgb: 0x51493D) : UIColor(rgb: 0xDED5C5)).cgColor
'''
    text = replace_exact(text, anchor, anchor + addition, "PeerInfo paper card surface")
    path.write_text(text, encoding="utf-8")


def patch_peer_info_section_titles(root: Path) -> None:
    path = root / "submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/ListItems/PeerInfoScreenHeaderItem.swift"
    text = path.read_text(encoding="utf-8")
    marker = "// CUE_INKWASH_SECTION_TITLE_STYLE_V1"
    if marker in text:
        return
    old = "        self.textNode.attributedText = NSAttributedString(string: item.text, font: Font.regular(13.0), textColor: presentationData.theme.list.freeTextColor)"
    new = "        // CUE_INKWASH_SECTION_TITLE_STYLE_V1\n        self.textNode.attributedText = NSAttributedString(string: item.text, font: Font.semibold(13.0), textColor: presentationData.theme.list.itemAccentColor)"
    text = replace_exact(text, old, new, "Ink section title typography")
    path.write_text(text, encoding="utf-8")


def patch_settings_spacing(root: Path) -> None:
    path = root / "submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoScreen.swift"
    text = path.read_text(encoding="utf-8")
    marker = "CUE_INKWASH_SETTINGS_SPACING_V1"
    if marker in text:
        return
    text = replace_exact(
        text,
        "        let sectionSpacing: CGFloat = 24.0",
        "        let sectionSpacing: CGFloat = self.isSettings ? 30.0 : 24.0 // CUE_INKWASH_SETTINGS_SPACING_V1",
        "Settings-only section rhythm",
    )
    path.write_text(text, encoding="utf-8")


def patch_tab_bar(root: Path) -> None:
    path = root / "submodules/TelegramUI/Components/TabBarComponent/Sources/TabBarComponent.swift"
    text = path.read_text(encoding="utf-8")
    if "CUE_INKWASH_TAB_PAPER_SELECTION_V1" not in text:
        anchor = "            self.component = component\n            self.state = state\n\n            let iconTintColor ="
        addition = '''            // CUE_INKWASH_TAB_PAPER_SELECTION_V1: a paper seal replaces the stock liquid-glass selection.
            let selectionPaper = component.theme.overallDarkAppearance ? UIColor(rgb: 0x484034) : UIColor(rgb: 0xE9E1D2)
            let selectionEdge = component.theme.overallDarkAppearance ? UIColor(rgb: 0x9C5B52) : UIColor(rgb: 0xB56A60)
            if component.isSelected && !component.isSearchActive {
                self.backgroundColor = selectionPaper
                self.layer.cornerRadius = min(16.0, availableSize.height * 0.45)
                self.layer.borderWidth = 1.0 / UIScreen.main.scale
                self.layer.borderColor = selectionEdge.cgColor
                self.layer.masksToBounds = true
            } else {
                self.backgroundColor = .clear
                self.layer.borderWidth = 0.0
                self.layer.borderColor = UIColor.clear.cgColor
            }

'''
        text = replace_exact(text, anchor, "            self.component = component\n            self.state = state\n\n" + addition + "            let iconTintColor =", "Tab bar ink selection mark")

    if "CUE_INKWASH_TAB_PAPER_SURFACE_V1" not in text:
        anchor = "            self.backgroundContainer.update(size: size, isDark: component.theme.overallDarkAppearance, transition: transition)\n\n            return size"
        addition = '''            self.backgroundContainer.update(size: size, isDark: component.theme.overallDarkAppearance, transition: transition)
            // CUE_INKWASH_TAB_PAPER_SURFACE_V1: solid rice-paper capsule with a quiet raised edge.
            let paper = component.theme.overallDarkAppearance ? UIColor(rgb: 0x292720) : UIColor(rgb: 0xF5F1E7)
            let edge = component.theme.overallDarkAppearance ? UIColor(rgb: 0x4B453A) : UIColor(rgb: 0xD8D0C2)
            self.backgroundContainer.backgroundColor = paper
            self.backgroundContainer.contentView.backgroundColor = paper
            self.backgroundContainer.layer.cornerRadius = size.height * 0.5
            self.backgroundContainer.layer.borderWidth = 1.0 / UIScreen.main.scale
            self.backgroundContainer.layer.borderColor = edge.cgColor
            self.backgroundContainer.layer.shadowColor = UIColor(rgb: 0x342D24).cgColor
            self.backgroundContainer.layer.shadowOpacity = component.theme.overallDarkAppearance ? 0.18 : 0.10
            self.backgroundContainer.layer.shadowRadius = 10.0
            self.backgroundContainer.layer.shadowOffset = CGSize(width: 0.0, height: 3.0)
            self.backgroundContainer.contentView.layer.cornerRadius = size.height * 0.5
            self.backgroundContainer.contentView.layer.masksToBounds = true

            return size'''
        text = replace_exact(text, anchor, addition, "Tab bar paper capsule surface")
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", required=True, type=Path)
    args = parser.parse_args()
    root = args.upstream.resolve()
    actual = subprocess.check_output(["git", "-C", str(root), "rev-parse", "HEAD"], text=True).strip()
    if actual != EXPECTED_SHA:
        raise SystemExit(f"Expected Telegram upstream {EXPECTED_SHA}, found {actual}")

    patch_settings_icon_catalog(root)
    patch_peer_info_cards(root)
    patch_peer_info_section_titles(root)
    patch_settings_spacing(root)
    patch_tab_bar(root)
    print("Applied component-level Chinese ink-wash styling to settings, cards, and root tabs.")


if __name__ == "__main__":
    main()
