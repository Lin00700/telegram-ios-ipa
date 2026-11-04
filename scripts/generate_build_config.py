#!/usr/bin/env python3
"""Write a runner-local Telegram build config. API values stay out of the repo.

TG_API_ID and TG_API_HASH come from the environment (GitHub Actions secrets).
When they are missing and --allow-placeholder is set, compile-only placeholders
are used and a notice file is written. Placeholder values are not a Telegram
login. Real values are never printed.
"""
import argparse
import json
import os
import re
from pathlib import Path

VALID_BUNDLE_ID = re.compile(r"^[A-Za-z0-9]+(?:[.-][A-Za-z0-9]+)+$")
PLACEHOLDER_API_ID = "1"
PLACEHOLDER_API_HASH = "00000000000000000000000000000000"


def fail(message: str) -> None:
    raise SystemExit(f"build-config error: {message}")


def resolve_credentials(allow_placeholder: bool) -> tuple[str, str, str]:
    api_id = os.environ.get("TG_API_ID", "").strip()
    api_hash = os.environ.get("TG_API_HASH", "").strip()
    if api_id and api_hash:
        return api_id, api_hash, "secrets"
    if allow_placeholder:
        return PLACEHOLDER_API_ID, PLACEHOLDER_API_HASH, "placeholder"
    fail("TG_API_ID and TG_API_HASH are missing. Add both as repository Actions secrets. No placeholder was used because --allow-placeholder was not set.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--notice", type=Path)
    parser.add_argument("--allow-placeholder", action="store_true")
    args = parser.parse_args()

    api_id, api_hash, source = resolve_credentials(args.allow_placeholder)
    bundle_id = os.environ.get("APP_BUNDLE_ID", "").strip()
    if not api_id.isdecimal() or api_id == "0":
        fail("TG_API_ID must be a positive decimal integer")
    if len(api_hash) != 32 or any(ch not in "0123456789abcdefABCDEF" for ch in api_hash):
        fail("TG_API_HASH must be a 32-character hexadecimal string")
    if not VALID_BUNDLE_ID.fullmatch(bundle_id):
        fail("APP_BUNDLE_ID must be a reverse-DNS identifier using letters, numbers, dots or hyphens")
    if bundle_id in {"ph.telegra.Telegraph", "org.telegram.Telegram", "org.telegram.TelegramEnterprise"}:
        fail("APP_BUNDLE_ID must not be an official Telegram bundle identifier")
    if not args.template.is_file():
        fail(f"upstream template not found: {args.template}")

    try:
        config = json.loads(args.template.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"could not read upstream configuration template: {exc}")

    config.update({
        "bundle_id": bundle_id,
        "api_id": api_id,
        "api_hash": api_hash,
        "team_id": "0000000000",
        "app_center_id": "0",
        "is_internal_build": "true",
        "is_appstore_build": "false",
        "appstore_id": "0",
        "app_specific_url_scheme": "inktg",
        "premium_iap_product_id": "",
        "enable_siri": False,
        "enable_icloud": False,
    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    os.chmod(args.output, 0o600)

    if source == "placeholder":
        notice = (
            "错误：仓库没有配置 GitHub Actions secrets TG_API_ID 和 TG_API_HASH。\n"
            "本次构建为了验证能否编出 IPA，使用了编译占位符（api_id=1，api_hash 为 32 个 0）。\n"
            "占位符不能登录 Telegram。请到仓库 Settings → Secrets and variables → Actions 添加这两个 secret 后重新运行 workflow。\n"
            "不要把真实的 api_id 或 api_hash 写进代码或提交。\n"
        )
        print("ERROR: TG_API_ID / TG_API_HASH are not configured. Compile-only placeholders were injected. This IPA cannot log in.")
    else:
        notice = "TG_API_ID 和 TG_API_HASH 来自仓库 Actions secrets，已注入构建配置。密钥值没有写入仓库，也没有打印到日志。\n"
        print(f"Temporary unsigned build config created for bundle ID {bundle_id}. Credential source: repository secrets. Values were not printed.")

    if args.notice:
        args.notice.parent.mkdir(parents=True, exist_ok=True)
        args.notice.write_text(notice, encoding="utf-8")


if __name__ == "__main__":
    main()
