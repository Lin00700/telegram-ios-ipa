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
- `features`：在 baseline 上加水墨增强。这个分支的 `BUILD_STAGE` 文件决定 push 触发时用哪一阶段。

## 水墨增强

设置里的「水墨增强」，聊天右上角也能进。默认是宣纸、墨色、朱砂。其它开关默认关闭，长按翻译默认打开。

- 全局背景和当前聊天背景，静态图或 GIF，从相册自选，按比例显示。
- AI：OpenAI、DeepSeek、Gemini、Claude，或自定义 OpenAI 兼容地址。Key 在钥匙串。
- 自动回复：总开关，按对话打开，可对全部新消息、关键词或被 @ 触发，带间隔和次数限制。群、频道、私聊都会走原来的发送权限，发不出去就不会发。
- 长按消息翻译，以及按对话自动翻译新消息。译文附在原文下面。
- 总结当前对话里已经加载的最近文字（打开聊天时通常包含未读窗口）。
- 防撤回：别人撤回或编辑时，本地留下原文并标注。自己删除消息仍然会删掉。
- 隐身：不发已读回执，不上报在线，不发送正在输入。
- 代理入口打开 Telegram 自带的 SOCKS5 / MTProxy 页面。
- 多账号上限从 3 改成 10。服务器对普通账号可能还有自己的限制。

Runner 是 `xcode-27`，Xcode 版本按上游 `versions.json` 选择。一次构建大约要一小时。产物是 `Shuimo-unsigned.ipa`，旁边有 `INSTALL.md`（扩展清单和建议 entitlements）。基线产物已经编出；功能包在 runner 空出来之后再编。

## 上游

默认提交：`fb0e62ba8a147f0821da6aa63c09da7d79a10111`。见 [UPSTREAM.md](UPSTREAM.md)。

官方客户端以 GPL 发布。分发 IPA 时需要同时提供对应的修改版源码，并遵守上游的安全要求：使用自己的 API ID，不要冒充官方，不要使用纸飞机标志。本仓库的图标是另一套图形。
