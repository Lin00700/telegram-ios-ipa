import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parent

TOGGLES = [
    "smsEnabled",
    "blockForeignSMS",
    "provinceFilterEnabled",
    "onlyGuangdongSMS",
    "blockVirtualSMS",
    "keywordFilterEnabled",
    "whitelistKeywordsEnabled",
    "whitelistSendersEnabled",
    "routeTransaction",
    "routePromotion",
    "callBlockingEnabled",
    "segmentBlockEnabled",
    "expandVirtualSegments",
    "contactsOnlyGuidanceEnabled",
]


class ContractTests(unittest.TestCase):
    def test_feature_toggles_default_off(self):
        source = (ROOT / "Shared" / "FilterRules.swift").read_text(encoding="utf-8")
        for name in TOGGLES:
            self.assertIn(f"var {name}: Bool = false", source)

    def test_extensions_stay_local_and_read_only(self):
        message = (ROOT / "MessageFilter" / "MessageFilterExtension.swift").read_text(encoding="utf-8")
        call = (ROOT / "CallDirectory" / "CallDirectoryHandler.swift").read_text(encoding="utf-8")
        shared = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "Shared").glob("*.swift"))
        app = "\n".join(path.read_text(encoding="utf-8") for path in (ROOT / "CallSMSBlocker").rglob("*.swift"))
        for banned in ("deferQueryRequestToNetwork", "URLSession", "LiveCallerID", "NEHotspot", "PIRService"):
            self.assertNotIn(banned, message)
            self.assertNotIn(banned, call)
            self.assertNotIn(banned, shared)
        self.assertNotIn("write(to:", message)
        self.assertNotIn("write(to:", call)
        self.assertIn("静音未知来电", app)
        self.assertIn("只接通讯录来电", app)
        self.assertIn("App-Prefs:root=Phone", app)
        self.assertIn("不能识破伪造的来电显示", app)

    def test_extension_points_and_app_group(self):
        message = (ROOT / "MessageFilter" / "Info.plist").read_text(encoding="utf-8")
        call = (ROOT / "CallDirectory" / "Info.plist").read_text(encoding="utf-8")
        self.assertIn("com.apple.identitylookup.message-filter", message)
        self.assertNotIn("ILMessageFilterExtensionNetworkURL", message)
        self.assertIn("com.apple.callkit.call-directory", call)
        for relative in (
            "CallSMSBlocker/CallSMSBlocker.entitlements",
            "MessageFilter/MessageFilter.entitlements",
            "CallDirectory/CallDirectory.entitlements",
        ):
            text = (ROOT / relative).read_text(encoding="utf-8")
            self.assertIn("com.apple.security.application-groups", text)
            self.assertIn("$(APP_GROUP_ID)", text)

    def test_workflow_publishes_unsigned_artifacts(self):
        workflow = (REPO / ".github" / "workflows" / "build-callsms-ipa.yml").read_text(encoding="utf-8")
        self.assertIn("runs-on: xcode-27", workflow)
        self.assertIn("CallSMSBlocker-unsigned.ipa", workflow)
        self.assertIn("INSTALL.md", workflow)
        self.assertIn(".sha256", workflow)
        self.assertIn("actions/upload-artifact@v4", workflow)
        self.assertNotIn("live-caller-id", workflow)
        original = (REPO / ".github" / "workflows" / "build-unsigned-ipa.yml").read_text(encoding="utf-8")
        self.assertIn("runs-on: xcode-27", original)
        self.assertNotIn("callsms-blocker", original)


if __name__ == "__main__":
    unittest.main()
