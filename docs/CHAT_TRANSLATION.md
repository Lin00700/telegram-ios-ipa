# 所选会话自动翻译到简体中文（与 AI 自动回复分开）

## 目标体验

- 用户可多选私聊、群组或频道，并给指定会话分配多个 AI 助手 profile；保留一次选择多个会话、多个 AI 助手并进行批量分配的既定能力。
- 自动翻译只处理用户可见的入站文字消息，目标为简体中文；原文完整保留，译文显示在原消息下方并明确标注。翻译不覆盖原文、不发送新消息，也不自动上传图片、语音或文件。
- 每个会话、每个论坛主题有独立的“自动翻译”开关，默认关闭。选择会话、分配 AI 助手或打开 AI 自动回复，都不能自动打开翻译。
- 翻译开关、翻译服务、翻译同意，与 AI 自动回复开关、助手分配及回复同意分别保存、分别管理。开启翻译永远不代表授权 AI 回复；开启 AI 回复也永远不代表授权翻译外发。

## Google 翻译方案调查

### 设备端优先选项：Google ML Kit Translation

Google ML Kit 在设备端完成翻译，聊天文本无需发送到远端服务器；语言模型按需下载，官方 iOS 文档称模型约 30 MB，首次下载需要联网，下载后可离线使用。模型下载不包含聊天正文。它没有 Cloud Translation API key 或按字符调用云端翻译的要求，隐私上更合适。Google 同时提醒该功能面向日常、简单翻译；质量依语言而异，非英语互译会经英语中转，应以真实聊天语料评估。

但 ML Kit 的官方翻译语言表只列通用中文代码 `zh`，没有明确的 `zh-Hans` / `zh-CN` 目标选项，也没有文档保证输出一定为简体字。因此不能在未验证输出前承诺其满足简体中文要求。iOS 集成文档示例使用 CocoaPods（`GoogleMLKit/Translate`）；Telegram iOS 上游通过 Make.py/Bazel 构建，未找到 Google 官方 Bazel 接入说明。理论上可将 Pod 的二进制框架及其传递依赖/资源封装成 Bazel targets，但这不是即插即用的官方集成，尚未在此项目中实现或验证。

### 精确语言选项：Google Cloud Translation API

Google Cloud Translation 的常规语言列表把简体中文列为 `zh-CN`（或 `zh`）；`zh-Hans` 则出现在其 Translation LLM 支持列表。若使用标准 Cloud Translation API，应显式设置 `zh-CN`，而不是假定所有模型都接受 `zh-Hans`。它通过云端服务翻译，消息文本会离开设备并发送给 Google；须在每个会话单独清楚告知并取得同意。把 REST API 用现有 iOS 网络层调用，通常比把 ML Kit 的 CocoaPods 二进制/资源接入 Telegram 的 Bazel 构建更直接，但需加入凭据配置和错误/用量处理。

使用 Cloud Translation 前，用户需要一个 Google Cloud 项目、启用 Cloud Translation API、项目关联启用结算的 billing account，并设置 API 认证。费用依使用量；本项目不能代用户启用结算或默认发出云端请求。选定 Cloud API 后，凭据只能由用户在应用运行时配置并安全保存（Keychain 或用户自有的服务端代理），不可放进源码、仓库或 GitHub Actions secrets。仅在相关会话同意后发送消息文本。

**待确认的取舍：**若优先隐私并可接受先验证通用 `zh` 是否输出简体，可走 ML Kit，但需要额外解决 Bazel 接入；若必须显式指定简体，标准 Cloud Translation 更合适，目标代码为 `zh-CN`，但需要用户自有 Cloud 项目、结算和认证，并把会话文本发给 Google。现在未配置 ML Kit，也未创建 Cloud 资源、启用计费或收集 Cloud 凭据。

## 翻译和 AI 自动回复独立

每个会话分别保存两类配置，不能共用同一开关或同一授权：

```text
ConversationTranslationSettings (accountId + peerId + optional threadId)
  autoTranslateIncoming: false
  targetLanguage: "zh-CN"     // 用户界面仍可用 zh-Hans；ML Kit 仅有 zh
  translationProvider: none    // 未选择服务时不发请求
  consentVersion: none
  displayMode: originalAndTranslation

ConversationAISettings (accountId + peerId + optional threadId)
  assignedAssistantIds: []     // 可多选
  autoReplyEnabled: false
  consentedProviderIds: []
```

翻译 profile 与回复助手 profile 可以选择相同服务，但“已分配”不等于“已同意翻译数据外发”。如使用 Cloud Translation，翻译同意须列出 Google、目标代码 `zh-CN`、发送的消息文本与数据处理方式；若改用任一 AI provider，也须列出 provider、模型、endpoint 及其数据处理方式。更换服务/模型/endpoint 后重新同意，撤回后立即停止后续翻译请求。

