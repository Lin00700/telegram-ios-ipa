"""Config injection and resign-compatibility patches. No real API secrets."""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


config = load("generate_build_config")
resign = load("apply_resign_compat")
branding = load("apply_branding")


class BuildConfigTests(unittest.TestCase):
    def write_template(self, directory: Path) -> Path:
        path = directory / "template.json"
        path.write_text("{}\n", encoding="utf-8")
        return path

    def test_missing_secrets_use_placeholders_and_do_not_print_them_as_success(self):
        env = os.environ.copy()
        env.pop("TG_API_ID", None)
        env.pop("TG_API_HASH", None)
        env["APP_BUNDLE_ID"] = "com.lin.telegram.ink"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "config.json"
            notice = root / "notice.txt"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "generate_build_config.py"),
                    "--template",
                    str(self.write_template(root)),
                    "--output",
                    str(output),
                    "--notice",
                    str(notice),
                    "--allow-placeholder",
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("placeholders", completed.stdout)
            payload = json.loads(output.read_text(encoding="utf-8"))
            self.assertEqual(payload["api_id"], config.PLACEHOLDER_API_ID)
            self.assertEqual(payload["api_hash"], config.PLACEHOLDER_API_HASH)
            self.assertEqual(payload["bundle_id"], "com.lin.telegram.ink")
            self.assertNotIn(config.PLACEHOLDER_API_HASH, completed.stdout)
            self.assertIn("TG_API_ID", notice.read_text(encoding="utf-8"))

    def test_missing_secrets_fail_without_placeholder_flag(self):
        env = os.environ.copy()
        env.pop("TG_API_ID", None)
        env.pop("TG_API_HASH", None)
        env["APP_BUNDLE_ID"] = "com.lin.telegram.ink"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "generate_build_config.py"),
                    "--template",
                    str(self.write_template(root)),
                    "--output",
                    str(root / "config.json"),
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("TG_API_ID", completed.stderr)

    def test_official_bundle_id_is_rejected(self):
        env = os.environ.copy()
        env["TG_API_ID"] = "100"
        env["TG_API_HASH"] = "0123456789abcdef0123456789abcdef"
        env["APP_BUNDLE_ID"] = "ph.telegra.Telegraph"
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            completed = subprocess.run(
                [
                    sys.executable,
                    str(ROOT / "scripts" / "generate_build_config.py"),
                    "--template",
                    str(self.write_template(root)),
                    "--output",
                    str(root / "config.json"),
                ],
                env=env,
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertNotIn("0123456789abcdef0123456789abcdef", completed.stdout)
            self.assertNotIn("0123456789abcdef0123456789abcdef", completed.stderr)


class ResignCompatTests(unittest.TestCase):
    def test_patches_delegate_and_entitlements(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            delegate = root / "submodules/TelegramUI/Sources/AppDelegate.swift"
            build = root / "Telegram/BUILD"
            delegate.parent.mkdir(parents=True)
            build.parent.mkdir(parents=True)
            delegate.write_text("prefix\n" + resign.APP_GROUP_GUARD + "suffix\n", encoding="utf-8")
            build.write_text(
                resign.APS_LINE + "\n<key>aps-environment</key>\n"
                + resign.APP_GROUPS_FRAGMENT
                + "name = \"ShareExtensionEntitlements\"\n",
                encoding="utf-8",
            )
            resign.patch_app_delegate(delegate)
            resign.patch_entitlements(build)
            delegate_text = delegate.read_text(encoding="utf-8")
            build_text = build.read_text(encoding="utf-8")
            self.assertIn("inkSandboxURL", delegate_text)
            self.assertNotIn("Error 2", delegate_text)
            self.assertIn("INK_RESIGN_NO_PUSH", build_text)
            self.assertNotIn("com.apple.security.application-groups", build_text)
            self.assertIn("application-identifier", build_text)

    def test_chinese_display_name_matches_packager(self):
        self.assertTrue(branding.SAFE_NAME.fullmatch("水墨"))
        self.assertTrue(branding.SAFE_NAME.fullmatch("非官方聊天"))
        self.assertFalse(branding.SAFE_NAME.fullmatch("Chat😀"))


class FeatureStageTests(unittest.TestCase):
    def test_feature_stage_wires_the_same_hooks(self):
        stage = (ROOT / "BUILD_STAGE").read_text(encoding="utf-8").strip()
        self.assertEqual(stage, "features")
        script = (ROOT / "scripts" / "apply_features.sh").read_text(encoding="utf-8")
        for name in ("apply_inkwash_theme.py", "apply_inkwash_components.py", "apply_global_wallpaper.py", "apply_ink_features.py", "ChatWallpaperBuiltin0.png"):
            self.assertIn(name, script)
        ink = (ROOT / "scripts" / "apply_ink_features.py").read_text(encoding="utf-8")
        prefs = (ROOT / "ink" / "Sources" / "InkPreferences.swift").read_text(encoding="utf-8")
        retain = (ROOT / "ink" / "upstream" / "InkRetainDeletedMessages.swift").read_text(encoding="utf-8")
        for key in ("ink.stealth.hideOnline", "ink.stealth.hideTyping", "ink.stealth.hideRead"):
            self.assertIn(key, ink)
            self.assertIn(key, prefs)
        self.assertIn("ink.antiRecall.enabled", prefs)
        self.assertIn("ink.antiRecall.enabled", retain)
        self.assertIn("maximumNumberOfAccounts = 10", ink)
        self.assertIn("InkAutoReplyPolicy.shouldReply", ink)
        self.assertIn("case .mention", (ROOT / "ink" / "Sources" / "InkPolicy.swift").read_text(encoding="utf-8"))


class UnsignedFlagTests(unittest.TestCase):
    def test_extensions_are_disabled_with_signing(self):
        text = (ROOT / "scripts" / "enable_unsigned_device_build.py").read_text(encoding="utf-8")
        self.assertIn("'--//Telegram:disableExtensions'", text)
        self.assertIn("'--features=disable_legacy_signing'", text)
        workflow = (ROOT / ".github/workflows" / "build-unsigned-ipa.yml").read_text(encoding="utf-8")
        self.assertIn("secrets.TG_API_ID", workflow)
        self.assertIn("secrets.TG_API_HASH", workflow)
        self.assertNotIn("fb0e62ba8a147f0821da6aa63c09da7d79a10111\"\n          api_hash", workflow)
        self.assertIn("com.lin.telegram.ink", workflow)


if __name__ == "__main__":
    unittest.main()
