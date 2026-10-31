import Foundation
import UIKit

public enum CueFeatureSettingsUI {
    public static func toggleTranslation(accountId: Int64, peerId: Int64, threadId: Int64?, presenter: UIViewController, onChanged: @escaping () -> Void) {
        let isEnabled = CueFeaturePreferences.isAutoTranslationEnabled(accountId: accountId, peerId: peerId, threadId: threadId)
        if isEnabled {
            CueFeaturePreferences.setAutoTranslationEnabled(false, accountId: accountId, peerId: peerId, threadId: threadId)
            CueTranslationStore.shared.removeTranslations(accountId: accountId, peerId: peerId, threadId: threadId)
            self.postTranslationSettingsChanged(accountId: accountId, peerId: peerId, threadId: threadId)
            onChanged()
            return
        }
        if CueFeaturePreferences.hasTranslationConsent(accountId: accountId, peerId: peerId, threadId: threadId) {
            CueFeaturePreferences.setAutoTranslationEnabled(true, accountId: accountId, peerId: peerId, threadId: threadId)
            self.postTranslationSettingsChanged(accountId: accountId, peerId: peerId, threadId: threadId)
            onChanged()
            return
        }

        let alert = UIAlertController(
            title: "开启本聊天自动翻译？",
            message: "只处理开启后、且应用在前台并打开此聊天时收到的新文本消息，在原文下显示简体中文译文；不会补译历史消息，也不会在 iOS 暂停应用后持续后台监听。翻译由 Google ML Kit 在本机完成，聊天正文不会上传到 Google、AI profile 或 Telegram 翻译服务。首次使用可能需要下载约 30MB 语言模型；默认只通过 Wi‑Fi 下载。\n\nTHIS SERVICE MAY CONTAIN TRANSLATIONS POWERED BY GOOGLE. GOOGLE DISCLAIMS ALL WARRANTIES RELATED TO THE TRANSLATIONS, EXPRESS OR IMPLIED, INCLUDING ANY WARRANTIES OF ACCURACY, RELIABILITY, AND ANY IMPLIED WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.",
            preferredStyle: .alert
        )
        alert.addAction(UIAlertAction(title: "取消", style: .cancel))
        alert.addAction(UIAlertAction(title: "同意并开启", style: .default, handler: { _ in
            CueFeaturePreferences.setTranslationConsent(true, accountId: accountId, peerId: peerId, threadId: threadId)
            CueFeaturePreferences.setAutoTranslationEnabled(true, accountId: accountId, peerId: peerId, threadId: threadId)
            self.postTranslationSettingsChanged(accountId: accountId, peerId: peerId, threadId: threadId)
            onChanged()
        }))
        presenter.present(alert, animated: true)
    }

    private static func postTranslationSettingsChanged(accountId: Int64, peerId: Int64, threadId: Int64?) {
        NotificationCenter.default.post(
            name: Notification.Name("CueTranslationSettingsChanged"),
            object: nil,
            userInfo: [
                "accountId": NSNumber(value: accountId),
                "peerId": NSNumber(value: peerId),
                "threadId": threadId.map(String.init) ?? "root"
            ]
        )
    }

    public static func toggleAutoReply(accountId: Int64, peerId: Int64, threadId: Int64?, presenter: UIViewController, allowAutoReply: Bool, onChanged: @escaping () -> Void) {
        guard allowAutoReply else {
            let alert = UIAlertController(title: "此聊天不支持 AI 自动回复", message: "自动回复仅适用于私聊和群组。客户端不会代表你向广播频道自动发布 AI 内容；本机聊天翻译仍可单独使用。", preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "知道了", style: .default))
            presenter.present(alert, animated: true)
            return
        }

        var options = CueFeaturePreferences.aiOptions(accountId: accountId, peerId: peerId, threadId: threadId)
        if options.autoReplyEnabled {
            options.autoReplyEnabled = false
            CueFeaturePreferences.setAIOptions(options, accountId: accountId, peerId: peerId, threadId: threadId)
            onChanged()
            return
        }