每条新消息只发送最少内容：当前一条入站文字、源语言（如有）和目标语言；默认不附带聊天历史、用户名或其他上下文。消息 ID 去重并做速率限制。译文只作为本地显示文本，不执行其中的指令；失败时保留原文、显示轻量状态，不自动切换服务、不记录消息正文。

## Telegram 原生翻译与频道规则

固定上游 `fb0e62ba8a147f0821da6aa63c09da7d79a10111` 已包含单条消息翻译、整聊翻译面板和翻译状态缓存，相关源码为 [`Translate.swift`](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TelegramCore/Sources/TelegramEngine/Messages/Translate.swift)、[`ChatTranslation.swift`](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TranslateUI/Sources/ChatTranslation.swift)、[`ChatTranslationPanelNode.swift`](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TelegramUI/Components/TranslateHeaderPanelComponent/Sources/ChatTranslationPanelNode.swift) 和 [`AutoTranslate.swift`](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TelegramCore/Sources/TelegramEngine/Peers/AutoTranslate.swift)。Telegram 原生整聊翻译有 Premium/频道能力条件；此处不修改或绕过 Telegram 原生状态。方案由用户另行选择 Google 翻译服务，并按本地会话权限显示译文。

频道只处理当前账号有权查看、且符合频道翻译能力/限制的消息；不得调用 Telegram 的频道自动翻译设置接口，不得修改频道设置、消息、反应或评论，也不得代发内容。第三方/Cloud 服务仍须另行取得逐频道数据外发同意。频道未允许该类翻译或当前账号没有查看权限时，隐藏/禁用该频道自动翻译入口。群组/论坛主题按 `peerId + threadId` 独立设置；未选中的聊天绝不外发。

## 简体中文界面与双语显示

新增控件提供简体中文（`zh-Hans`）文案，例如“自动翻译”“目标语言”“原文”“简体中文译文”“翻译来源”“数据共享说明”“撤回同意”。默认目标为简体中文，但各会话的开关默认关闭。译文位于原文下方，用次级文字色与轻分隔标识，并沿用暖象牙白、砖红状态点和圆角交互。

**上游原生翻译栏是“译文/显示原文”切换，无法满足原文与译文同时显示。** 定制版仍需为消息气泡增加译文副行，并在真实 iOS 构建中验证。

## 完成前验证

1. 每个会话/主题初始关闭；批量选择只配置指定对象，不隐式开启翻译。
2. 翻译与 AI 自动回复开关、profile 分配和各自同意互不影响。
3. 原文与简体中文译文同时显示；失败/离线时仍保留原文。
4. 未选 provider、未逐会话同意、授权已撤回或权限不足时，网络请求为零。
5. ML Kit 分支需确认 `zh` 实际输出简体、模型下载/删除和离线行为，并完成 Bazel 依赖与资源打包验证；标准 Google Cloud Translation 分支使用 `zh-CN` 并核实认证限制及费用告知。
6. API key 只在运行时保存到 Keychain/用户代理，不进入仓库/GitHub；日志不含消息文本或 key。
7. 频道权限和翻译能力受限时不开启；客户端不发送或修改频道消息/设置。
8. 新增控件为简体中文且可访问；消息、搜索、附件、通知和主题功能不回归。

## 实施状态

已确定翻译必须与 AI 自动回复彻底分开，但 Google 服务实现仍待选择 ML Kit 或 Cloud Translation。ML Kit 可保护聊天文本留在本地，但只公开通用 `zh` 且需要非即插即用的 Bazel 集成；标准 Cloud Translation 使用简体中文代码 `zh-CN`（其 Translation LLM 列表另列 `zh-Hans`），但需要项目/API/结算/认证并把文本发到 Google。两种均尚未集成或通过构建验证；GitHub Actions workflow/secrets 写权限也仍待恢复，目前没有 IPA。

## 来源

- [ML Kit Translation（设备端处理、模型与质量边界）](https://developers.google.com/ml-kit/language/translation)
- [ML Kit iOS 安装与模型下载说明（CocoaPods）](https://developers.google.com/ml-kit/language/translation/ios)
- [ML Kit 翻译语言表（中文代码 `zh`）](https://developers.google.com/ml-kit/language/translation/translation-language-support)
- [Google Cloud Translation 语言表（常规翻译简体 `zh-CN`；Translation LLM 列表含 `zh-Hans`）](https://docs.cloud.google.com/translate/docs/languages)
- [Google Cloud Translation 设置要求（项目、API、结算、认证）](https://docs.cloud.google.com/translate/docs/setup)
- [Telegram：消息翻译（2021-12-30）](https://telegram.org/blog/reactions-spoilers-translations?setln=en)
- [Telegram：Premium 整聊翻译与频道自动翻译（2025-05-08）](https://telegram.org/blog/gift-marketplace-and-more)
- [固定上游：ChatTranslationPanelNode.swift](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TelegramUI/Components/TranslateHeaderPanelComponent/Sources/ChatTranslationPanelNode.swift)
