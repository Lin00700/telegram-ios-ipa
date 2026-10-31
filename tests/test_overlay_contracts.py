"""Static contract tests for the Telegram-iOS overlay.

These run on Linux (no Xcode/Bazel) and pin the invariants the overlay must keep:
per-chat opt-in, fail-closed AI/translation gating, no entitlement bypass,
local-only wallpaper/translation, iOS 15.5 floor. They match the *actual* patch
strings in scripts/ and runtime/, so a rename in either place fails here first.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8")


class AIAutoReplyContract(unittest.TestCase):
    def test_defaults_are_off_and_consent_coupled(self):
        prefs = read("runtime/CueFeaturePreferences.swift")
        self.assertIn("autoReplyEnabled: Bool = false", prefs)
        self.assertIn("outboundConsentAccepted: Bool = false", prefs)
        self.assertIn("self.autoReplyEnabled = autoReplyEnabled && outboundConsentAccepted", prefs)
        # missing/corrupt stored value falls back to the all-off default
        self.assertIn("return CueAIChatOptions()", prefs)

    def test_state_is_keyed_per_conversation(self):
        prefs = read("runtime/CueFeaturePreferences.swift")
        self.assertIn("accountId: Int64, peerId: Int64, threadId: Int64?", prefs)
        self.assertNotIn("globalAutoReply", prefs)

    def test_send_path_rechecks_before_and_after_generation(self):
        src = read("scripts/apply_runtime_features.py")
        start = src.index("private func cueStartAIReply")
        body = src[start:src.index("private func cueHandleNewIncomingMessage", start)]
        self.assertEqual(body.count("options.autoReplyEnabled") + body.count("currentOptions.autoReplyEnabled"), 2)
        self.assertEqual(body.count("outboundConsentAccepted"), 2)
        self.assertEqual(body.count("canSendMessages()"), 2)
        self.assertIn("!options.assignedProfileIDs.isEmpty", body)
        self.assertIn("CueAIReplyStore.shared.claim(key)", body)

    def test_bots_and_broadcast_channels_are_skipped(self):
        src = read("scripts/apply_runtime_features.py")
        self.assertIn("guard !isBroadcast else", src)
        self.assertIn("author.botInfo != nil", src)

    def test_provider_requires_https_and_keychain(self):
        svc = read("runtime/CueAIReplyService.swift")
        prefs = read("runtime/CueFeaturePreferences.swift")
        self.assertIn("CueFeaturePreferences.isSecureHTTPS(profile.endpoint)", svc)
        self.assertIn('components.scheme?.lowercased() == "https"', svc)
        self.assertIn("URLSessionConfiguration.ephemeral", svc)
        self.assertIn("kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly", prefs)
        self.assertNotRegex(prefs, r"defaults\.set\([^)]*apiKey")

    def test_profiles_never_embed_the_key(self):
        prefs = read("runtime/CueFeaturePreferences.swift")
        block = prefs[prefs.index("public struct CueAIProfile"):prefs.index("public struct CueAIChatOptions")]
        self.assertNotIn("apiKey", block)

    def test_provider_manager_is_global_and_does_not_auto_assign_or_enable(self):
        ui = read("runtime/CueFeatureSettingsUI.swift")
        self.assertIn('title: "管理 AI 服务商…"', ui)
        self.assertIn('title: "添加 AI 服务商…"', ui)
        self.assertIn("assignToChat: false", ui)
        self.assertIn("if assignToChat {", ui)
        self.assertIn('title: "分配本聊天的 AI 服务商…"', ui)
        self.assertIn('aiOptions.autoReplyEnabled ? "关闭本聊天 AI 自动回复" : "开启本聊天 AI 自动回复"', ui)
        self.assertIn("Keychain", ui)


class TranslationContract(unittest.TestCase):
    def test_translation_is_gated_by_switch_and_consent_everywhere(self):
        src = read("scripts/apply_runtime_features.py")
        enabled = src.count("CueFeaturePreferences.isAutoTranslationEnabled(")
        consent = src.count("CueFeaturePreferences.hasTranslationConsent(")
        self.assertGreaterEqual(enabled, 3)
        self.assertEqual(enabled, consent)

    def test_translation_defaults_off(self):
        prefs = read("runtime/CueFeaturePreferences.swift")
        self.assertIn('defaults.bool(forKey: conversationKey("translation.enabled"', prefs)  # unset -> false

    def test_translation_is_on_device_only(self):
        for rel in ("runtime/CueLocalTranslation.swift", "runtime/CueOpenCCT2S.swift"):
            text = read(rel)
            self.assertNotIn("URLSession", text, rel)
            self.assertNotIn("CueAIReply", text, rel)
        self.assertIn("import MLKitTranslate", read("runtime/CueLocalTranslation.swift"))

    def test_translation_not_coupled_to_ai(self):
        prefs = read("runtime/CueFeaturePreferences.swift")
        for name in ("translation.enabled", "translation.consent", "ai-chat.options"):
            self.assertIn(name, prefs)


class MonetizationAndEntitlementContract(unittest.TestCase):
    def test_only_ui_gates_are_changed(self):
        src = read("scripts/apply_custom_client_ui.py")
        self.assertIn("isPremiumDisabled: true,", src)
        self.assertIn("areStarsDisabled: true,", src)
        self.assertIn("CUE_REMOVE_MONETIZATION_ENTRIES_V1", src)
        self.assertIn("CUE_HIDE_PAID_SETTINGS_SEARCH_V1", src)
        self.assertIn("CUE_DISABLE_STOREKIT_PURCHASES_V1", src)
        # never force a premium/entitlement state
        self.assertNotRegex(src, r"\bisPremium\s*[:=]\s*true")
        self.assertNotIn("premiumGracePeriod = ", src)

    def test_patches_fail_closed_on_upstream_drift(self):
        for rel in ("scripts/apply_custom_client_ui.py", "scripts/apply_global_wallpaper.py", "scripts/apply_runtime_features.py"):
            text = read(rel)
            self.assertIn("raise RuntimeError", text, rel)


class WallpaperContract(unittest.TestCase):
    def test_wallpaper_is_local_aspect_fit_and_dimmed_in_dark(self):
        src = read("scripts/apply_global_wallpaper.py")
        self.assertIn(".applicationSupportDirectory", src)
        self.assertIn("contentMode = .scaleAspectFit", src)
        self.assertIn("isUserInteractionEnabled = false", src)
        self.assertIn("dimAlpha = 0.46", src)
        self.assertIn("data.count <= 32 * 1024 * 1024", src)
        self.assertIn("let maximumFrames = 16", src)
        self.assertNotIn("URLSession", src)

    def test_bundled_ink_wash_asset_exists(self):
        self.assertTrue((ROOT / "assets/cf-inkwash-global.png").is_file())
        self.assertIn("ChatWallpaperBuiltin0.png", read("scripts/build_from_upstream.sh"))

    def test_photo_gif_picker_is_local_and_reachable(self):
        picker = read("runtime/CueGlobalWallpaperPicker.swift")
        ui = read("runtime/CueFeatureSettingsUI.swift")
        self.assertIn("PHPickerViewController", picker)
        self.assertIn('"CueGlobalWallpaperPath"', picker)
        self.assertIn('"CueGlobalWallpaperChanged"', picker)
        self.assertIn('title: "设置全局图片/GIF聊天背景…"', ui)
        self.assertIn('title: "恢复默认水墨聊天背景"', ui)
        self.assertNotIn("URLSession", picker)


class BuildContract(unittest.TestCase):
    def test_upstream_pin_is_consistent(self):
        sha = re.search(r'EXPECTED_SHA = "([0-9a-f]{40})"', read("scripts/apply_custom_client_ui.py")).group(1)
        self.assertIn(sha, read(".github/workflows/build-unsigned-ipa.yml"))
        self.assertIn(sha, read("UPSTREAM.md") + read("README.md"))

    def test_min_ios_is_15_5_and_unsigned(self):
        build = read("scripts/build_from_upstream.sh")
        self.assertIn('--minimum-ios-version "15.5"', build)
        self.assertIn("--disableProvisioningProfiles", build)
        self.assertIn("apply_inkwash_theme.py", build)

    def test_full_inkwash_theme_targets_shared_and_live_message_variants(self):
        theme = read("scripts/apply_inkwash_theme.py")
        self.assertIn("CUE_CF_INKWASH_THEME_V2", theme)
        self.assertIn("CUE_CF_DARK_INKWASH_THEME_V2", theme)
        self.assertIn('"    let messageDay = PresentationThemeChatMessage("', theme)
        self.assertIn('"    let actionSheet = PresentationThemeActionSheet("', theme)

    def test_every_runtime_file_is_installed(self):
        installer = read("scripts/apply_runtime_features.py")
        for path in (ROOT / "runtime").glob("*.swift"):
            self.assertIn(path.name, installer, f"{path.name} not copied into the upstream tree")

    def test_secrets_not_in_repo_files(self):
        for rel in (".github/workflows/build-unsigned-ipa.yml", "scripts/build_from_upstream.sh"):
            text = read(rel)
            self.assertNotRegex(text, r"api_hash\s*[:=]\s*[\"']?[0-9a-f]{32}")


if __name__ == "__main__":
    unittest.main()
