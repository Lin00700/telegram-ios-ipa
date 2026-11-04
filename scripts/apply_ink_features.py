#!/usr/bin/env python3
"""Install the 水墨增强 module and the small Telegram hooks it needs.

Every edit is an exact string match. If upstream moves, the build stops
instead of shipping a half-applied client.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path


def replace_exact(text: str, old: str, new: str, expected: int, label: str) -> str:
    count = text.count(old)
    if count != expected:
        raise RuntimeError(f"{label}: expected {expected} match(es), found {count}")
    return text.replace(old, new, expected)


def patch_file(path: Path, old: str, new: str, expected: int, label: str) -> None:
    text = path.read_text(encoding="utf-8")
    if new in text and old not in text:
        return
    path.write_text(replace_exact(text, old, new, expected, label), encoding="utf-8")


def install_module(repo_root: Path, upstream: Path) -> None:
    destination = upstream / "submodules/InkEnhance/Sources"
    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    for source in sorted((repo_root / "ink/Sources").glob("*.swift")):
        shutil.copy2(source, destination / source.name)
    retain = upstream / "submodules/TelegramCore/Sources/InkRetainDeletedMessages.swift"
    shutil.copy2(repo_root / "ink/core/InkRetainDeletedMessages.swift", retain)
    build = '''load("@build_bazel_rules_swift//swift:swift.bzl", "swift_library")

swift_library(
    name = "InkEnhance",
    module_name = "InkEnhance",
    srcs = glob(["Sources/**/*.swift"]),
    copts = [
        "-warnings-as-errors",
    ],
    visibility = ["//visibility:public"],
)
'''
    (upstream / "submodules/InkEnhance/BUILD").write_text(build, encoding="utf-8")


def patch_dependencies(upstream: Path) -> None:
    patch_file(
        upstream / "submodules/TelegramUI/BUILD",
        '        "//submodules/TelegramUIPreferences:TelegramUIPreferences",\n',
        '        "//submodules/TelegramUIPreferences:TelegramUIPreferences",\n        "//submodules/InkEnhance:InkEnhance",\n',
        1,
        "TelegramUI InkEnhance dependency",
    )
    patch_file(
        upstream / "submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/BUILD",
        '        "//submodules/AccountContext",\n',
        '        "//submodules/AccountContext",\n        "//submodules/InkEnhance:InkEnhance",\n',
        1,
        "PeerInfoScreen InkEnhance dependency",
    )
    patch_file(
        upstream / "submodules/TelegramUI/Components/Chat/ChatMessageTextBubbleContentNode/BUILD",
        '        "//submodules/TelegramCore",\n',
        '        "//submodules/TelegramCore",\n        "//submodules/InkEnhance:InkEnhance",\n',
        1,
        "bubble InkEnhance dependency",
    )


def patch_behavior(upstream: Path) -> None:
    patch_file(
        upstream / "submodules/AccountUtils/Sources/AccountUtils.swift",
        "public let maximumNumberOfAccounts = 3\n",
        "public let maximumNumberOfAccounts = 10\n",
        1,
        "account limit",
    )
    patch_file(
        upstream / "submodules/TelegramCore/Sources/State/ManagedAccountPresence.swift",
        "        if isOnline {\n",
        '        if UserDefaults.standard.bool(forKey: "ink.stealth.hideOnline") ? false : isOnline {\n',
        1,
        "hide online status",
    )
    patch_file(
        upstream / "submodules/TelegramCore/Sources/State/ManagedLocalInputActivities.swift",
        "    return postbox.transaction { transaction -> Signal<Void, NoError> in\n        if let peer = transaction.getPeer(peerId) {\n",
        "    return postbox.transaction { transaction -> Signal<Void, NoError> in\n"
        '        if UserDefaults.standard.bool(forKey: "ink.stealth.hideTyping") {\n'
        "            return .complete()\n"
        "        }\n"
        "        if let peer = transaction.getPeer(peerId) {\n",
        1,
        "hide typing",
    )
    patch_file(
        upstream / "submodules/TelegramCore/Sources/State/SynchronizePeerReadState.swift",
        "private func pushPeerReadState(network: Network, postbox: Postbox, stateManager: AccountStateManager, peerId: PeerId, readState: PeerReadState) -> Signal<PeerReadState, PeerReadStateValidationError> {\n"
        "    if peerId.namespace == Namespaces.Peer.SecretChat {\n",
        "private func pushPeerReadState(network: Network, postbox: Postbox, stateManager: AccountStateManager, peerId: PeerId, readState: PeerReadState) -> Signal<PeerReadState, PeerReadStateValidationError> {\n"
        '    if UserDefaults.standard.bool(forKey: "ink.stealth.hideRead") {\n'
        "        return .single(readState)\n"
        "    }\n"
        "    if peerId.namespace == Namespaces.Peer.SecretChat {\n",
        1,
        "suppress read receipts",
    )
    delete_old = """            case let .DeleteMessagesWithGlobalIds(ids):
                var resourceIds: [MediaResourceId] = []
                transaction.deleteMessagesWithGlobalIds(ids, forEachMedia: { media in
                    addMessageMediaResourceIdsToRemove(media: media, resourceIds: &resourceIds)
                })
                if !resourceIds.isEmpty {
                    let _ = mediaBox.removeCachedResources(Array(Set(resourceIds)), force: true).start()
                }
                deletedMessageIds.append(contentsOf: ids.map { .global($0) })
            case let .DeleteMessages(ids):
                _internal_deleteMessages(transaction: transaction, mediaBox: mediaBox, ids: ids, manualAddMessageThreadStatsDifference: { id, add, remove in
                    addMessageThreadStatsDifference(threadKey: id, remove: remove, addedMessagePeer: nil, addedMessageId: nil, isOutgoing: false)
                })
                deletedMessageIds.append(contentsOf: ids.map { .messageId($0) })
