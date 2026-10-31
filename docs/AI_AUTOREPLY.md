# AI 助手与逐聊天自动回复

## 用户流程

1. 用户从聊天自动化菜单打开全局“AI 服务商”管理，添加一个或多个服务商名称、OpenAI-compatible HTTPS endpoint、模型和 API key。配置保存在此账号范围内；密钥保存在本机 Keychain。
2. 用户在目标聊天内将一个或多个已添加服务商单独分配给该聊天。添加服务商不会自动分配，也不会自动开启自动回复。
3. 用户打开某个会话，在会话内查看助手分配、数据范围和自动回复状态。每个会话、每个论坛主题分别保存状态，默认关闭。
4. 首次请求之前，显示不可混淆的同意提示：会把哪些消息内容发送给哪些 provider、数据可能如何留存/使用，以及撤回同意的入口。用户必须明确同意该会话的数据外发后，才可以发送第一条内容。
5. 自动回复开关由用户在该会话内单独打开。关闭或撤回同意后立即停止后续 AI 请求；不能用全局开关替代逐会话同意。

## 建议的策略模型

```text
AssistantProfile
  id, displayName, providerKind, endpoint, model, keychainCredentialRef, systemPrompt

ConversationAISettings (keyed by accountId + peerId + optional threadId)
  assignedAssistantIds: [AssistantProfile.id]
  autoReplyEnabled: false
  consentVersion: none
  consentedProviderIds: []
  contextPolicy: incomingTextOnly
```

Provider 抽象应是独立协议，例如 `AIReplyProvider`，并提供 OpenAI-compatible 与其他显式选定 provider 的适配器。API key/token 只在运行时录入并存入 iOS Keychain；不能写入仓库、构建配置、日志、崩溃报告或 GitHub Actions secrets。自定义远端 endpoint 默认要求 HTTPS；配置或连接失败时 fail closed。

Telegram 源码集成建议：

- 用 `AccountContext` 的 `ChatLocation`/`peerId` 与可选 `threadId` 标识会话；AI 状态不能放进现有全局 `ChatSettings`。
- 在 `ChatListUI/Sources/ChatContextMenus.swift` 加入逐会话入口，在列表中加入可多选分配助手的管理页；从该页可直接打开指定会话。
- 在聊天标题/会话设置中显示状态和“管理 AI 自动回复”入口。正常聊天列表、聊天历史、搜索、附件、通知和发送交互均保留。
- 生成后的回复应走 `ChatController` 暴露的原生消息发送/排队路径，并遵守 `canSendMessagesToChat`、当前 `peerId` 与 `threadId`；不能绕过用户/频道的发送权限或直接替换底层网络协议。

## 安全默认值

- 所有会话初始 `autoReplyEnabled = false`；选择助手或批量选择会话不会打开它。
- 首版仅发送触发消息的文本，不自动上传图片、文件、语音、联系人或完整聊天记录。扩展上下文必须由用户单独选择并在同意页明确说明。
- 群组默认只在明确提及/回复机器人或用户配置的触发条件时处理，不扫描或转发群聊全部内容；每个群组需要自己的授权。
- Secret Chats 默认不支持 AI 外发。只读频道或当前账号无权发送的会话不提供自动发送开关。
- 不响应自己的消息、AI 自己的消息或机器人消息；使用消息 ID 去重、速率限制和最大回复长度，防止循环和刷屏。
- 每次请求前重新检查该会话开关、provider 分配、同意版本、发送权限和当前账号；任一项缺失则不调用 provider。
- 先让用户手动预览回复，再开放“自动发送”选项。真正的自动发送也必须是该会话内的显式选择，并始终可以一键暂停。

## 聊天翻译与自动回复严格分离

逐会话自动翻译使用独立的 `ConversationTranslationSettings`（建议至少包含 `autoTranslateIncoming: false`、`targetLanguage: zh-Hans`、translation mode/provider 和单独的 consent version），按 `accountId + peerId + optional threadId` 保存。多选会话或分配 AI 助手不会开启翻译；翻译授权不会授权 AI 自动回复，AI 回复授权也不会授权把消息送去翻译。若翻译使用第三方 provider，必须在翻译开关开启前另行说明 provider/model/endpoint、要发送的入站文本和可能的数据处理方式，并取得该会话独立同意。实现细节和 Telegram 原生 Premium/频道规则见 [`CHAT_TRANSLATION.md`](CHAT_TRANSLATION.md)。

## 用户必须能看到的事实

AI 请求把选定内容传到第三方 provider；Telegram 的加密/云端保护不延伸到用户自行选择的 AI 服务。provider 可能按自己的条款保留、处理或用于改进服务。用户应能查看当前助手、端点、模型、最近的处理状态，并随时撤回某一会话的授权。撤回无法追回已经发送给 provider 的内容。

## 实施状态

代码现已包含全局服务商管理、Keychain 密钥存取、逐聊天服务商分配、独立默认关闭的自动回复开关和明确外发同意。当前 provider 请求格式为 OpenAI-compatible HTTPS；原生 Anthropic/Gemini 等非兼容协议还没有单独适配。静态回归测试通过，实际 iOS 构建与受控设备测试仍需验证“未同意绝不请求”“不同会话状态互不影响”“权限不足不会发送”。
