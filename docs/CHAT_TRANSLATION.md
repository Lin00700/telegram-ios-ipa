# 所选会话设备端自动翻译到简体中文

## 目标体验

- 用户可多选私聊、群组或频道，并给指定会话分配多个 AI 助手 profile；保留批量选择多个会话/profile 的既定能力。
- 自动翻译只处理用户可见的入站文字消息；原文完整保留，简体中文译文显示在原消息下方并明确标注。翻译不覆盖原文、不发送新消息，也不自动上传图片、语音或文件。
- 每个会话、每个论坛主题有独立的“自动翻译”开关，默认关闭。选择会话、分配 AI 助手或打开 AI 自动回复，都不能自动打开翻译。
- 翻译开关/翻译授权与 AI 自动回复开关/回复授权各自独立保存。开启翻译永远不代表授权 AI 回复；开启 AI 回复也永远不代表授权翻译。

## 每个聊天可随时单独开关

在当前聊天页右上角的更多菜单（`⋯`）中提供明确的“自动翻译新消息”开关；不提供默认开启的全局开关。群组论坛主题按 `peerId + threadId` 分开保存。状态按 `accountId + peerId + optional threadId` 持久化，应用重启后保持原值。

固定 Telegram 上游的更多菜单入口位于 [`ChatController.swift`](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TelegramUI/Sources/ChatController.swift) 的 `moreBarButton.contextAction`。现有委托只传 `peerId`；为支持论坛主题的独立开关，新增动作必须由当前 `ChatController` 保留 `threadId`，或扩展委托传递完整会话位置，不能丢掉主题 ID。

- **OFF（默认）**：不翻译新消息、不处理待翻译任务，也不为该聊天启动模型下载。
- **ON**：只翻译用户打开开关后收到的新入站文字消息；不回溯补译打开前收到的历史消息。原文始终保留，译文显示在原消息下方。
- 关闭时立即停止后续自动翻译；取消尚未开始的任务，无法取消的在途结果丢弃。此前已显示的译文可保留，但不再更新或翻译新消息。
- 首次开启时先说明“本机处理，聊天正文不会上传；首次下载模型需要联网”，并取得该会话的本地翻译授权。关闭翻译不影响任何 AI 回复设置或已显示的 AI 消息。
- 此开关与 AI 自动回复开关完全分开：翻译开/关不改变 AI 自动回复；AI 自动回复开/关也不改变翻译。

## 已选择：Google ML Kit 设备端翻译

翻译采用 Google ML Kit Translation 的设备端 API，不使用 Google Cloud Translation API，不启用 Cloud 结算，也不把聊天正文上传给 Google Cloud。Google 官方说明，ML Kit 在设备本地处理文本；首次使用时需下载对应语言模型（约 30 MB），下载后可离线翻译。首次下载模型会连接 Google，但模型下载不包含聊天正文。模型下载默认走 Wi-Fi，用户明确允许后才可使用蜂窝网络；模型尚未就绪时不发送翻译请求。

此功能逐会话默认关闭，并需要用户在该会话确认开启；确认页说明“由设备端 Google ML Kit 处理，聊天文本留在本机；首次下载语言模型需联网”。这是一项本地翻译授权，与 AI profile、AI 自动回复、其 provider/API key 和对应授权完全分开。翻译不使用 AI 自动回复所选的 provider，也不依赖用户配置 AI API key。

关闭该会话翻译后，停止后续翻译；删除模型只影响本机缓存，不更改 Telegram 消息。不得自动切换到 Cloud Translation 或任何其他远端 provider。若设备端结果不满足简体中文要求，应停止/标记该会话翻译不可用并询问用户，不得悄悄把消息发到云端。

## 建议本地规范化：ML Kit + OpenCC `t2s`

ML Kit 官方语言表只列通用中文代码 `zh`，没有单独的 `zh-Hans`/`zh-CN` 目标，也未保证结果一定是简体。建议在设备内串接一层 OpenCC：先让 ML Kit 将来文翻译成通用中文，再对译文应用 OpenCC 的 `t2s`（OpenCC 标准繁体 → 简体）字典转换，最后显示规范化译文。原消息不进入转换器、不被改写；即使 ML Kit 对繁体中文输入返回原文，`t2s` 仍可尝试把该文本转成简体。

