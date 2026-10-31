#!/usr/bin/env python3
"""Apply per-chat local translation and consent-gated AI reply to pinned Telegram-iOS.

The overlay is deliberately deterministic: every source edit is guarded by an
exact match count and a marker, so upstream drift fails closed instead of
silently producing a partially integrated client.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

MARKER = "CUE_RUNTIME_FEATURES_V1"


def replace_exact(text: str, old: str, new: str, expected: int, label: str) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{label}: expected {expected} source occurrence(s), found {count}")
    return text.replace(old, new, expected)


def patch_chat_controller(root: Path) -> None:
    path = root / "submodules/TelegramUI/Sources/ChatController.swift"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    text = replace_exact(text, "import TelegramCore\n", "import TelegramCore\nimport CueChatAutomation\n", 1, "chat controller automation import")

    old = '''        self.moreBarButton.contextAction = { [weak self] sourceNode, gesture in
            guard let self else {
                return
            }
            guard let peerId = self.chatLocation.peerId else {
                return
            }
\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20
            if peerId == self.context.account.peerId {
                PeerInfoScreenImpl.openSavedMessagesMoreMenu(context: self.context, sourceController: self, isViewingAsTopics: false, sourceView: self.navigationBar?.navigationButtonContextContainer(sourceView: sourceNode.view) ?? sourceNode.view, gesture: gesture)
            } else if peerId.namespace == Namespaces.Peer.CloudUser {
                self.openBotForumMoreMenu(sourceView: self.navigationBar?.navigationButtonContextContainer(sourceView: sourceNode.view) ?? sourceNode.view, gesture: gesture)
            } else {
                ChatListControllerImpl.openMoreMenu(context: self.context, peerId: peerId, sourceController: self, isViewingAsTopics: false, sourceView: sourceNode.view, gesture: gesture)
            }
        }
'''
    new = '''        self.moreBarButton.contextAction = { [weak self] sourceNode, gesture in
            guard let self, let peerId = self.chatLocation.peerId else {
                return
            }
            let sourceView = self.navigationBar?.navigationButtonContextContainer(sourceView: sourceNode.view) ?? sourceNode.view
            let openTelegramMenu = { [weak self] in
                guard let self else {
                    return
                }
                if peerId == self.context.account.peerId {
                    PeerInfoScreenImpl.openSavedMessagesMoreMenu(context: self.context, sourceController: self, isViewingAsTopics: false, sourceView: sourceView, gesture: nil)
                } else if peerId.namespace == Namespaces.Peer.CloudUser {
                    self.openBotForumMoreMenu(sourceView: sourceView, gesture: nil)
                } else {
                    ChatListControllerImpl.openMoreMenu(context: self.context, peerId: peerId, sourceController: self, isViewingAsTopics: false, sourceView: sourceView, gesture: nil)
                }
            }
            if gesture != nil {
                openTelegramMenu()
                return
            }
            let isBroadcast: Bool
            if let channel = self.presentationInterfaceState.renderedPeer?.chatMainPeer as? TelegramChannel, case .broadcast = channel.info {
                isBroadcast = true
            } else {
                isBroadcast = false
            }
            let isGroup: Bool
            if peerId.namespace == Namespaces.Peer.CloudGroup {
                isGroup = true
            } else if peerId.namespace == Namespaces.Peer.CloudChannel,
                      let channel = self.presentationInterfaceState.renderedPeer?.chatMainPeer as? TelegramChannel,
                      case .group = channel.info {
                isGroup = true
            } else {
                isGroup = false
            }
            let isPrivateUser = peerId.namespace == Namespaces.Peer.CloudUser && peerId != self.context.account.peerId
            let canAutoReply = !isBroadcast && (isPrivateUser || isGroup)
            CueFeatureSettingsUI.presentChatFeaturesMenu(
                accountId: self.context.account.peerId.toInt64(),
                peerId: peerId.toInt64(),
                threadId: self.chatLocation.threadId,
                presenter: self,
                allowAutoReply: canAutoReply,
                onMoreOptions: openTelegramMenu
            )
        } // CUE_RUNTIME_FEATURES_V1
'''
    text = replace_exact(text, old, new, 1, "chat-specific feature menu")
    path.write_text(text, encoding="utf-8")


def history_helpers() -> str:
    return r'''    private func cueFeatureMessageKey(_ message: Message, peerId: PeerId, threadId: Int64?) -> CueTranslationMessageKey {
        return CueTranslationMessageKey(
            accountId: self.context.account.peerId.toInt64(),
            peerId: peerId.toInt64(),
            threadId: threadId,
            namespace: message.id.namespace,
            messageId: message.id.id
        )
    }

    @objc private func cueTranslationSettingsDidChange(_ notification: Notification) {
        guard let userInfo = notification.userInfo,
              let accountId = userInfo["accountId"] as? NSNumber,
              let peerId = userInfo["peerId"] as? NSNumber,
              let threadKey = userInfo["threadId"] as? String,
              accountId.int64Value == self.context.account.peerId.toInt64(),
              let currentPeerId = self.chatLocation.peerId,
              currentPeerId.toInt64() == peerId.int64Value,
              (self.chatLocation.threadId.map(String.init) ?? "root") == threadKey else {
            return
        }
        let messageIds = self.previousView.with { value in
            value?.0.originalView.entries.map { $0.message.id } ?? []
        }
        for messageId in messageIds {
            self.controllerInteraction.requestMessageUpdate(messageId, false, nil)
        }
    }

    private func cueContainsUsernameMention(_ text: String, username: String) -> Bool {
        guard !username.isEmpty,
              let expression = try? NSRegularExpression(
                pattern: "(?<![A-Za-z0-9_])@\(NSRegularExpression.escapedPattern(for: username))(?![A-Za-z0-9_])",
                options: [.caseInsensitive]
              ) else {
            return false
        }
        let range = NSRange(text.startIndex ..< text.endIndex, in: text)
        return expression.firstMatch(in: text, options: [], range: range) != nil
    }

    private func cueHasMentionOfAccount(_ message: Message, completion: @escaping (Bool) -> Void) {
        let accountPeerId = self.context.account.peerId
        let hasEntityMention = message.attributes
            .compactMap { $0 as? TextEntitiesMessageAttribute }
            .flatMap { $0.entities }
            .contains { entity in
                if case let .TextMention(peerId) = entity.type {
                    return peerId == accountPeerId
                }
                return false
            }
        if hasEntityMention {
            completion(true)
            return
        }

        let _ = (self.context.account.postbox.peerView(id: accountPeerId)
        |> take(1)
        |> deliverOnMainQueue).startStrict(next: { [weak self] peerView in
            guard let self, let accountUser = peerView.peers[accountPeerId] as? TelegramUser else {
                completion(false)
                return
            }
            var usernames = accountUser.usernames.map { $0.username }
            if let username = accountUser.username {
                usernames.append(username)
            }
            completion(usernames.contains { self.cueContainsUsernameMention(message.text, username: $0) })
        })
    }

    private func cueStartAIReply(_ message: Message, peerId: PeerId, threadId: Int64?, key: CueTranslationMessageKey) {
        let options = CueFeaturePreferences.aiOptions(accountId: key.accountId, peerId: key.peerId, threadId: threadId)
        guard options.autoReplyEnabled,
              options.outboundConsentAccepted,
              !options.assignedProfileIDs.isEmpty,
              self.controllerInteraction.canSendMessages(),
              CueAIReplyStore.shared.claim(key) else {
            return
        }

        CueAIReplyService.shared.generateReply(
            incomingText: message.text,
            accountId: key.accountId,
            peerId: key.peerId,
            threadId: threadId,
            completion: { [weak self] reply in
                DispatchQueue.main.async {
                    guard let self,
                          let reply,
                          !reply.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                        CueAIReplyStore.shared.finish(key, sent: false)
                        return
                    }
                    let currentOptions = CueFeaturePreferences.aiOptions(accountId: key.accountId, peerId: key.peerId, threadId: threadId)
                    guard currentOptions.autoReplyEnabled,
                          currentOptions.outboundConsentAccepted,
                          self.controllerInteraction.canSendMessages() else {
                        CueAIReplyStore.shared.finish(key, sent: false)
                        return
                    }
                    self.controllerInteraction.sendMessage(reply, message.id)
                    CueAIReplyStore.shared.finish(key, sent: true)
                }
            }
        )
    }

    private func cueHandleNewIncomingMessage(_ message: Message, peerId: PeerId, threadId: Int64?, isGroup: Bool, isBroadcast: Bool) {
        guard message.effectivelyIncoming(self.context.account.peerId),
              !message.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            return
        }

        let key = self.cueFeatureMessageKey(message, peerId: peerId, threadId: threadId)
        let accountId = key.accountId
        let chatId = key.peerId

        if CueFeaturePreferences.isAutoTranslationEnabled(accountId: accountId, peerId: chatId, threadId: threadId),
           CueFeaturePreferences.hasTranslationConsent(accountId: accountId, peerId: chatId, threadId: threadId),
           let generation = CueTranslationStore.shared.claim(key) {
            CueLocalTranslationService.shared.translateToSimplifiedChinese(message.text) { [weak self] translatedText in
                let stillEnabled = CueFeaturePreferences.isAutoTranslationEnabled(accountId: accountId, peerId: chatId, threadId: threadId)
                    && CueFeaturePreferences.hasTranslationConsent(accountId: accountId, peerId: chatId, threadId: threadId)
                let isCurrent = CueTranslationStore.shared.isCurrent(key, generation: generation)
                CueTranslationStore.shared.finish(key, generation: generation, translatedText: stillEnabled && isCurrent ? translatedText : nil)
                guard stillEnabled, isCurrent, translatedText != nil else {
                    return
                }
                DispatchQueue.main.async { [weak self] in
                    self?.controllerInteraction.requestMessageUpdate(message.id, false, nil)
                }
            }
        }

        guard !isBroadcast else {
            return
        }
        if let author = message.author as? TelegramUser, author.botInfo != nil {
            return
        }
        let options = CueFeaturePreferences.aiOptions(accountId: accountId, peerId: chatId, threadId: threadId)
        guard options.autoReplyEnabled, options.outboundConsentAccepted else {
            return
        }

        if isGroup {
            let replyAttribute = message.attributes.compactMap { $0 as? ReplyMessageAttribute }.first
            self.cueHasMentionOfAccount(message) { [weak self] mentioned in
                guard let self else {
                    return
                }
                if mentioned {
                    self.cueStartAIReply(message, peerId: peerId, threadId: threadId, key: key)
                    return
                }
                guard let replyMessageId = replyAttribute?.messageId else {
                    return
                }
                let accountPeerId = self.context.account.peerId
                let _ = (self.context.account.postbox.messageAtId(replyMessageId)
                |> take(1)
                |> deliverOnMainQueue).startStrict(next: { [weak self] repliedToMessage in
                    guard let self, repliedToMessage?.author?.id == accountPeerId else {
                        return
                    }
                    self.cueStartAIReply(message, peerId: peerId, threadId: threadId, key: key)
                })
            }
        } else if peerId.namespace == Namespaces.Peer.CloudUser {
            self.cueStartAIReply(message, peerId: peerId, threadId: threadId, key: key)
        }
    }

'''


def patch_history_list(root: Path) -> None:
    path = root / "submodules/TelegramUI/Sources/ChatHistoryListNode.swift"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    text = replace_exact(text, "import TelegramCore\n", "import TelegramCore\nimport CueChatAutomation\n", 1, "history list automation import")
    text = replace_exact(
        text,
        "        let _ = self.view\n",
        "        let _ = self.view\n        NotificationCenter.default.addObserver(self, selector: #selector(self.cueTranslationSettingsDidChange(_:)), name: Notification.Name(\"CueTranslationSettingsChanged\"), object: nil)\n",
        1,
        "translation settings refresh observer registration",
    )
    text = replace_exact(
        text,
        "    deinit {\n        self.historyDisposable.dispose()\n",
        "    deinit {\n        NotificationCenter.default.removeObserver(self)\n        self.historyDisposable.dispose()\n",
        1,
        "translation settings refresh observer cleanup",
    )

    anchor = "    private func beginChatHistoryTransitions(resetScrolling: Bool, switchedToAnotherSource: Bool) {\n"
    helpers = history_helpers()
    text = replace_exact(text, anchor, helpers + anchor, 1, "history automation helpers")

    hook = '''                if let strongSelf = self {
                    if let recommendedChannels, !recommendedChannels.channels.isEmpty && !recommendedChannels.isHidden {
'''
    injected = '''                if case .InteractiveChanges = reason, let strongSelf = self, let previous = previous {
                    let automationPeerId: PeerId?
                    switch chatLocation {
                    case let .peer(peerId):
                        automationPeerId = peerId
                    case let .replyThread(messageId):
                        automationPeerId = messageId.peerId
                    default:
                        automationPeerId = nil
                    }
                    if let automationPeerId {
                        let previousIds = Set(previous.originalView.entries.map { $0.message.id })
                        let previousNewestIndex = previous.originalView.entries.map { $0.index }.max()
                        let now = Int32(Date().timeIntervalSince1970)
                        for entry in view.entries {
                            let message = entry.message
                            guard !previousIds.contains(message.id),
                                  message.timestamp >= now - 120,
                                  message.timestamp <= now + 120 else {
                                continue
                            }
                            if let previousNewestIndex, message.index <= previousNewestIndex {
                                continue
                            }
                            let channel = message.peers[automationPeerId] as? TelegramChannel
                            let isBroadcast: Bool
                            let isGroup: Bool
                            if automationPeerId.namespace == Namespaces.Peer.CloudGroup {
                                isBroadcast = false
                                isGroup = true
                            } else if let channel {
                                if case .broadcast = channel.info {
                                    isBroadcast = true
                                    isGroup = false
                                } else {
                                    isBroadcast = false
                                    if case .group = channel.info {
                                        isGroup = true
                                    } else {
                                        isGroup = false
                                    }
                                }
                            } else {
                                isBroadcast = automationPeerId.namespace == Namespaces.Peer.CloudChannel
                                isGroup = false
                            }
                            strongSelf.cueHandleNewIncomingMessage(
                                message,
                                peerId: automationPeerId,
                                threadId: chatLocation.threadId,
                                isGroup: isGroup,
                                isBroadcast: isBroadcast
                            )
                        }
                    }
                }

                if let strongSelf = self {
                    if let recommendedChannels, !recommendedChannels.channels.isEmpty && !recommendedChannels.isHidden {
'''
    text = replace_exact(text, hook, injected, 1, "new incoming history message hook")
    text = text.replace("                if let strongSelf = self {\n                    if let recommendedChannels", f"                if let strongSelf = self {{\n                    if let recommendedChannels", 1)
    if "CUE_RUNTIME_FEATURES_V1_HISTORY" not in text:
        text = text.replace(
            "                if case .InteractiveChanges = reason, let strongSelf = self, let previous = previous {",
            "                // CUE_RUNTIME_FEATURES_V1_HISTORY: only new, recent entries are processed.\n                if case .InteractiveChanges = reason, let strongSelf = self, let previous = previous {",
            1,
        )
    path.write_text(text, encoding="utf-8")


def patch_bubble(root: Path) -> None:
    path = root / "submodules/TelegramUI/Components/Chat/ChatMessageTextBubbleContentNode/Sources/ChatMessageTextBubbleContentNode.swift"
    text = path.read_text(encoding="utf-8")
    if MARKER in text:
        return
    text = replace_exact(text, "import TelegramCore\n", "import TelegramCore\nimport CueChatAutomation\n", 1, "bubble automation import")

    text = replace_exact(
        text,
        "                let attributedText: NSAttributedString\n",
        "                var attributedText: NSAttributedString\n",
        1,
        "mutable translated message text",
    )

    anchor = '''                } else {
                    attributedText = NSAttributedString(string: " ", font: textFont, textColor: messageTheme.primaryTextColor)
                }
\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20\x20
                // The custom-emoji attribute is not re-applied here: `stringWithAppliedEntities`
                // already attached it, using ranges adjusted for the substitutions it performs
                // (`.FormattedDate` renders to text of a different length). An entity's own offsets
                // index `rawText`, not the string above, so indexing with them lands on the wrong
                // characters — or out of bounds.
'''
    insertion = '''                } else {
                    attributedText = NSAttributedString(string: " ", font: textFont, textColor: messageTheme.primaryTextColor)
                }

                if incoming && !item.presentationData.isPreview {
                    let accountId = item.context.account.peerId.toInt64()
                    let peerId = item.message.id.peerId.toInt64()
                    let threadId = item.chatLocation.threadId
                    if CueFeaturePreferences.isAutoTranslationEnabled(accountId: accountId, peerId: peerId, threadId: threadId),
                       CueFeaturePreferences.hasTranslationConsent(accountId: accountId, peerId: peerId, threadId: threadId) {
                        let key = CueTranslationMessageKey(
                            accountId: accountId,
                            peerId: peerId,
                            threadId: threadId,
                            namespace: item.message.id.namespace,
                            messageId: item.message.id.id
                        )
                        if let translatedText = CueTranslationStore.shared.value(for: key) {
                            let translatedFont = Font.regular(max(12.0, textFont.pointSize - 1.0))
                            let translatedColor = messageTheme.primaryTextColor.withMultipliedAlpha(0.82)
                            let combinedText = NSMutableAttributedString(attributedString: attributedText)
                            combinedText.append(NSAttributedString(string: "\\n\\n" + translatedText + "\\n", font: translatedFont, textColor: translatedColor))
                            if let badgeURL = Bundle.main.url(forResource: "CueGoogleTranslateAttribution", withExtension: "png"),
                               let badgeImage = UIImage(contentsOfFile: badgeURL.path), badgeImage.size.width > 0.0 {
                                let attachment = NSTextAttachment()
                                attachment.image = badgeImage
                                let badgeWidth: CGFloat = 104.0
                                let badgeHeight = badgeWidth * badgeImage.size.height / badgeImage.size.width
                                attachment.bounds = CGRect(x: 0.0, y: -2.0, width: badgeWidth, height: badgeHeight)
                                combinedText.append(NSAttributedString(attachment: attachment))
                            }
                            attributedText = combinedText
                        }
                    }
                } // CUE_RUNTIME_FEATURES_V1_BUBBLE

                // The custom-emoji attribute is not re-applied here: `stringWithAppliedEntities`
                // already attached it, using ranges adjusted for the substitutions it performs
                // (`.FormattedDate` renders to text of a different length). An entity's own offsets
                // index `rawText`, not the string above, so indexing with them lands on the wrong
                // characters — or out of bounds.
'''
    text = replace_exact(text, anchor, insertion, 1, "translated text rendering")
    path.write_text(text, encoding="utf-8")


def patch_build_dependencies(root: Path, target_entries: list[dict[str, str]]) -> None:
    if not target_entries:
        raise RuntimeError("ML Kit vendor target manifest is empty")
    if not any(entry.get("name") == "MLKitTranslate" for entry in target_entries):
        raise RuntimeError("MLKitTranslate.framework is missing from the generated vendor package")

    automation_dir = root / "submodules/CueChatAutomation"
    automation_dir.mkdir(parents=True, exist_ok=True)
    labels = "".join(
        f'        "//submodules/CueChatAutomation/MLKitVendor:{entry["target"]}",\n'
        for entry in target_entries
    )
    automation_build = '''load("@build_bazel_rules_swift//swift:swift.bzl", "swift_library")

swift_library(
    name = "CueChatAutomation",
    module_name = "CueChatAutomation",
    srcs = glob(["Sources/**/*.swift"]),
    deps = [
{labels}    ],
    visibility = ["//visibility:public"],
)
'''.format(labels=labels)
    (automation_dir / "BUILD").write_text(automation_build, encoding="utf-8")

    telegram_ui_build = root / "submodules/TelegramUI/BUILD"
    text = telegram_ui_build.read_text(encoding="utf-8")
    if "CUE_CHAT_AUTOMATION_DEP_V1" not in text:
        anchor = '        "//submodules/TelegramUIPreferences:TelegramUIPreferences",\n'
        addition = '        "//submodules/CueChatAutomation:CueChatAutomation",  # CUE_CHAT_AUTOMATION_DEP_V1\n'
        text = replace_exact(text, anchor, anchor + addition, 1, "TelegramUI automation dependency")
        telegram_ui_build.write_text(text, encoding="utf-8")

    bubble_build = root / "submodules/TelegramUI/Components/Chat/ChatMessageTextBubbleContentNode/BUILD"
    text = bubble_build.read_text(encoding="utf-8")
    if "CUE_TRANSLATION_STORE_DEP_V1" not in text:
        anchor = '        "//submodules/TelegramCore",\n'
        addition = '        "//submodules/CueChatAutomation:CueChatAutomation",  # CUE_TRANSLATION_STORE_DEP_V1\n'
        text = replace_exact(text, anchor, anchor + addition, 1, "bubble preferences dependency")
        bubble_build.write_text(text, encoding="utf-8")


def copy_runtime_sources(repo_root: Path, upstream_root: Path) -> None:
    destination = upstream_root / "submodules/CueChatAutomation/Sources"
    destination.mkdir(parents=True, exist_ok=True)
    for name in (
        "CueFeaturePreferences.swift",
        "CueLocalTranslation.swift",
        "CueOpenCCT2S.swift",
        "CueAIReplyService.swift",
        "CueAIReplyStore.swift",
        "CueFeatureSettingsUI.swift",
    ):
        shutil.copy2(repo_root / "runtime" / name, destination / name)

    resources = upstream_root / "Telegram/Telegram-iOS/Resources"
    resources.mkdir(parents=True, exist_ok=True)
    shutil.copy2(repo_root / "assets/CueGoogleTranslateAttribution.png", resources / "CueGoogleTranslateAttribution.png")
    shutil.copy2(repo_root / "assets/opencc/LICENSE.OpenCC", resources / "CueOpenCC-LICENSE.txt")
    for name in (
        "CJK_Compatibility_Ideographs.txt",
        "TSPhrases.txt",
        "TSCharactersExt.txt",
        "TSCharacters.txt",
    ):
        shutil.copy2(repo_root / "assets/opencc" / name, resources / f"CueOpenCC_{name}")


def patch_ziparchive_linkage(root: Path) -> None:
    path = root / "third-party/ZipArchive/Sources/SSZipArchive.m"
    text = path.read_text(encoding="utf-8")
    # This helper has no public declaration or external callers. Keep both its
    # forward declaration and definition local to the Objective-C translation unit.
    old = "\nint _zipOpenEntry("
    new = "\nstatic int _zipOpenEntry("
    if text.count(new) == 2 and old not in text:
        return
    text = replace_exact(text, old, new, 2, "ZipArchive internal helper linkage")
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", required=True, type=Path)
    parser.add_argument("--repo-root", type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()

    upstream = args.upstream.resolve()
    repo_root = args.repo_root.resolve()
    vendor = upstream / "submodules/CueChatAutomation/MLKitVendor"
    manifest_path = vendor / "targets.json"
    if not manifest_path.is_file():
        raise SystemExit(f"ML Kit vendor manifest missing: {manifest_path}; run build_mlkit_vendor.sh first")
    target_entries = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not (vendor / "BUILD").is_file():
        raise SystemExit(f"ML Kit vendor Bazel package missing: {vendor / 'BUILD'}")

    copy_runtime_sources(repo_root, upstream)
    patch_build_dependencies(upstream, target_entries)
    patch_chat_controller(upstream)
    patch_history_list(upstream)
    patch_bubble(upstream)
    patch_ziparchive_linkage(upstream)
    print("Integrated per-chat on-device translation and consent-gated AI auto-reply source overlays.")


if __name__ == "__main__":
    main()