"""
    delete_new = """            case let .DeleteMessagesWithGlobalIds(ids):
                if inkAntiRecallEnabled() {
                    for messageId in transaction.messageIdsForGlobalIds(ids) {
                        inkRememberRecalledMessage(transaction: transaction, id: messageId)
                    }
                } else {
                    var resourceIds: [MediaResourceId] = []
                    transaction.deleteMessagesWithGlobalIds(ids, forEachMedia: { media in
                        addMessageMediaResourceIdsToRemove(media: media, resourceIds: &resourceIds)
                    })
                    if !resourceIds.isEmpty {
                        let _ = mediaBox.removeCachedResources(Array(Set(resourceIds)), force: true).start()
                    }
                    deletedMessageIds.append(contentsOf: ids.map { .global($0) })
                }
            case let .DeleteMessages(ids):
                if inkAntiRecallEnabled() {
                    for messageId in ids {
                        inkRememberRecalledMessage(transaction: transaction, id: messageId)
                    }
                } else {
                    _internal_deleteMessages(transaction: transaction, mediaBox: mediaBox, ids: ids, manualAddMessageThreadStatsDifference: { id, add, remove in
                        addMessageThreadStatsDifference(threadKey: id, remove: remove, addedMessagePeer: nil, addedMessageId: nil, isOutgoing: false)
                    })
                    deletedMessageIds.append(contentsOf: ids.map { .messageId($0) })
                }
