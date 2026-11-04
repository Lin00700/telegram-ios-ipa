#!/usr/bin/env python3
"""Make the main app launch after a personal-certificate re-sign.

Telegram stores its database in an App Group container and shows "Error 2"
when that container is missing. Personal certificates used by 全能签 often
cannot provision App Groups or Push. This patch:

- falls back to the app sandbox when the App Group container is unavailable
- drops the App Group and Push entitlements from the main app

Extensions are disabled separately (--//Telegram:disableExtensions) and are
not part of the IPA. Official Telegram behavior is unchanged when the App
Group exists and the feature flags added later are left off.
"""
import argparse
from pathlib import Path

MARKER = "INK_RESIGN_APP_GROUP_FALLBACK"

APP_GROUP_GUARD = """        guard let appGroupUrl = maybeAppGroupUrl else {
            self.mainWindow?.presentNative(UIAlertController(title: nil, message: "Error 2", preferredStyle: .alert))
            return true
        }
"""

APP_GROUP_FALLBACK = """        let inkSandboxURL = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        let appGroupUrl = maybeAppGroupUrl ?? inkSandboxURL
        // INK_RESIGN_APP_GROUP_FALLBACK: personal certificates often have no App Group.
"""

APP_GROUPS_FRAGMENT = (
    'app_groups_fragment = """\n'
    "    <key>com.apple.security.application-groups</key>\n"
    "    <array>\n"
    "        <string>group.{telegram_bundle_id}</string>\n"
    "    </array>\n"
    "    <key>application-identifier</key>\n"
    "    <string>{telegram_team_id}.{telegram_bundle_id}</string>\n"
    '""".format(\n'
)

APP_GROUPS_REPLACEMENT = (
    'app_groups_fragment = """\n'
    "    <key>application-identifier</key>\n"
    "    <string>{telegram_team_id}.{telegram_bundle_id}</string>\n"
    '""".format(\n'
)

APS_LINE = 'aps_fragment = "" if telegram_aps_environment == "" else """'
APS_REPLACEMENT = 'aps_fragment = "" if True else """  # INK_RESIGN_NO_PUSH'


def replace_exact(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{label}: expected 1 match, found {count}")
    return text.replace(old, new, 1)


def patch_app_delegate(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    text = replace_exact(text, APP_GROUP_GUARD, APP_GROUP_FALLBACK, "AppDelegate app group guard")
    path.write_text(text, encoding="utf-8")


def patch_entitlements(path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    if "INK_RESIGN_NO_PUSH" not in text:
        text = replace_exact(text, APS_LINE, APS_REPLACEMENT, "push entitlement")
    if APP_GROUPS_FRAGMENT in text:
        text = replace_exact(text, APP_GROUPS_FRAGMENT, APP_GROUPS_REPLACEMENT, "main app group entitlement")
    elif "INK_RESIGN_APP_GROUP_FALLBACK" not in text and "<key>com.apple.security.application-groups</key>" in text.split('name = "ShareExtensionEntitlements"', 1)[0]:
        raise SystemExit("main app group entitlement fragment was not found")
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", required=True, type=Path)
    args = parser.parse_args()
    root = args.upstream
    delegate = root / "submodules/TelegramUI/Sources/AppDelegate.swift"
    build = root / "Telegram/BUILD"
    if not delegate.is_file() or not build.is_file():
        raise SystemExit("upstream checkout is missing AppDelegate.swift or Telegram/BUILD")
    patch_app_delegate(delegate)
    patch_entitlements(build)
    print("Resign compatibility applied: sandbox fallback, no main-app App Group, no push entitlement.")


if __name__ == "__main__":
    main()