OpenCC 是确定性的离线词典转换库，支持字词级映射；它只负责繁简字形/词形转换，不会翻译语言、改善 ML Kit 的语义准确度，也不保证将粤语改写成普通话。若 ML Kit 译文意思不通，或 OpenCC 处理后仍有不可接受的繁体/混合字形，不能声称该消息已可靠翻译。始终保留原文供用户判断。

### 许可与随包体积

OpenCC 上游版本 1.4.2 以 Apache License 2.0 发布。上游 README 还列出其依赖项目的不同许可，例如 darts-clone 与 marisa-trie 为 BSD、RapidJSON 为 MIT；实际集成时应按最终 Bazel 依赖闭包保留对应许可证/通知文件。私有自用不改变依赖许可要求，若之后分发 IPA 也应保留这些材料。

OpenCC 的 `t2s.json` 仅引用四个运行时字典：`CJK_Compatibility_Ideographs.ocd2`、`TSPhrases.ocd2`、`TSCharactersExt.ocd2`、`TSCharacters.ocd2`；其中 `TSCharactersExt` 可由 `TSCharacters.txt` 在构建时生成。对应的三份原始文本输入合计 **152,799 字节（约 153 KB）**，而上游全部 20 份字典文本合计 **1,425,567 字节（约 1.43 MB）**。这是原始字典文本体积，不是编译后的 `.ocd2` 或最终 IPA 增量；后两者尚未测量。

为保持轻量，不应直接使用上游根 `//:opencc_lib` 的默认资源包：它把所有配置及二进制/文本字典列入 `data`。建议建立窄化的 Bazel target，只包含 OpenCC 转换运行时代码、`t2s.json` 及其四个字典资产；避免打包其他地区词典、命令行工具和测试资源。

## Bazel 接入可行性

与 ML Kit 的 CocoaPods-only 官方 iOS 接入不同，OpenCC 1.4.2 上游本身提供 `BUILD.bazel`、`MODULE.bazel` 和 C++ library target。上游 `.bazelversion` 为 9.1.1；固定 Telegram 上游的 `versions.json` 记录 Bazel 9.2.0，因此版本号接近，基于 Bazel 接入具有实际可行性，但并不等于已在 Telegram 构建中通过。

推荐实现方式是固定 OpenCC 1.4.2 源码/commit，在 Telegram Bazel 图中建立只含转换器与 `t2s` 资源的窄化 target；用 Objective-C++ 小封装把 Swift 消息译文送入 C++ `SimpleConverter`，再把结果返回消息显示层。OpenCC 的 Bazel `MODULE.bazel` 包含不少 Python、Node、测试和工具链依赖；直接照搬整个模块会比功能所需更重，宜只接入运行时代码和必要的 C++ 依赖，并固定其版本/许可证。

集成后必须验证设备与模拟器架构、字典资源定位、线程安全/并发、内存和最终 IPA 资源体积。当前没有实际添加 OpenCC、创建 Bazel target 或运行 iOS 构建，因此目前只能说“技术上可行、应采用窄化 target”，不能称已集成、已构建或已测量最终体积。

## 固定上游的实现点与必须避开的路径

当前仓库不是 Telegram 应用源码副本；构建脚本只在 CI 临时 checkout 上游、改品牌并补上 unsigned build 参数，尚无功能 overlay。实现运行时开关，需要再增加受版本固定的源码 overlay，并在 macOS/Xcode 构建中验证。

上游已有的 `ChatTranslationState` 虽按 peer/thread 缓存一些状态，但它还受 Telegram 全局语言设置和翻译资格逻辑约束，不能替代本功能的“明确选择、默认 OFF”本地设置。频道的 `_internal_toggleAutoTranslation` 会调用 Telegram 服务器 API，也不能用于这里。应另存 `(accountId, peerId, optional threadId) -> autoTranslateIncoming`；没有记录时视为 OFF，并保存显式 OFF。可以从 [`ChatTranslation.swift`](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TranslateUI/Sources/ChatTranslation.swift) 学习 peer/thread 键方式，但不能复用其服务端语义。

