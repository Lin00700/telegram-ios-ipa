#!/usr/bin/env python3
"""Write the install note that ships next to the unsigned IPA."""
import argparse
import json
from pathlib import Path

OMITTED = [
    ("Share.appex", "分享扩展", "App Group"),
    ("NotificationContent.appex", "通知界面扩展", "App Group"),
    ("NotificationService.appex", "推送解密扩展", "App Group、Push"),
    ("SiriIntents.appex", "Siri 意图扩展", "Siri、App Group"),
    ("Widget.appex", "小组件", "App Group"),
    ("BroadcastUpload.appex", "屏幕广播扩展", "App Group"),
    ("Watch/watchkitapp", "Apple Watch", "独立 bundle 与描述文件"),
]

RECOMMENDED = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>application-identifier</key>
    <string>TEAMID.com.lin.telegram.ink</string>
    <key>com.apple.developer.team-identifier</key>
    <string>TEAMID</string>
    <key>keychain-access-groups</key>
    <array>
        <string>TEAMID.com.lin.telegram.ink</string>
    </array>
</dict>
</plist>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--contents", required=True, type=Path)
    parser.add_argument("--validation", required=True, type=Path)
    parser.add_argument("--notice", required=True, type=Path)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    contents = json.loads(args.contents.read_text(encoding="utf-8"))
    validation = json.loads(args.validation.read_text(encoding="utf-8"))
    notice = args.notice.read_text(encoding="utf-8").strip()
    removed = contents.get("removed_bundles") or []
    lines = [
        "# 未签名 IPA 安装说明",
        "",
        f"- 构建阶段：`{args.stage}`",
        f"- Bundle ID：`{contents.get('bundle_id')}`",
        f"- 显示名称：{contents.get('display_name')}",
        f"- 主程序校验：arm64，已去掉签名和描述文件（sha256 `{validation.get('sha256')}`）",
        f"- IPA 里剩余的扩展：{validation.get('extensions') or '无'}",
        "",
        "## 凭据",
        "",
        notice,
        "",
        "## 重签时建议去掉的扩展",
        "",
        "本机构建传入 `--//Telegram:disableExtensions`，并且打包时会删掉 PlugIns 和 Watch。",
        "上游 Telegram 原本会带上下面这些扩展；它们依赖 App Group 或 Push，个人证书重签后经常装不上或启动即退出。",
        "当前 IPA 不包含它们。主 App 可以聊天；系统分享、通知解密、小组件、Siri、Watch 不可用。",
        "",
        "| 扩展 | 作用 | 需要的额外 entitlement |",
        "| --- | --- | --- |",
    ]
    for name, purpose, entitlement in OMITTED:
        lines.append(f"| `{name}` | {purpose} | {entitlement} |")
    if removed:
        lines.extend(["", "打包时实际删除：", ""])
        for item in removed:
            lines.append(f"- `{item}`")
    lines.extend([
        "",
        "## 主 App 建议的 entitlements",
        "",
        "全能签重签时把 `TEAMID` 换成证书的 Team ID。不要勾选 App Groups，也不要勾选 Push，除非证书里确实有对应能力。",
        "主程序在没有 App Group 容器时会改用自身的 Application Support 目录，避免官方客户端的 “Error 2”。",
        "",
        "```xml",
        RECOMMENDED.strip(),
        "```",
        "",
        "已从主程序 entitlement 中去掉：",
        "",
        "- `com.apple.security.application-groups`",
        "- `aps-environment`",
        "- Siri、iCloud、Associated Domains（非官方 bundle id 本来就不会写入）",
        "",
        "保留并需要与证书一致的是 `application-identifier` 和钥匙串访问组（默认同 bundle id）。",
        "",
    ])
    args.output.write_text("\n".join(lines), encoding="utf-8")
    plist_path = args.output.with_name("recommended.entitlements")
    plist_path.write_text(RECOMMENDED, encoding="utf-8")
    print(f"Wrote {args.output}")


if __name__ == "__main__":
    main()
