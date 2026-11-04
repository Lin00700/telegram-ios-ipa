import UIKit

public enum InkSettingsPresenter {
    public static func present(accountId: Int64, peerId: Int64?, openProxy: @escaping () -> Void, recentMessages: (() -> String)? = nil) {
        let controller = InkSettingsController(accountId: accountId, peerId: peerId, openProxy: openProxy, recentMessages: recentMessages)
        let navigation = UINavigationController(rootViewController: controller)
        navigation.modalPresentationStyle = .formSheet
        guard let host = topController() else {
            return
        }
        host.present(navigation, animated: true)
    }

    private static func topController() -> UIViewController? {
        let scenes = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
        let window = scenes.flatMap { $0.windows }.first { $0.isKeyWindow }
        var controller = window?.rootViewController
        while let presented = controller?.presentedViewController {
            controller = presented
        }
        return controller
    }
}

public final class InkSettingsController: UITableViewController {
    private let accountId: Int64
    private let peerId: Int64?
    private let openProxy: () -> Void
    private let recentMessages: (() -> String)?
    private var rows: [Row] = []

    fileprivate init(accountId: Int64, peerId: Int64?, openProxy: @escaping () -> Void, recentMessages: (() -> String)?) {
        self.accountId = accountId
        self.peerId = peerId
        self.openProxy = openProxy
        self.recentMessages = recentMessages
        super.init(style: .insetGrouped)
    }

    required init?(coder: NSCoder) {
        return nil
    }

