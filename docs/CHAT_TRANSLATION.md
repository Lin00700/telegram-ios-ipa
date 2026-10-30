# 所选会话设备端自动翻译到简体中文

## 目标体验

- 用户可多选私聊、群组或频道，并给指定会话分配多个 AI 助手 profile；保留批量选择多个会话/profile 的既定能力。
- 自动翻译只处理用户可见的入站文字消息；原文完整保留，简体中文译文显示在原消息下方并明确标注。翻译不覆盖原文、不发送新消息，也不自动上传图片、语音或文件。
- 每个会话、每个论坛主题有独立的“自动翻译”开关，默认关闭。选择会话、分配 AI 助手或打开 AI 自动回复，都不能自动打开翻译。
- 翻译开关/翻译授权与 AI 自动回复开关/回复授权各自独立保存。开启翻译永远不代表授权 AI 回复；开启 AI 回复也永远不代表授权翻译。

## 已选择：Google ML Kit 设备端翻译

翻译采用 Google ML Kit Translation 的设备端 API，不使用 Google Cloud Translation API，不启用 Cloud 结算，也不把聊天正文上传给 Google Cloud。Google 官方说明，ML Kit 在设备本地处理文本；首次使用时需下载对应语言模型（约 30 MB），下载后可离线翻译。首次下载模型会连接 Google，但模型下载不包含聊天正文。模型下载默认走 Wi-Fi，用户明确允许后才可使用蜂窝网络；模型尚未就绪时不发送翻译请求。

此功能仍逐会话默认关闭，并需要用户在该会话确认开启；确认页说明“由设备端 Google ML Kit 处理，聊天文本留在本机；首次下载语言模型需联网”。这是一项本地翻译授权，与 AI profile、AI 自动回复、其 provider/API key 和对应授权完全分开。翻译不使用 AI 自动回复所选的 provider，也不依赖用户配置 AI API key。

关闭该会话翻译后，停止后续翻译；删除模型只影响本机缓存，不更改 Telegram 消息。不得自动切换到 Cloud Translation 或任何其他远端 provider。若设备端结果不满足简体中文要求，应停止/标记该会话翻译不可用并询问用户，不得悄悄把消息发到云端。

## 简体中文输出：必须设备实测

ML Kit 官方翻译语言表只列通用中文代码 `zh`，不提供单独的 `zh-Hans`/`zh-CN` 目标，也没有保证输出必定使用简体字的文档。因此目前只能确认它支持“中文”，**不能据此宣称已经满足简体中文**。应用界面目标仍显示“简体中文”，但在以下真实 iOS 验收通过之前，不得声称翻译结果已可靠保持简体。

验收必须在集成后的 iPhone/iOS 模拟器上用合成文本运行 ML Kit（不是把聊天内容发送到 Google Translate 网页或 Cloud API）：

1. 英文句子需覆盖有繁简差异的字词，例如“我在会议后染了头发”“面条有点干”；检查输出使用“会议/后/头发/面条/干”等简体字形，而非“會議/後/頭髮/麵條/乾”。
2. 用日文、韩文及至少一种常用欧洲语言的合成短句测试目标为 `zh` 时的自然度；ML Kit 的非英语互译会以英语为中转，需人工评估可读性。
3. 加入繁体中文输入（例如“會議後我去買麵條”），检查目标 `zh` 是否真的转换成简体，而不是原样保留或继续输出繁体。
4. 使用人工审阅及本地繁简检查表验证字形；对专名、口语、短消息、emoji 与换行做抽样。任何脚本不合格、返回原文或质量不可接受的情况都算未通过；不允许自动回退到云服务。
5. 在模型未下载、下载失败、离线、蜂窝网络未授权、低内存和应用重启时验证行为；原文始终可读，翻译失败不丢消息、不记录正文。

当前工作环境没有 iOS/Xcode 运行环境，GitHub Actions workflow 也尚未获准写入，因此这里不能实际运行上述 ML Kit 输出测试；输出脚本与自然度仍为**未验证**。

## Telegram iOS / Bazel 集成评估

Google 官方 iOS 集成页示例要求 CocoaPods 依赖 `GoogleMLKit/Translate`，并通过 `.xcworkspace` 工作；没有找到 Google 官方 Bazel 接入配方。Telegram iOS 固定上游使用 Make.py/Bazel 构建，因此 ML Kit 不是可直接添加的一条 Bazel 依赖。