不应调用 Telegram 的 `messages.translateText` 翻译路径：它会请求 Telegram 服务，且现有 [`ChatMessageTextBubbleContentNode.swift`](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TelegramUI/Components/Chat/ChatMessageTextBubbleContentNode/Sources/ChatMessageTextBubbleContentNode.swift) 展示路径会以译文替换原文。现有 [`ChatHistoryListNode.swift`](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TelegramUI/Sources/ChatHistoryListNode.swift) 还会扫描可见历史消息来补译，也不满足只处理开关开启后新消息的要求。应只监听开关开启期间新插入的入站文字消息，关闭时取消/丢弃待处理结果，并在消息气泡中增加保留原文的次级译文行。

## 简体输出验收计划

实际验收时仅用合成文本，不使用用户聊天内容，也不请求 Cloud Translation：

1. 让 ML Kit 翻译英语短句，再将结果经 OpenCC `t2s` 处理；检查“会议/后/头发/面条/干”等简体字形，而非“會議/後/頭髮/麵條/乾”。
2. 用繁体中文输入（例如“會議後我去買麵條”）检查最终输出是否变为简体；确认原文仍逐字保留。
3. 用日文、韩文及至少一种常用欧洲语言的合成短句检查译文意思与可读性。ML Kit 的非英语互译会以英语为中转，需人工评估；OpenCC 不能修复错误翻译。
4. 抽查专名、口语、emoji、换行、短消息和繁简混合内容；任何不自然/错误内容都由原文兜底。
5. 测试模型未下载、下载失败、离线、蜂窝网络未授权、低内存及应用重启；原文始终可见，失败不丢消息、不记录正文。模型首下载默认仅 Wi-Fi。
6. 检查聊天文本不会流向 Google Cloud、Telegram 翻译接口或 AI 回复 provider；关闭单个会话翻译后不再处理后续消息。

本地工作环境没有 iOS/Xcode；GitHub Actions workflow 已发布，两项 Telegram API repository secrets 已通过仓库网页配置，基础 macOS 构建已实际启动。ML Kit + OpenCC 及其 UI 尚未加入构建，上述输出和集成仍为**未验证**。

## 与 AI 自动回复彻底分开

两类功能各自保存状态，不能共用开关、profile 选择或授权：

```text
ConversationTranslationSettings (accountId + peerId + optional threadId)
  autoTranslateIncoming: false
  mlKitTargetLanguage: "zh"     // ML Kit 通用中文代码
  localNormalizer: "OpenCC:t2s" // 候选本地规范化层，待集成
  localConsentVersion: none
  displayMode: originalAndTranslation

ConversationAISettings (accountId + peerId + optional threadId)
  assignedAssistantIds: []       // 可多选
  autoReplyEnabled: false
  consentedProviderIds: []
```

翻译不调用 AI 回复 provider；AI 回复 profile 不会触发翻译。无论选中多少 AI 助手，翻译状态仍独立。翻译功能不处理历史记录，只在当前会话开关开启且收到新入站文字时运行，按消息 ID 去重、控制并发并遵守每会话独立状态。

## 群组与频道限制

- 群组/论坛主题只处理用户明确开启的会话/主题，按 `peerId + threadId` 区分；绝不读取或上传未选聊天的内容。
- 频道只处理当前账号有权查看、且用户在本机明确开启的消息；设备端 ML Kit + OpenCC 翻译不依赖 Telegram Premium 或 Telegram 服务器翻译功能。
- 不调用 Telegram 频道自动翻译设置接口，不修改频道设置、消息、反应或评论，也不代发内容。该功能只在本机显示译文；没有频道管理权限时不展示任何修改频道侧设置的入口。

## 中文界面与样式

新增控件提供简体中文（`zh-Hans`）文案，例如“自动翻译”“目标语言”“原文”“简体中文译文”“设备端翻译”“模型下载”“撤回授权”。译文位于原文下方，以次级文字色和轻分隔标识，并沿用暖象牙白、砖红状态点和圆角交互。UI 显示“简体中文”是用户目标，不可代替设备端输出验收。

## 验收清单