    public override func viewDidLoad() {
        super.viewDidLoad()
        title = "水墨增强"
        navigationItem.rightBarButtonItem = UIBarButtonItem(title: "关闭", style: .done, target: self, action: #selector(close))
        tableView.register(UITableViewCell.self, forCellReuseIdentifier: "cell")
        reloadRows()
    }

    public override func viewWillAppear(_ animated: Bool) {
        super.viewWillAppear(animated)
        reloadRows()
        tableView.reloadData()
    }

    @objc private func close() {
        dismiss(animated: true)
    }

    private func reloadRows() {
        var next: [Row] = []
        next.append(Row(title: "水墨主题", detail: "默认宣纸底、墨色字、朱砂点缀。外观里仍可改别的主题。", kind: .info))
        next.append(Row(title: "自选全局背景", detail: InkPreferences.globalWallpaperEnabled ? "开" : "关", kind: .toggleGlobalWallpaper))
        next.append(Row(title: "选择全局背景图或 GIF", detail: "从相册选择，不拉伸", kind: .pickGlobal))
        if peerId != nil {
            next.append(Row(title: "本聊天背景", detail: InkPreferences.chatWallpaperEnabled ? "开" : "关", kind: .toggleChatWallpaper))
            next.append(Row(title: "选择本聊天背景图或 GIF", detail: "只覆盖当前对话", kind: .pickChat))
        }
        next.append(Row(title: "AI 接口", detail: InkPreferences.preset.title + " · " + InkPreferences.model, kind: .provider))
        next.append(Row(title: InkPreferences.hasAPIKey() ? "API Key 已保存在钥匙串" : "填写 API Key", detail: "只存在本机钥匙串", kind: .apiKey))
        next.append(Row(title: "补充提示词", detail: InkPreferences.extraPrompt.isEmpty ? "可选" : "已填写", kind: .prompt))
        next.append(Row(title: "自动回复总开关", detail: InkPreferences.autoReplyMaster ? "开" : "关", kind: .master))
        next.append(Row(title: "频率限制", detail: "间隔 \(Int(InkPreferences.minInterval)) 秒，\(Int(InkPreferences.windowSeconds / 60)) 分钟最多 \(InkPreferences.maxPerWindow) 条", kind: .rate))
        if let peerId {
            let reply = InkPreferences.autoReplyEnabled(accountId: accountId, peerId: peerId)
            next.append(Row(title: "本对话自动回复", detail: reply ? "开" : "关", kind: .chatReply))
            next.append(Row(title: "触发方式", detail: InkPreferences.trigger(accountId: accountId, peerId: peerId).title, kind: .trigger))
            next.append(Row(title: "关键词", detail: InkPreferences.keywordText(accountId: accountId, peerId: peerId).isEmpty ? "用逗号分隔" : InkPreferences.keywordText(accountId: accountId, peerId: peerId), kind: .keywords))
            let translate = InkPreferences.autoTranslateEnabled(accountId: accountId, peerId: peerId)
            next.append(Row(title: "本对话自动翻译", detail: translate ? "开" : "关", kind: .chatTranslate))
            next.append(Row(title: "总结未读或最近消息", detail: "使用当前已加载的文字", kind: .summarize))
        } else {
            next.append(Row(title: "按对话设置自动回复和翻译", detail: "打开某个聊天后，从右上角进入本页", kind: .info))
        }
        next.append(Row(title: "长按消息翻译", detail: InkPreferences.longPressTranslate ? "开" : "关", kind: .longPress))
        next.append(Row(title: "防撤回", detail: InkPreferences.antiRecall ? "开，保留原文并标注" : "关", kind: .antiRecall))
        next.append(Row(title: "不发已读回执", detail: InkPreferences.hideRead ? "开" : "关", kind: .hideRead))
        next.append(Row(title: "隐藏在线状态", detail: InkPreferences.hideOnline ? "开" : "关", kind: .hideOnline))
        next.append(Row(title: "隐藏正在输入", detail: InkPreferences.hideTyping ? "开" : "关", kind: .hideTyping))
        next.append(Row(title: "代理（SOCKS5 / MTProxy）", detail: "打开 Telegram 自带的代理页", kind: .proxy))
        next.append(Row(title: "多账号上限", detail: "本客户端为 \(InkPreferences.accountLimit) 个。服务器对普通账号可能仍有限制。", kind: .info))
        rows = next
    }

    public override func tableView(_ tableView: UITableView, numberOfRowsInSection section: Int) -> Int {
        return rows.count
    }

    public override func tableView(_ tableView: UITableView, cellForRowAt indexPath: IndexPath) -> UITableViewCell {
        let cell = tableView.dequeueReusableCell(withIdentifier: "cell", for: indexPath)
        let row = rows[indexPath.row]
        var content = cell.defaultContentConfiguration()
        content.text = row.title
        content.secondaryText = row.detail
        content.secondaryTextProperties.color = UIColor(red: 0.45, green: 0.16, blue: 0.14, alpha: 1)
        cell.contentConfiguration = content
        cell.accessoryType = row.kind == .info ? .none : .disclosureIndicator
        cell.backgroundColor = UIColor(red: 0.97, green: 0.95, blue: 0.91, alpha: 1)
        return cell
    }

    public override func tableView(_ tableView: UITableView, didSelectRowAt indexPath: IndexPath) {
        tableView.deselectRow(at: indexPath, animated: true)
        switch rows[indexPath.row].kind {
        case .info:
            break
        case .toggleGlobalWallpaper:
            InkPreferences.globalWallpaperEnabled.toggle()
            NotificationCenter.default.post(name: InkWallpaperStore.changed, object: nil)
        case .toggleChatWallpaper:
            InkPreferences.chatWallpaperEnabled.toggle()
            NotificationCenter.default.post(name: InkWallpaperStore.changed, object: nil)
        case .pickGlobal:
            InkWallpaperPicker.shared.present(from: self, scope: "global", peerId: 0)
        case .pickChat:
            guard let peerId else { return }
            InkWallpaperPicker.shared.present(from: self, scope: "chat", peerId: peerId)
        case .provider:
            choosePreset()
        case .apiKey:
            prompt(title: "API Key", message: "密钥只写入本机钥匙串，不会进聊天记录。", secure: true) { value in
                guard let value else { return }
                if !InkPreferences.saveAPIKey(value) {
                    self.alert("没有写入钥匙串", message: "请重试。")
                }
            }
        case .prompt:
            prompt(title: "补充提示词", message: "会附加在自动回复和翻译的系统提示后面。", secure: false) { value in
                InkPreferences.extraPrompt = value ?? ""
            }
        case .master:
            InkPreferences.autoReplyMaster.toggle()
        case .rate:
            prompt(title: "最短间隔（秒）", message: "两次自动回复至少间隔这么多秒。", secure: false) { value in
                if let value, let seconds = Double(value), seconds >= 1 {
                    InkPreferences.minInterval = seconds
                }
            }
        case .chatReply:
            guard let peerId else { return }
            let enabled = !InkPreferences.autoReplyEnabled(accountId: accountId, peerId: peerId)
            if enabled && !InkPreferences.hasAPIKey() {
                alert("还没有 API Key", message: "先在上面保存钥匙串里的密钥。")
                return
            }
            InkPreferences.setAutoReplyEnabled(enabled, accountId: accountId, peerId: peerId)
        case .trigger:
            guard let peerId else { return }
            let sheet = UIAlertController(title: "触发方式", message: "只对打开了自动回复的这个对话生效。", preferredStyle: .actionSheet)
            for trigger in InkTrigger.allCases {
                sheet.addAction(UIAlertAction(title: trigger.title, style: .default) { _ in
                    InkPreferences.setTrigger(trigger, accountId: self.accountId, peerId: peerId)
                    self.reloadRows()
                    self.tableView.reloadData()
                })
            }
            sheet.addAction(UIAlertAction(title: "取消", style: .cancel))
            present(sheet, animated: true)
        case .keywords:
            guard let peerId else { return }
            prompt(title: "关键词", message: "用逗号分隔。命中其中任意一个才会回复。", secure: false) { value in
                InkPreferences.setKeywords(value ?? "", accountId: self.accountId, peerId: peerId)
            }
        case .chatTranslate:
            guard let peerId else { return }
            let enabled = !InkPreferences.autoTranslateEnabled(accountId: accountId, peerId: peerId)
            if enabled && !InkPreferences.hasAPIKey() {
                alert("还没有 API Key", message: "自动翻译会把新消息文本发给你配置的 AI。")
                return
            }
            InkPreferences.setAutoTranslateEnabled(enabled, accountId: accountId, peerId: peerId)
        case .summarize:
            summarize()
        case .longPress:
            InkPreferences.longPressTranslate.toggle()
        case .antiRecall:
            InkPreferences.antiRecall.toggle()
        case .hideRead:
            InkPreferences.hideRead.toggle()
        case .hideTyping:
            InkPreferences.hideTyping.toggle()
        case .hideOnline:
            InkPreferences.hideOnline.toggle()
        case .proxy:
            dismiss(animated: true) {
                self.openProxy()
            }
            return
        }
        reloadRows()
        tableView.reloadData()
    }

    private func choosePreset() {
        let sheet = UIAlertController(title: "AI 接口", message: "预设会填入官方兼容地址和默认模型，密钥仍在钥匙串。", preferredStyle: .actionSheet)
        for preset in InkPreset.allCases {
            sheet.addAction(UIAlertAction(title: preset.title, style: .default) { _ in
                if preset == .custom {
                    self.prompt(title: "Base URL", message: "OpenAI 兼容的 HTTPS 地址，例如 https://example.com/v1", secure: false) { value in
                        guard let value, InkPreferences.isHTTPS(value) else {
                            self.alert("地址无效", message: "必须是 https。")
                            return
                        }
                        InkPreferences.applyPreset(.custom)
                        InkPreferences.baseURL = value
                        self.prompt(title: "模型名", message: "服务商要求的 model id。", secure: false) { model in
                            InkPreferences.model = model ?? ""
                            self.reloadRows()
                            self.tableView.reloadData()
                        }
                    }
                } else {
                    InkPreferences.applyPreset(preset)
                    self.reloadRows()
                    self.tableView.reloadData()
                }
            })
        }
        sheet.addAction(UIAlertAction(title: "取消", style: .cancel))
        present(sheet, animated: true)
    }

    private func summarize() {
        guard let recentMessages else {
            alert("请从聊天里打开", message: "在对话右上角进入水墨增强，再总结这个对话里已经加载的消息。")
            return
        }
        let transcript = recentMessages()
        guard !transcript.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            alert("没有可总结的文字", message: "当前已加载的消息里没有文本。")
            return
        }
        InkAIClient.summarize(String(transcript.prefix(12000))) { text in
            DispatchQueue.main.async {
                self.alert("总结", message: text ?? "总结失败。请检查密钥、模型和网络。")
            }
        }
    }

    private func prompt(title: String, message: String, secure: Bool, completion: @escaping (String?) -> Void) {
        let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
        alert.addTextField { field in
            field.isSecureTextEntry = secure
            field.autocapitalizationType = .none
            field.autocorrectionType = .no
        }
        alert.addAction(UIAlertAction(title: "取消", style: .cancel) { _ in completion(nil) })
        alert.addAction(UIAlertAction(title: "保存", style: .default) { _ in
            completion(alert.textFields?.first?.text)
        })
        present(alert, animated: true)
    }

    private func alert(_ title: String, message: String) {
        let alert = UIAlertController(title: title, message: message, preferredStyle: .alert)
        alert.addAction(UIAlertAction(title: "好", style: .default))
        present(alert, animated: true)
    }
}

private struct Row {
    enum Kind {
        case info
        case toggleGlobalWallpaper
        case toggleChatWallpaper
        case pickGlobal
        case pickChat
        case provider
        case apiKey
        case prompt
        case master
        case rate
        case chatReply
        case trigger
        case keywords
        case chatTranslate
        case summarize
        case longPress
        case antiRecall
        case hideRead
        case hideTyping
        case hideOnline
        case proxy
    }

    var title: String
    var detail: String
    var kind: Kind
}