Bazel 技术上可以导入预编译 Apple Framework；[`rules_apple` 官方文档](https://github.com/bazelbuild/rules_apple/blob/master/doc/frameworks.md)提供静态/动态 framework import 规则。要接入 ML Kit，仍须从 CocoaPods 解析/固定 Translate Pod 的全部二进制传递依赖与资源，选择设备/模拟器架构，创建并维护 Bazel targets，正确打包框架、模型管理所需资源和隐私清单，再跑完整 iOS release 构建。这是可尝试的自定义集成，不是已经确认能工作的官方 Bazel 支持。

Google ML Kit 样例仓库的 issue 记录 Translate Pod 的最低 iOS 版本曾提升到 iOS 15.5；接入前要核对固定 Telegram 上游的 deployment target 与当前 Podspec，避免无意提高应用最低系统版本。最终需在 CI/Xcode 中验证 arm64 真机与模拟器目标、无签名 IPA 打包、模型下载和翻译；在这之前不宣称已集成或可安装。

## 与 AI 自动回复彻底分开

两类功能各自保存状态，不能共用开关、profile 选择或授权：

```text
ConversationTranslationSettings (accountId + peerId + optional threadId)
  autoTranslateIncoming: false
  targetLanguage: "zh"              // ML Kit 唯一公开的中文代码；UI目标为简体
  engine: googleMlKitOnDevice
  localConsentVersion: none
  displayMode: originalAndTranslation

ConversationAISettings (accountId + peerId + optional threadId)
  assignedAssistantIds: []           // 可多选
  autoReplyEnabled: false
  consentedProviderIds: []
```

翻译 profile 不调用 AI 回复 provider；AI 回复 profile 不会触发翻译。无论选中多少 AI 助手，翻译状态仍独立。翻译功能不处理历史记录，只在当前会话开关开启且收到新入站文字时运行，按消息 ID 去重、控制并发并遵守每会话独立状态。

## 群组与频道限制

- 群组/论坛主题只处理用户明确开启的会话/主题，按 `peerId + threadId` 区分；绝不读取或上传未选聊天的内容。
- 频道仅处理当前账号有权查看、且符合 Telegram 频道翻译能力/限制的消息；频道未启用相应翻译能力时不提供自动翻译开关。
- 不调用 Telegram 频道自动翻译设置接口，不修改频道设置、消息、反应或评论，也不代发内容。该功能只在本机显示译文；没有频道管理权限时不展示任何修改频道侧设置的入口。

## 中文界面与样式

新增控件提供简体中文（`zh-Hans`）文案，例如“自动翻译”“目标语言”“原文”“简体中文译文”“设备端翻译”“模型下载”“撤回授权”。译文位于原文下方，以次级文字色和轻分隔标识，并沿用暖象牙白、砖红状态点和圆角交互。UI 显示“简体中文”是用户目标，不可代替输出验收。

## 验收清单

1. 所有会话/主题默认关闭；只有选中的会话在本地确认后开始处理新入站文字。
2. 设备端模型首次下载后可离线翻译；聊天正文始终不发往 Google Cloud、Telegram 翻译接口或 AI 回复 provider。
3. 原文与译文同时显示；模型/翻译失败、离线或权限不足时仍保留原文。
4. ML Kit `zh` 输出通过繁简字形、繁体输入、常见短消息及人工可读性测试；不通过即标记未完成，不自动调用云端服务。
5. 翻译开关与 AI 自动回复开关、profile 分配和各自授权互不影响。
6. 频道权限与频道翻译能力受限时不开启；客户端不发送或修改频道内容/设置。
7. 依赖与 Bazel 规则通过 Xcode release 构建，确认 iOS deployment target、资源/隐私清单、模型下载和无签名 IPA 打包均正确。

## 实施状态

用户已选择 ML Kit 设备端路线。未使用 Cloud Translation API；未启用结算；未要求 API key。逐会话开关、设备端 ML Kit 集成、简体输出实测、原文+译文气泡 UI 和 Bazel 依赖均尚未实现/验证。GitHub Actions workflow/secrets 写权限仍待恢复，目前没有可验证的 IPA。

## 来源

- [ML Kit Translation：设备端处理与质量限制](https://developers.google.com/ml-kit/language/translation)
- [ML Kit iOS：CocoaPods 安装、模型下载/管理与模型大小](https://developers.google.com/ml-kit/language/translation/ios)
- [ML Kit 官方翻译语言表：中文仅列 `zh`](https://developers.google.com/ml-kit/language/translation/translation-language-support)
- [`rules_apple`：导入预编译 Framework 的官方规则](https://github.com/bazelbuild/rules_apple/blob/master/doc/frameworks.md)
- [Google ML Kit 样例仓库 issue：Translate Pod 的 iOS deployment target 记录](https://github.com/googlesamples/mlkit/issues/795)
- [固定上游：ChatTranslationPanelNode.swift](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TelegramUI/Components/TranslateHeaderPanelComponent/Sources/ChatTranslationPanelNode.swift)
- [固定上游：ChatTranslation.swift](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TranslateUI/Sources/ChatTranslation.swift)
