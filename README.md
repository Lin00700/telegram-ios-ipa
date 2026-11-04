# 水墨 — 自用 Telegram iOS 客户端

这是官方 [TelegramMessenger/Telegram-iOS](https://github.com/TelegramMessenger/Telegram-iOS) 的构建脚手架，不是官方客户端。仓库里不存放 Telegram 源码；GitHub Actions 在 macOS runner 上拉取固定提交和子模块，编出**未签名 IPA**。用自己的证书（例如全能签）重签后再安装。

默认 bundle id 是 `com.lin.telegram.ink`，主屏幕名称是「水墨」。不要改回 `ph.telegra.Telegraph`。

## 凭据

在仓库 **Settings → Secrets and variables → Actions** 添加：

- `TG_API_ID`
- `TG_API_HASH`

到 [my.telegram.org](https://my.telegram.org) 申请你自己的 API 凭据。不要把真实值写进代码或提交。

secrets 缺失时，workflow 会打出明确错误，并用编译占位符继续编 IPA，用来验证能否编过。占位符**不能登录**。说明写在产物 `credentials-notice.txt` 里。

## 怎么构建

Actions → **Build unsigned IPA** → Run workflow。

- `baseline`：只编上游源码，加上重签兼容（去掉扩展、App Group、Push，主程序可落到自己的沙盒）。
- `features`：在 baseline 上加水墨增强。需要对应脚本已经在这个分支里。

Runner 是 `xcode-27`，Xcode 版本按上游 `versions.json` 选择。一次构建大约要一小时。产物是 `Shuimo-unsigned.ipa`，旁边有 `INSTALL.md`（扩展清单和建议 entitlements）。

## 上游

默认提交：`fb0e62ba8a147f0821da6aa63c09da7d79a10111`。见 [UPSTREAM.md](UPSTREAM.md)。

官方客户端以 GPL 发布。分发 IPA 时需要同时提供对应的修改版源码，并遵守上游的安全要求：使用自己的 API ID，不要冒充官方，不要使用纸飞机标志。本仓库的图标是另一套图形。