"""
    patch_file(
        upstream / "submodules/TelegramCore/Sources/State/AccountStateManagementUtils.swift",
        delete_old,
        delete_new,
        1,
        "retain revoked messages",
    )
    patch_file(
        upstream / "submodules/TelegramCore/Sources/State/AccountStateManagementUtils.swift",
        "            case let .EditMessage(id, message):\n                var generatedEvent:",
        "            case let .EditMessage(id, message):\n"
        "                if inkAntiRecallEnabled() {\n"
        "                    inkRememberPreEditText(transaction: transaction, id: id, updated: message)\n"
        "                }\n"
        "                var generatedEvent:",
        1,
        "remember pre-edit text",
    )


HISTORY_HELPERS = r'''    func inkRecentMessageText(limit: Int = 40) -> String {
        let messages = self.previousView.with { value in
            value?.0.originalView.entries.map { $0.message } ?? []
        }
        return messages.suffix(limit).compactMap { message -> String? in
            let text = message.text.trimmingCharacters(in: .whitespacesAndNewlines)
            return text.isEmpty ? nil : text
        }.joined(separator: "\n")
    }

    private func inkMarkSeen(_ key: String, id: String) -> Bool {
        var seen = UserDefaults.standard.stringArray(forKey: key) ?? []
        if seen.contains(id) {
            return false
        }
        seen.append(id)
        if seen.count > 400 {
            seen.removeFirst(seen.count - 400)
        }
        UserDefaults.standard.set(seen, forKey: key)
        return true
    }

    private func inkClaimReplySlot(accountId: Int64, peerId: Int64) -> Bool {
        let key = "ink.autoReply.history.\(accountId).\(peerId)"
        let now = Date().timeIntervalSince1970
        let stored = UserDefaults.standard.array(forKey: key) as? [Double] ?? []
        let decision = InkRateLimit.allow(
            now: now,
            history: stored,
            minInterval: InkPreferences.minInterval,
            maxCount: InkPreferences.maxPerWindow,
            window: InkPreferences.windowSeconds
        )
        guard decision.allowed else {
            return false
        }
        UserDefaults.standard.set(decision.history, forKey: key)
        return true
    }

    private func inkEntityMention(_ message: Message) -> Bool {
        let accountPeerId = self.context.account.peerId
        return message.attributes
            .compactMap { $0 as? TextEntitiesMessageAttribute }
            .flatMap { $0.entities }
            .contains { entity in
                if case let .TextMention(peerId) = entity.type {
                    return peerId == accountPeerId
                }
                return false
            }
    }

    private func inkResolveMention(_ message: Message, completion: @escaping (Bool) -> Void) {
        if inkEntityMention(message) {
            completion(true)
            return
        }
        let accountPeerId = self.context.account.peerId
        let _ = (self.context.account.postbox.peerView(id: accountPeerId)
        |> take(1)
        |> deliverOnMainQueue).startStrict(next: { view in
            guard let user = view.peers[accountPeerId] as? TelegramUser else {
                completion(false)
                return
            }
            var names = user.usernames.map { $0.username.lowercased() }
            if let username = user.username {
                names.append(username.lowercased())
            }
            let lower = message.text.lowercased()
            completion(names.contains { !$0.isEmpty && lower.contains("@" + $0) })
        })
    }

    private func inkHandleNewMessage(_ message: Message, peerId: PeerId) {
        let accountId = self.context.account.peerId.toInt64()
        let chatId = peerId.toInt64()
        let id = "\(message.id.namespace):\(message.id.id)"
        guard inkMarkSeen("ink.seen.\(accountId).\(chatId)", id: id) else {
            return
        }
        let isOutgoing = message.flags.intersection(.IsIncomingMask).isEmpty
        let isBot = (message.author as? TelegramUser)?.botInfo != nil
        if !isOutgoing, InkPreferences.autoTranslateEnabled(accountId: accountId, peerId: chatId), !message.text.isEmpty {
            let namespace = message.id.namespace
            let messageId = message.id.id
            InkAIClient.translate(message.text) { [weak self] translated in
                guard let translated, let self else {
                    return
                }
                InkRetention.saveTranslation(peerId: chatId, namespace: namespace, messageId: messageId, text: translated)
                Queue.mainQueue().async {
                    self.controllerInteraction.requestMessageUpdate(message.id, false, nil)
                }
            }
        }
        let trigger = InkPreferences.trigger(accountId: accountId, peerId: chatId)
        let start: (Bool) -> Void = { [weak self] mentioned in
            guard let self else {
                return
            }
            guard InkAutoReplyPolicy.shouldReply(
                master: InkPreferences.autoReplyMaster,
                chatEnabled: InkPreferences.autoReplyEnabled(accountId: accountId, peerId: chatId),
                trigger: trigger,
                text: message.text,
                mentioned: mentioned,
                isBot: isBot,
                isOutgoing: isOutgoing,
                keywords: InkPreferences.keywords(accountId: accountId, peerId: chatId)
            ) else {
                return
            }
            guard self.controllerInteraction.canSendMessages(), self.inkClaimReplySlot(accountId: accountId, peerId: chatId) else {
                return
            }
            InkAIClient.reply(to: message.text) { [weak self] reply in
                Queue.mainQueue().async {
                    guard let self, let reply, !reply.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                        return
                    }
                    guard InkPreferences.autoReplyMaster,
                          InkPreferences.autoReplyEnabled(accountId: accountId, peerId: chatId),
                          self.controllerInteraction.canSendMessages() else {
                        return
                    }
                    self.controllerInteraction.sendMessage(reply, message.id)
                }
            }
        }
        if trigger != .mention || inkEntityMention(message) {
            start(inkEntityMention(message) || trigger != .mention)
        } else {
            inkResolveMention(message, completion: start)
        }
    }

'''

HISTORY_HOOK_OLD = """                if let strongSelf = self {
                    if let recommendedChannels, !recommendedChannels.channels.isEmpty && !recommendedChannels.isHidden {
"""

HISTORY_HOOK_NEW = """                if case .InteractiveChanges = reason, let strongSelf = self, let previous = previous {
                    let inkPeerId: PeerId?
                    switch chatLocation {
                    case let .peer(peerId):
                        inkPeerId = peerId
                    case let .replyThread(messageId):
                        inkPeerId = messageId.peerId
                    default:
                        inkPeerId = nil
                    }
                    if let inkPeerId {
                        let previousIds = Set(previous.originalView.entries.map { $0.message.id })
                        let now = Int32(Date().timeIntervalSince1970)
                        for entry in view.entries where !previousIds.contains(entry.message.id) && abs(entry.message.timestamp - now) <= 180 {
                            strongSelf.inkHandleNewMessage(entry.message, peerId: inkPeerId)
                        }
                    }
                }

                if let strongSelf = self {
                    if let recommendedChannels, !recommendedChannels.channels.isEmpty && !recommendedChannels.isHidden {
"""


def patch_history(upstream: Path) -> None:
    path = upstream / "submodules/TelegramUI/Sources/ChatHistoryListNode.swift"
    text = path.read_text(encoding="utf-8")
    text = replace_exact(text, "import TelegramCore\n", "import TelegramCore\nimport InkEnhance\n", 1, "history import")
    text = replace_exact(
        text,
        "    private func beginChatHistoryTransitions(resetScrolling: Bool, switchedToAnotherSource: Bool) {\n",
        HISTORY_HELPERS + "    private func beginChatHistoryTransitions(resetScrolling: Bool, switchedToAnotherSource: Bool) {\n",
        1,
        "history helpers",
    )
    text = replace_exact(text, HISTORY_HOOK_OLD, HISTORY_HOOK_NEW, 1, "history incoming hook")
    path.write_text(text, encoding="utf-8")


MORE_OLD = """        self.moreBarButton.contextAction = { [weak self] sourceNode, gesture in
            guard let self else {
                return
            }
            guard let peerId = self.chatLocation.peerId else {
                return
            }
            
            if peerId == self.context.account.peerId {
                PeerInfoScreenImpl.openSavedMessagesMoreMenu(context: self.context, sourceController: self, isViewingAsTopics: false, sourceView: self.navigationBar?.navigationButtonContextContainer(sourceView: sourceNode.view) ?? sourceNode.view, gesture: gesture)
            } else if peerId.namespace == Namespaces.Peer.CloudUser {
                self.openBotForumMoreMenu(sourceView: self.navigationBar?.navigationButtonContextContainer(sourceView: sourceNode.view) ?? sourceNode.view, gesture: gesture)
            } else {
                ChatListControllerImpl.openMoreMenu(context: self.context, peerId: peerId, sourceController: self, isViewingAsTopics: false, sourceView: sourceNode.view, gesture: gesture)
            }
        }
"""

MORE_NEW = """        self.moreBarButton.contextAction = { [weak self] sourceNode, gesture in
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
            let sheet = UIAlertController(title: "水墨增强", message: nil, preferredStyle: .actionSheet)
            sheet.addAction(UIAlertAction(title: "打开水墨增强", style: .default, handler: { [weak self] _ in
                guard let self else {
                    return
                }
                InkSettingsPresenter.present(
                    accountId: self.context.account.peerId.toInt64(),
                    peerId: peerId.toInt64(),
                    openProxy: { [weak self] in
                        guard let self else {
                            return
                        }
                        self.push(proxySettingsController(context: self.context))
                    },
                    recentMessages: { [weak self] in
                        self?.chatDisplayNode.historyNode.inkRecentMessageText() ?? ""
                    }
                )
            }))
            sheet.addAction(UIAlertAction(title: "更多聊天操作", style: .default, handler: { _ in
                openTelegramMenu()
            }))
            sheet.addAction(UIAlertAction(title: "取消", style: .cancel))
            if let popover = sheet.popoverPresentationController {
                popover.sourceView = sourceView
                popover.sourceRect = sourceView.bounds
            }
            self.present(sheet, animated: true)
        }
"""


def patch_chat_controller(upstream: Path) -> None:
    path = upstream / "submodules/TelegramUI/Sources/ChatController.swift"
    text = path.read_text(encoding="utf-8")
    text = replace_exact(text, "import TelegramCore\n", "import TelegramCore\nimport InkEnhance\n", 1, "chat controller import")
    text = replace_exact(text, MORE_OLD, MORE_NEW, 1, "chat more menu")
    text = replace_exact(
        text,
        "    override public func viewWillAppear(_ animated: Bool) {\n        super.viewWillAppear(animated)\n",
        "    override public func viewWillAppear(_ animated: Bool) {\n        super.viewWillAppear(animated)\n        InkPreferences.noteActivePeer(self.chatLocation.peerId?.toInt64())\n",
        1,
        "active wallpaper peer",
    )
    text = replace_exact(
        text,
        "    override public func viewWillDisappear(_ animated: Bool) {\n        super.viewWillDisappear(animated)\n",
        "    override public func viewWillDisappear(_ animated: Bool) {\n        super.viewWillDisappear(animated)\n        InkPreferences.noteActivePeer(nil)\n",
        1,
        "clear wallpaper peer",
    )
    path.write_text(text, encoding="utf-8")


BUBBLE_ANCHOR = """                } else {
                    attributedText = NSAttributedString(string: " ", font: textFont, textColor: messageTheme.primaryTextColor)
                }
                
                // The custom-emoji attribute is not re-applied here: `stringWithAppliedEntities`
"""

BUBBLE_INSERT = """                } else {
                    attributedText = NSAttributedString(string: " ", font: textFont, textColor: messageTheme.primaryTextColor)
                }
                let inkPeerId = item.message.id.peerId.toInt64()
                let inkNamespace = item.message.id.namespace
                let inkMessageId = item.message.id.id
                if let note = InkRetention.note(peerId: inkPeerId, namespace: inkNamespace, messageId: inkMessageId) {
                    let combined = NSMutableAttributedString(attributedString: attributedText)
                    let noteFont = Font.regular(max(12.0, textFont.pointSize - 1.0))
                    if note.recalled {
                        combined.append(NSAttributedString(string: "\\n【已撤回】", font: Font.semibold(max(12.0, textFont.pointSize - 1.0)), textColor: UIColor(rgb: 0xA33B32)))
                    }
                    if let previous = note.previousText, !previous.isEmpty {
                        combined.append(NSAttributedString(string: "\\n【编辑前】" + previous, font: noteFont, textColor: messageTheme.primaryTextColor.withMultipliedAlpha(0.72)))
                    }
                    attributedText = combined
                }
                if let translated = InkRetention.translation(peerId: inkPeerId, namespace: inkNamespace, messageId: inkMessageId),
                   InkPreferences.autoTranslateEnabled(accountId: item.context.account.peerId.toInt64(), peerId: inkPeerId) {
                    let combined = NSMutableAttributedString(attributedString: attributedText)
                    combined.append(NSAttributedString(string: "\\n" + translated, font: Font.regular(max(12.0, textFont.pointSize - 1.0)), textColor: messageTheme.primaryTextColor.withMultipliedAlpha(0.78)))
                    attributedText = combined
                }
                
                // The custom-emoji attribute is not re-applied here: `stringWithAppliedEntities`
"""


def patch_bubble(upstream: Path) -> None:
    path = upstream / "submodules/TelegramUI/Components/Chat/ChatMessageTextBubbleContentNode/Sources/ChatMessageTextBubbleContentNode.swift"
    text = path.read_text(encoding="utf-8")
    text = replace_exact(text, "import TelegramCore\n", "import TelegramCore\nimport InkEnhance\n", 1, "bubble import")
    text = replace_exact(
        text,
        "                let attributedText: NSAttributedString\n",
        "                var attributedText: NSAttributedString\n",
        1,
        "mutable bubble text",
    )
    text = replace_exact(text, BUBBLE_ANCHOR, BUBBLE_INSERT, 1, "bubble annotations")
    path.write_text(text, encoding="utf-8")


TRANSLATE_OLD = """                    if !isCopyProtected {
                        actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.Conversation_ContextMenuCopy, icon: { theme in
                            return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Copy"), color: theme.actionSheet.primaryTextColor)
"""

TRANSLATE_NEW = """                    if !isCopyProtected {
                        if (UserDefaults.standard.object(forKey: "ink.translate.longPress") as? Bool ?? true) && !messageText.isEmpty {
                            let inkSource = messageText
                            actions.append(.action(ContextMenuActionItem(text: "翻译", icon: { theme in
                                return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Copy"), color: theme.actionSheet.primaryTextColor)
                            }, action: { _, f in
                                InkAIClient.translate(inkSource) { translated in
                                    Queue.mainQueue().async {
                                        let alert = UIAlertController(title: "译文", message: translated ?? "翻译失败。请先在「水墨增强」里保存 API Key。", preferredStyle: .alert)
                                        alert.addAction(UIAlertAction(title: "关闭", style: .cancel))
                                        let scenes = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
                                        let root = scenes.flatMap { $0.windows }.first { $0.isKeyWindow }?.rootViewController
                                        var top = root
                                        while let presented = top?.presentedViewController {
                                            top = presented
                                        }
                                        top?.present(alert, animated: true)
                                    }
                                }
                                f(.default)
                            })))
                        }
                        actions.append(.action(ContextMenuActionItem(text: chatPresentationInterfaceState.strings.Conversation_ContextMenuCopy, icon: { theme in
                            return generateTintedImage(image: UIImage(bundleImageName: "Chat/Context Menu/Copy"), color: theme.actionSheet.primaryTextColor)
"""


def patch_context_menu(upstream: Path) -> None:
    path = upstream / "submodules/TelegramUI/Sources/ChatInterfaceStateContextMenus.swift"
    text = path.read_text(encoding="utf-8")
    text = replace_exact(text, "import TelegramCore\n", "import TelegramCore\nimport InkEnhance\n", 1, "context menu import")
    text = replace_exact(text, TRANSLATE_OLD, TRANSLATE_NEW, 1, "long-press translate")
    path.write_text(text, encoding="utf-8")


def patch_settings_entry(upstream: Path) -> None:
    path = upstream / "submodules/TelegramUI/Components/PeerInfo/PeerInfoScreen/Sources/PeerInfoSettingsItems.swift"
    text = path.read_text(encoding="utf-8")
    text = replace_exact(text, "import WalletContext\n", "import WalletContext\nimport InkEnhance\n", 1, "settings import")
    anchor = "    let premiumConfiguration = PremiumConfiguration.with(appConfiguration: context.currentAppConfiguration.with { $0 })\n"
    addition = """    items[.advanced]!.append(PeerInfoScreenDisclosureItem(id: 880, text: "水墨增强", icon: PresentationResourcesSettings.appearance, action: {
        InkSettingsPresenter.present(accountId: context.account.peerId.toInt64(), peerId: nil, openProxy: {
            interaction.openSettings(.proxy)
        })
    }))

"""
    text = replace_exact(text, anchor, addition + anchor, 1, "settings entry")
    path.write_text(text, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--upstream", required=True, type=Path)
    parser.add_argument("--repo-root", required=True, type=Path)
    args = parser.parse_args()
    install_module(args.repo_root, args.upstream)
    patch_dependencies(args.upstream)
    patch_behavior(args.upstream)
    patch_history(args.upstream)
    patch_chat_controller(args.upstream)
    patch_bubble(args.upstream)
    patch_context_menu(args.upstream)
    patch_settings_entry(args.upstream)
    print("Installed 水墨增强: theme hooks are separate; AI, stealth, anti-recall, wallpaper peer and account limit are patched.")


if __name__ == "__main__":
    main()