1. 所有会话/主题默认关闭；只有选中的会话在本地确认后开始处理新入站文字。
2. ML Kit 翻译结果先经 OpenCC `t2s` 本地规范化，之后与原文同时显示；失败/离线时仍保留原文。
3. ML Kit + OpenCC 通过繁简字形、繁体输入、自然度及真实 iOS 架构测试；不通过即标记未完成，不自动调用云端服务。
4. 聊天正文始终不发往 Google Cloud、Telegram 翻译接口或 AI 回复 provider；模型下载只获取模型文件。
5. 翻译开关与 AI 自动回复开关、profile 分配和各自授权互不影响。
6. 频道仅在当前账号可见且用户明确开启时本地翻译；不要求 Telegram Premium/服务器翻译，也不发送或修改频道内容/设置。
7. 依赖与 Bazel 规则通过 Xcode release 构建，确认 iOS deployment target、许可证、资源/隐私清单、模型下载和无签名 IPA 打包均正确。

## 实施状态

用户已选择 ML Kit 设备端路线，并要求增加逐聊天独立开关；OpenCC `t2s` 是推荐的本地简体字形规范化层。当前仓库只有规格与构建脚手架，没有 Telegram 翻译功能 overlay；因此运行时开关、翻译路径和原文+译文气泡尚未实现/验证。未使用 Cloud Translation API、未启用结算、未要求翻译 API key。Workflow 与 Telegram API secrets 已配置；首次真实构建在 Bazel 的 extension profile 校验处失败，正在修正 unsigned 补丁，尚无可验证的 IPA。

## 来源

- [ML Kit Translation：设备端处理与质量限制](https://developers.google.com/ml-kit/language/translation)
- [ML Kit iOS：CocoaPods 安装、模型下载/管理与模型大小](https://developers.google.com/ml-kit/language/translation/ios)
- [ML Kit 官方翻译语言表：中文仅列 `zh`](https://developers.google.com/ml-kit/language/translation/translation-language-support)
- [OpenCC 1.4.2 项目（固定 commit）](https://github.com/BYVoid/OpenCC/tree/fae2a0a911c30764e669a7d8b0591cd8e852934a)
- [OpenCC Apache 2.0 LICENSE](https://github.com/BYVoid/OpenCC/blob/fae2a0a911c30764e669a7d8b0591cd8e852934a/LICENSE)
- [OpenCC `t2s` 字典配置](https://github.com/BYVoid/OpenCC/blob/fae2a0a911c30764e669a7d8b0591cd8e852934a/data/config/t2s.json)
- [OpenCC Bazel 根 target](https://github.com/BYVoid/OpenCC/blob/fae2a0a911c30764e669a7d8b0591cd8e852934a/BUILD.bazel)
- [OpenCC Bazel 依赖模块](https://github.com/BYVoid/OpenCC/blob/fae2a0a911c30764e669a7d8b0591cd8e852934a/MODULE.bazel)
- [OpenCC `.bazelversion`](https://github.com/BYVoid/OpenCC/blob/fae2a0a911c30764e669a7d8b0591cd8e852934a/.bazelversion)
- [Telegram 固定上游 Bazel 版本](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/versions.json)
- [Google ML Kit 样例 issue：Translate Pod 的 iOS deployment target 记录](https://github.com/googlesamples/mlkit/issues/795)
- [固定上游：ChatController.swift](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TelegramUI/Sources/ChatController.swift)
- [固定上游：ChatTranslation.swift](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TranslateUI/Sources/ChatTranslation.swift)
- [固定上游：ChatHistoryListNode.swift](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TelegramUI/Sources/ChatHistoryListNode.swift)
- [固定上游：ChatMessageTextBubbleContentNode.swift](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TelegramUI/Components/Chat/ChatMessageTextBubbleContentNode/Sources/ChatMessageTextBubbleContentNode.swift)
- [固定上游：Translate.swift](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TelegramCore/Sources/TelegramEngine/Messages/Translate.swift)
- [固定上游：AutoTranslate.swift](https://github.com/TelegramMessenger/Telegram-iOS/blob/fb0e62ba8a147f0821da6aa63c09da7d79a10111/submodules/TelegramCore/Sources/TelegramEngine/Peers/AutoTranslate.swift)
