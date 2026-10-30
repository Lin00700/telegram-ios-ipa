# 所选会话自动翻译到简体中文

## 目标体验

- 用户可以在会话列表中多选私聊、群组或频道，为所选会话分别启用“自动翻译入站消息”。
- 翻译是每个会话、每个论坛主题独立的开关，默认关闭；不得因为选择会话、选择 AI 助手或开启 AI 自动回复而自动开启翻译。
- 目标语言默认是简体中文（`zh-Hans`）。只处理收到的文字消息，不翻译用户自己发出的消息；暂不自动上传图片、语音、文件等媒体。
- 原文始终保留并与简体中文译文同时显示，建议在原消息下方加入清楚标注的“简体中文译文”。不能用译文覆盖原文，也不能把“显示原文”的切换按钮当作满足双语并列需求。
- 翻译开关、翻译服务选择和翻译同意，与该会话的 AI 自动回复开关、AI 助手分配及自动回复同意完全分离；切换其中一项不得更改另一项。

## 固定上游版本已有的翻译能力

本项目固定的 Telegram iOS 上游版本 `fb0e62ba8a147f0821da6aa63c09da7d79a10111` 已包含单条消息翻译、翻译设置、整聊翻译面板和翻译状态缓存。相关实现包括：[`Translate.swift`](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TelegramCore/Sources/TelegramEngine/Messages/Translate.swift)、[`ChatTranslation.swift`](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TranslateUI/Sources/ChatTranslation.swift)、[`ChatTranslationPanelNode.swift`](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TelegramUI/Components/TranslateHeaderPanelComponent/Sources/ChatTranslationPanelNode.swift) 和 [`AutoTranslate.swift`](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TelegramCore/Sources/TelegramEngine/Peers/AutoTranslate.swift)。翻译缓存以 `peerId` 及可选 `threadId` 为键，目标语言可跟随界面语言。

Telegram 官方说明，用户可从设置中的“语言”开启单条消息翻译，并在消息菜单中选择“翻译”；此功能在 iOS 需要 iOS 15 或更新版本。Telegram 的整聊实时翻译适用条件不同：个人/群组整聊翻译受 Premium 限制；频道由频道侧启用自动翻译后，用户才可使用相应频道翻译。客户端必须遵守上游的 Premium 与频道能力检查，不得绕过订阅或修改频道权限。

**原生界面当前不能满足本项目的“双语同时显示”要求。** 上游翻译栏在已翻译时显示“显示原文”操作，官方频道说明也称可通过翻译栏切回原文；这属于原文/译文切换，而非两者同时展示。因此需要为消息气泡增加译文副行，并在真实 iOS 构建中验证，不得仅凭源码控件存在就宣称定制版已实现。

## 翻译服务与隐私

### Telegram 原生翻译

优先复用 Telegram 已有翻译流程与服务端功能，保持账号原有 Premium/频道条件。上游引擎调用 Telegram 的 `messages.translateText` 翻译接口；开启前应明确告知：选中的消息文本会发给 Telegram 服务处理。用户仍须逐会话主动开启；关闭后停止后续翻译请求。

### 用户配置的 AI/provider 翻译

如用户为不支持 Telegram 原生自动翻译的会话选择自有 provider，则必须在该会话内单独展示数据外发说明，至少列明 provider、模型、endpoint、发送的消息文本及可能的数据保留/使用方式，并取得明确同意后才可发送第一条内容。优先复用已保存的一个 provider profile 作为该会话的翻译器，但不得把它自动绑定为 AI 回复助手，也不得将消息发送给所有已分配的 AI 助手。provider 凭据只可运行时录入并存入 iOS Keychain，不能放入源码、构建配置、日志或 GitHub Secrets。

撤回翻译同意或关闭该会话翻译后，立即停止后续 provider 请求。翻译同意不包含 AI 自动回复同意；AI 自动回复同意也不包含翻译同意。每个会话、每个主题分别保存两类状态。

## 中文界面与样式

新增设置、操作和状态文案必须提供简体中文 `zh-Hans` 文案；例如“自动翻译”“目标语言”“简体中文”“原文”“翻译来源”“数据共享说明”“撤回同意”。目标语言默认简体中文，但不得在没有用户选择时打开任何会话的翻译开关。译文在原文下方显示，使用次级文字色与轻分隔，让用户能一眼区分原文、译文和发送者；沿用暖象牙白背景、砖红状态点和圆角交互。

## 频道与群组规则

- 群组或论坛主题只处理用户明确开启的会话/主题，状态按 `peerId + threadId` 区分；不得因多选自动打开全部。
- 原生频道自动翻译只在 Telegram 返回频道已启用相应能力时提供；只有具备频道管理权限时才可展示/调用修改频道侧设置的入口。
- 第三方 provider 对频道可见消息的翻译同样需要该频道的逐会话数据外发同意，但不得发送或修改频道内容。
- 翻译失败、受限或离线时保留原文并显示轻量错误/重试状态，不丢消息、不自动切换到其他 provider，也不把原文写入日志。

## 完成前验证

1. 未显式开启时，各私聊、群组、频道及论坛主题均不自动翻译；多选只配置指定对象。
2. 译文目标为 `zh-Hans`，原文与译文在同一消息记录中同时可见；翻译失败仍保留原文。
3. 翻译开关与 AI 自动回复开关、分配的助手和各自同意状态互不影响。
4. 原生整聊翻译遵守 Telegram Premium 与频道启用条件；单条消息菜单仍可用。
5. 第三方 provider 在逐会话同意前零网络请求；同意文案准确列出 provider/model/endpoint；撤回后不再请求。
6. 新增控件显示简体中文且无障碍标签可读；正常消息发送、搜索、附件、通知和主题功能不回归。

## 实施状态

固定上游已有原生翻译接口和翻译栏，但定制版的简体中文 UI、原文+译文同时显示、独立逐会话自动翻译开关及第三方 provider 授权流程尚未集成或通过 iOS 构建验证。GitHub Actions workflow/secrets 权限仍待用户在 Cue 中重新授权；在此之前没有可验证的 IPA。

## 来源

- [Telegram：消息翻译（2021-12-30）](https://telegram.org/blog/reactions-spoilers-translations?setln=en)
- [Telegram：整聊翻译与频道翻译（2023-02-03）](https://telegram.org/blog/profile-pics-emoji-translations)
- [Telegram：Premium 整聊翻译与频道自动翻译（2025-05-08）](https://telegram.org/blog/gift-marketplace-and-more)
- [固定上游：ChatTranslationPanelNode.swift](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TelegramUI/Components/TranslateHeaderPanelComponent/Sources/ChatTranslationPanelNode.swift)
- [固定上游：ChatTranslation.swift](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TranslateUI/Sources/ChatTranslation.swift)
- [固定上游：AutoTranslate.swift](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TelegramCore/Sources/TelegramEngine/Peers/AutoTranslate.swift)
- [固定上游：Translate.swift](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TelegramCore/Sources/TelegramEngine/Messages/Translate.swift)