        let profiles = CueFeaturePreferences.profiles(accountId: accountId)
        let usableProfile = profiles.contains { profile in
            options.assignedProfileIDs.contains(profile.id)
                && CueFeaturePreferences.isSecureHTTPS(profile.endpoint)
                && CueFeaturePreferences.apiKey(accountId: accountId, profileId: profile.id) != nil
        }
        guard usableProfile else {
            let alert = UIAlertController(title: "尚未配置 AI 服务商", message: "请先打开“管理 AI 服务商”添加 OpenAI-compatible HTTPS 服务商，再将其分配给本聊天。翻译和自动回复是独立开关。", preferredStyle: .alert)
            alert.addAction(UIAlertAction(title: "知道了", style: .default))
            presenter.present(alert, animated: true)
            return
        }

        let enable: () -> Void = {
            var updated = CueFeaturePreferences.aiOptions(accountId: accountId, peerId: peerId, threadId: threadId)
            updated.outboundConsentAccepted = true
            updated.autoReplyEnabled = true
            CueFeaturePreferences.setAIOptions(updated, accountId: accountId, peerId: peerId, threadId: threadId)
            onChanged()
        }
        if options.outboundConsentAccepted {
            enable()
            return
        }

        let alert = UIAlertController(
            title: "开启本聊天 AI 自动回复？",
            message: "只在应用前台且此聊天打开时处理新消息。消息文本会发送到你分配的 AI 服务商；生成的回复会由你的 Telegram 账号自动发出。私聊可逐条回复；群组仅在被提及或收到针对机器人的回复时处理。不会自动向频道发布，也不会在 iOS 暂停应用后持续后台监听。你可随时关闭此开关。",
            preferredStyle: .alert
        )
        alert.addAction(UIAlertAction(title: "取消", style: .cancel))
        alert.addAction(UIAlertAction(title: "同意并开启", style: .default, handler: { _ in enable() }))
        presenter.present(alert, animated: true)
    }

    public static func presentChatFeaturesMenu(accountId: Int64, peerId: Int64, threadId: Int64?, presenter: UIViewController, allowAutoReply: Bool, onMoreOptions: @escaping () -> Void) {
        let translationEnabled = CueFeaturePreferences.isAutoTranslationEnabled(accountId: accountId, peerId: peerId, threadId: threadId)
        let aiOptions = CueFeaturePreferences.aiOptions(accountId: accountId, peerId: peerId, threadId: threadId)
        let alert = UIAlertController(title: "聊天自动化", message: "自动翻译与 AI 自动回复彼此独立；每项只应用于本聊天，并且仅在应用前台、此聊天打开时处理新消息。", preferredStyle: .actionSheet)
        alert.addAction(UIAlertAction(title: "设置全局图片/GIF聊天背景…", style: .default, handler: { _ in
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                CueGlobalWallpaperSettingsUI.present(from: presenter)
            }
        }))
        alert.addAction(UIAlertAction(title: "恢复默认水墨聊天背景", style: .default, handler: { _ in
            CueGlobalWallpaperSettingsUI.clearCurrentWallpaper()
        }))
        alert.addAction(UIAlertAction(title: translationEnabled ? "关闭本聊天自动翻译" : "开启本聊天自动翻译", style: .default, handler: { _ in
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                self.toggleTranslation(accountId: accountId, peerId: peerId, threadId: threadId, presenter: presenter, onChanged: {})
            }
        }))
        alert.addAction(UIAlertAction(title: "管理 AI 服务商…", style: .default, handler: { _ in
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                self.manageAIProviders(accountId: accountId, presenter: presenter)
            }
        }))
        if allowAutoReply {
            alert.addAction(UIAlertAction(title: aiOptions.autoReplyEnabled ? "关闭本聊天 AI 自动回复" : "开启本聊天 AI 自动回复", style: .default, handler: { _ in
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                    self.toggleAutoReply(accountId: accountId, peerId: peerId, threadId: threadId, presenter: presenter, allowAutoReply: true, onChanged: {})
                }
            }))
        } else {
            alert.addAction(UIAlertAction(title: "AI 自动回复不可用", style: .default, handler: { _ in
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                    let explanation = UIAlertController(title: "此聊天不支持 AI 自动回复", message: "自动回复仅适用于私聊和群组。客户端不会代表你向广播频道自动发布 AI 内容；本机聊天翻译仍可单独使用。", preferredStyle: .alert)
                    explanation.addAction(UIAlertAction(title: "知道了", style: .default))
                    presenter.present(explanation, animated: true)
                }
            }))
        }
        alert.addAction(UIAlertAction(title: "分配本聊天的 AI 服务商…", style: .default, handler: { _ in
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                self.manageAIProfiles(accountId: accountId, peerId: peerId, threadId: threadId, presenter: presenter)
            }
        }))
        alert.addAction(UIAlertAction(title: "更多 Telegram 聊天操作…", style: .default, handler: { _ in
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35, execute: onMoreOptions)
        }))
        alert.addAction(UIAlertAction(title: "完成", style: .cancel))
        if let popover = alert.popoverPresentationController {
            popover.sourceView = presenter.view
            popover.sourceRect = CGRect(x: presenter.view.bounds.midX, y: presenter.view.bounds.midY, width: 1.0, height: 1.0)
        }
        presenter.present(alert, animated: true)
    }

    public static func manageAIProviders(accountId: Int64, presenter: UIViewController) {
        let profiles = CueFeaturePreferences.profiles(accountId: accountId)
        let message = profiles.isEmpty
            ? "还没有添加服务商。添加只会保存 endpoint、模型和本机 Keychain 密钥，不会自动分配到任何聊天，也不会发送聊天内容。"
            : "已配置的服务商对本账号可用。添加服务商不会自动分配到聊天或开启自动回复；每个聊天仍需单独分配并明确开启。密钥仅保存在本机 Keychain。"
        let alert = UIAlertController(title: "AI 服务商", message: message, preferredStyle: .actionSheet)
        for profile in profiles {
            let keyStatus = CueFeaturePreferences.apiKey(accountId: accountId, profileId: profile.id) == nil ? "缺少密钥" : "Keychain 已保存"
            let title = "\(profile.name) · \(profile.model)（\(keyStatus)）"
            alert.addAction(UIAlertAction(title: title, style: .default, handler: { _ in
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                    self.showAIProviderDetails(profile, accountId: accountId, presenter: presenter)
                }
            }))
        }
        alert.addAction(UIAlertAction(title: "添加 AI 服务商…", style: .default, handler: { _ in
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                self.promptForProfileName(accountId: accountId, peerId: 0, threadId: nil, presenter: presenter, assignToChat: false)
            }
        }))
        alert.addAction(UIAlertAction(title: "完成", style: .cancel))
        if let popover = alert.popoverPresentationController {
            popover.sourceView = presenter.view
            popover.sourceRect = CGRect(x: presenter.view.bounds.midX, y: presenter.view.bounds.midY, width: 1.0, height: 1.0)
        }
        presenter.present(alert, animated: true)
    }

    private static func showAIProviderDetails(_ profile: CueAIProfile, accountId: Int64, presenter: UIViewController) {
        let hasKey = CueFeaturePreferences.apiKey(accountId: accountId, profileId: profile.id) != nil
        let message = "服务类型：OpenAI-compatible HTTPS\nEndpoint：\(profile.endpoint)\n模型：\(profile.model)\n密钥：\(hasKey ? "已存于本机 Keychain" : "尚未配置")\n\n服务商只在被分配且聊天单独开启自动回复后才会处理消息。"
        let alert = UIAlertController(title: profile.name, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "删除服务商…", style: .destructive, handler: { _ in
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                self.confirmDeleteAIProvider(profile, accountId: accountId, presenter: presenter)
            }
        }))
        alert.addAction(UIAlertAction(title: "完成", style: .cancel, handler: { _ in
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                self.manageAIProviders(accountId: accountId, presenter: presenter)
            }
        }))
        presenter.present(alert, animated: true)
    }

    private static func confirmDeleteAIProvider(_ profile: CueAIProfile, accountId: Int64, presenter: UIViewController) {
        let alert = UIAlertController(title: "删除 AI 服务商？", message: "将从此设备删除服务商设置和对应的 Keychain 密钥。此操作不会发送或删除 Telegram 消息。", preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "取消", style: .cancel, handler: { _ in
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                self.manageAIProviders(accountId: accountId, presenter: presenter)
            }
        }))
        alert.addAction(UIAlertAction(title: "删除", style: .destructive, handler: { _ in
            guard CueFeaturePreferences.deleteAPIKey(accountId: accountId, profileId: profile.id) else {
                self.showError("无法从本机 Keychain 删除密钥。", presenter: presenter) {
                    self.manageAIProviders(accountId: accountId, presenter: presenter)
                }
                return
            }
            let profiles = CueFeaturePreferences.profiles(accountId: accountId).filter { $0.id != profile.id }
            CueFeaturePreferences.setProfiles(profiles, accountId: accountId)
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                self.manageAIProviders(accountId: accountId, presenter: presenter)
            }
        }))
        presenter.present(alert, animated: true)
    }

    public static func manageAIProfiles(accountId: Int64, peerId: Int64, threadId: Int64?, presenter: UIViewController) {
        self.showProfileAssignments(accountId: accountId, peerId: peerId, threadId: threadId, presenter: presenter)
    }

    private static func showProfileAssignments(accountId: Int64, peerId: Int64, threadId: Int64?, presenter: UIViewController) {
        let profiles = CueFeaturePreferences.profiles(accountId: accountId)
        let options = CueFeaturePreferences.aiOptions(accountId: accountId, peerId: peerId, threadId: threadId)
        let alert = UIAlertController(
            title: "本聊天的 AI 服务商",
            message: "点按可分配/取消分配已添加的服务商，可选择多个。此操作不会开启自动回复；需要另行明确开启本聊天的 AI 自动回复。",
            preferredStyle: .alert
        )
        for profile in profiles {
            let isAssigned = options.assignedProfileIDs.contains(profile.id)
            let title = "\(isAssigned ? "✓ " : "")\(profile.name) · \(profile.model)"
            alert.addAction(UIAlertAction(title: title, style: .default, handler: { _ in
                var updated = CueFeaturePreferences.aiOptions(accountId: accountId, peerId: peerId, threadId: threadId)
                if let index = updated.assignedProfileIDs.firstIndex(of: profile.id) {
                    updated.assignedProfileIDs.remove(at: index)
                } else {
                    updated.assignedProfileIDs.append(profile.id)
                }
                CueFeaturePreferences.setAIOptions(updated, accountId: accountId, peerId: peerId, threadId: threadId)
                DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                    self.showProfileAssignments(accountId: accountId, peerId: peerId, threadId: threadId, presenter: presenter)
                }
            }))
        }
        alert.addAction(UIAlertAction(title: "前往 AI 服务商管理…", style: .default, handler: { _ in
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                self.manageAIProviders(accountId: accountId, presenter: presenter)
            }
        }))
        alert.addAction(UIAlertAction(title: "完成", style: .cancel))
        presenter.present(alert, animated: true)
    }

    private static func returnToProviderDestination(accountId: Int64, peerId: Int64, threadId: Int64?, presenter: UIViewController, assignToChat: Bool) {
        if assignToChat {
            self.showProfileAssignments(accountId: accountId, peerId: peerId, threadId: threadId, presenter: presenter)
        } else {
            self.manageAIProviders(accountId: accountId, presenter: presenter)
        }
    }

    private static func promptForProfileName(accountId: Int64, peerId: Int64, threadId: Int64?, presenter: UIViewController, assignToChat: Bool) {
        self.prompt(title: "添加 AI 服务商", message: "输入便于识别的服务商名称。", secure: false, presenter: presenter) { name in
            guard let name, !name.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                self.returnToProviderDestination(accountId: accountId, peerId: peerId, threadId: threadId, presenter: presenter, assignToChat: assignToChat)
                return
            }
            self.promptForEndpoint(name: name, accountId: accountId, peerId: peerId, threadId: threadId, presenter: presenter, assignToChat: assignToChat)
        }
    }

    private static func promptForEndpoint(name: String, accountId: Int64, peerId: Int64, threadId: Int64?, presenter: UIViewController, assignToChat: Bool) {
        self.prompt(title: "服务商 API endpoint", message: "填写 OpenAI-compatible HTTPS base URL，例如 https://api.example.com/v1。", secure: false, presenter: presenter) { endpoint in
            guard let endpoint, CueFeaturePreferences.isSecureHTTPS(endpoint) else {
                self.showError("Endpoint 必须是有效的 HTTPS URL。", presenter: presenter) {
                    self.promptForEndpoint(name: name, accountId: accountId, peerId: peerId, threadId: threadId, presenter: presenter, assignToChat: assignToChat)
                }
                return
            }
            self.promptForModel(name: name, endpoint: endpoint, accountId: accountId, peerId: peerId, threadId: threadId, presenter: presenter, assignToChat: assignToChat)
        }
    }

    private static func promptForModel(name: String, endpoint: String, accountId: Int64, peerId: Int64, threadId: Int64?, presenter: UIViewController, assignToChat: Bool) {
        self.prompt(title: "模型名称", message: "输入该服务商支持的 model ID。", secure: false, presenter: presenter) { model in
            guard let model, !model.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
                self.showError("模型名称不能为空。", presenter: presenter) {
                    self.promptForModel(name: name, endpoint: endpoint, accountId: accountId, peerId: peerId, threadId: threadId, presenter: presenter, assignToChat: assignToChat)
                }
                return
            }
            self.promptForAPIKey(name: name, endpoint: endpoint, model: model, accountId: accountId, peerId: peerId, threadId: threadId, presenter: presenter, assignToChat: assignToChat)
        }
    }

    private static func promptForAPIKey(name: String, endpoint: String, model: String, accountId: Int64, peerId: Int64, threadId: Int64?, presenter: UIViewController, assignToChat: Bool) {
        self.prompt(title: "服务商 API key", message: "密钥使用安全输入并只保存到此设备的 Keychain；添加后不会自动分配或开启聊天回复。", secure: true, presenter: presenter) { apiKey in
            guard let apiKey, !apiKey.isEmpty else {
                self.returnToProviderDestination(accountId: accountId, peerId: peerId, threadId: threadId, presenter: presenter, assignToChat: assignToChat)
                return
            }
            let profile = CueAIProfile(name: String(name.prefix(80)), endpoint: endpoint, model: String(model.prefix(160)))
            guard CueFeaturePreferences.saveAPIKey(apiKey, accountId: accountId, profileId: profile.id) else {
                self.showError("无法保存 API key 到 Keychain。", presenter: presenter) {
                    self.returnToProviderDestination(accountId: accountId, peerId: peerId, threadId: threadId, presenter: presenter, assignToChat: assignToChat)
                }
                return
            }
            var profiles = CueFeaturePreferences.profiles(accountId: accountId)
            profiles.append(profile)
            CueFeaturePreferences.setProfiles(profiles, accountId: accountId)
            if assignToChat {
                var options = CueFeaturePreferences.aiOptions(accountId: accountId, peerId: peerId, threadId: threadId)
                options.assignedProfileIDs.append(profile.id)
                CueFeaturePreferences.setAIOptions(options, accountId: accountId, peerId: peerId, threadId: threadId)
            }
            self.returnToProviderDestination(accountId: accountId, peerId: peerId, threadId: threadId, presenter: presenter, assignToChat: assignToChat)
        }
    }

    private static func prompt(title: String, message: String, secure: Bool, presenter: UIViewController, completion: @escaping (String?) -> Void) {
        let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
        let completeAfterDismissal: (String?) -> Void = { value in
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) {
                completion(value)
            }
        }
        alert.addTextField { field in
            field.isSecureTextEntry = secure
            field.autocapitalizationType = .none
            field.autocorrectionType = .no
        }
        alert.addAction(UIAlertAction(title: "取消", style: .cancel, handler: { _ in completeAfterDismissal(nil) }))
        alert.addAction(UIAlertAction(title: "继续", style: .default, handler: { _ in completeAfterDismissal(alert.textFields?.first?.text) }))
        presenter.present(alert, animated: true)
    }

    private static func showError(_ message: String, presenter: UIViewController, retry: @escaping () -> Void) {
        let alert = UIAlertController(title: "无法保存", message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "返回", style: .cancel, handler: { _ in
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35, execute: retry)
        }))
        presenter.present(alert, animated: true)
    }
}
