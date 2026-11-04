import Foundation
import Security

public enum InkPreset: String, CaseIterable {
    case openAI
    case deepSeek
    case gemini
    case claude
    case custom

    public var title: String {
        switch self {
        case .openAI: return "OpenAI"
        case .deepSeek: return "DeepSeek"
        case .gemini: return "Gemini"
        case .claude: return "Claude"
        case .custom: return "自定义（OpenAI 兼容）"
        }
    }

    public var defaultBaseURL: String {
        switch self {
        case .openAI: return "https://api.openai.com/v1"
        case .deepSeek: return "https://api.deepseek.com/v1"
        case .gemini: return "https://generativelanguage.googleapis.com/v1beta/openai"
        case .claude: return "https://api.anthropic.com/v1"
        case .custom: return "https://"
        }
    }

    public var defaultModel: String {
        switch self {
        case .openAI: return "gpt-4o-mini"
        case .deepSeek: return "deepseek-chat"
        case .gemini: return "gemini-2.0-flash"
        case .claude: return "claude-3-5-haiku-latest"
        case .custom: return ""
        }
    }

    public var usesAnthropicHeaders: Bool {
        return self == .claude
    }
}

public enum InkTrigger: String, CaseIterable {
    case all
    case mention
    case keyword

    public var title: String {
        switch self {
        case .all: return "该对话的每条新消息"
        case .mention: return "被 @ 时"
        case .keyword: return "命中关键词时"
        }
    }
}

public enum InkPreferences {
    public static let hideOnlineKey = "ink.stealth.hideOnline"
    public static let hideTypingKey = "ink.stealth.hideTyping"
    public static let hideReadKey = "ink.stealth.hideRead"
    public static let antiRecallKey = "ink.antiRecall.enabled"
    public static let autoReplyMasterKey = "ink.autoReply.master"
    public static let longPressTranslateKey = "ink.translate.longPress"
    public static let minIntervalKey = "ink.autoReply.minInterval"
    public static let maxPerWindowKey = "ink.autoReply.maxPerWindow"
    public static let windowSecondsKey = "ink.autoReply.windowSeconds"
    public static let presetKey = "ink.ai.preset"
    public static let baseURLKey = "ink.ai.baseURL"
    public static let modelKey = "ink.ai.model"
    public static let extraPromptKey = "ink.ai.extraPrompt"
    public static let globalWallpaperKey = "ink.wallpaper.globalEnabled"
    public static let chatWallpaperKey = "ink.wallpaper.chatEnabled"
    public static let activePeerKey = "ink.wallpaper.activePeer"
    public static let accountLimit = 10

    private static let defaults = UserDefaults.standard
    private static let keychainService = "com.lin.telegram.ink.ai"
    private static let keychainAccount = "active-provider"

    public static var preset: InkPreset {
        get { InkPreset(rawValue: defaults.string(forKey: presetKey) ?? "") ?? .openAI }
        set { defaults.set(newValue.rawValue, forKey: presetKey) }
    }

    public static var baseURL: String {
        get {
            let stored = defaults.string(forKey: baseURLKey) ?? ""
            return stored.isEmpty ? preset.defaultBaseURL : stored
        }
        set { defaults.set(newValue, forKey: baseURLKey) }
    }

    public static var model: String {
        get {
            let stored = defaults.string(forKey: modelKey) ?? ""
            return stored.isEmpty ? preset.defaultModel : stored
        }
        set { defaults.set(newValue, forKey: modelKey) }
    }

    public static var extraPrompt: String {
        get { defaults.string(forKey: extraPromptKey) ?? "" }
        set { defaults.set(newValue, forKey: extraPromptKey) }
    }

    public static var hideOnline: Bool {
        get { defaults.bool(forKey: hideOnlineKey) }
        set { defaults.set(newValue, forKey: hideOnlineKey) }
    }

    public static var hideTyping: Bool {
        get { defaults.bool(forKey: hideTypingKey) }
        set { defaults.set(newValue, forKey: hideTypingKey) }
    }

    public static var hideRead: Bool {
        get { defaults.bool(forKey: hideReadKey) }
        set { defaults.set(newValue, forKey: hideReadKey) }
    }

    public static var antiRecall: Bool {
        get { defaults.bool(forKey: antiRecallKey) }
        set { defaults.set(newValue, forKey: antiRecallKey) }
    }

    public static var autoReplyMaster: Bool {
        get { defaults.bool(forKey: autoReplyMasterKey) }
        set { defaults.set(newValue, forKey: autoReplyMasterKey) }
    }

    public static var longPressTranslate: Bool {
        get {
            if defaults.object(forKey: longPressTranslateKey) == nil {
                return true
            }
            return defaults.bool(forKey: longPressTranslateKey)
        }
        set { defaults.set(newValue, forKey: longPressTranslateKey) }
    }

    public static var globalWallpaperEnabled: Bool {
        get {
            if defaults.object(forKey: globalWallpaperKey) == nil {
                return true
            }
            return defaults.bool(forKey: globalWallpaperKey)
        }
        set { defaults.set(newValue, forKey: globalWallpaperKey) }
    }

    public static var chatWallpaperEnabled: Bool {
        get {
            if defaults.object(forKey: chatWallpaperKey) == nil {
                return true
            }
            return defaults.bool(forKey: chatWallpaperKey)
        }
        set { defaults.set(newValue, forKey: chatWallpaperKey) }
    }

    public static var minInterval: TimeInterval {
        get {
            let value = defaults.double(forKey: minIntervalKey)
            return value > 0 ? value : 8
        }
        set { defaults.set(newValue, forKey: minIntervalKey) }
    }

    public static var maxPerWindow: Int {
        get {
            let value = defaults.integer(forKey: maxPerWindowKey)
            return value > 0 ? value : 6
        }
        set { defaults.set(newValue, forKey: maxPerWindowKey) }
    }

    public static var windowSeconds: TimeInterval {
        get {
            let value = defaults.double(forKey: windowSecondsKey)
            return value > 0 ? value : 600
        }
        set { defaults.set(newValue, forKey: windowSecondsKey) }
    }

    public static func applyPreset(_ preset: InkPreset) {
        self.preset = preset
        if preset != .custom {
            baseURL = preset.defaultBaseURL
            model = preset.defaultModel
        }
    }

    public static func isHTTPS(_ value: String) -> Bool {
        guard let components = URLComponents(string: value),
              components.scheme?.lowercased() == "https",
              let host = components.host, !host.isEmpty,
              components.user == nil, components.password == nil else {
            return false
        }
        return true
    }

    private static func chatKey(_ feature: String, accountId: Int64, peerId: Int64) -> String {
        return "ink.chat.\(feature).\(accountId).\(peerId)"
    }

    public static func autoReplyEnabled(accountId: Int64, peerId: Int64) -> Bool {
        return defaults.bool(forKey: chatKey("autoReply", accountId: accountId, peerId: peerId))
    }

    public static func setAutoReplyEnabled(_ enabled: Bool, accountId: Int64, peerId: Int64) {
        defaults.set(enabled, forKey: chatKey("autoReply", accountId: accountId, peerId: peerId))
    }

    public static func autoTranslateEnabled(accountId: Int64, peerId: Int64) -> Bool {
        return defaults.bool(forKey: chatKey("autoTranslate", accountId: accountId, peerId: peerId))
    }

    public static func setAutoTranslateEnabled(_ enabled: Bool, accountId: Int64, peerId: Int64) {
        defaults.set(enabled, forKey: chatKey("autoTranslate", accountId: accountId, peerId: peerId))
    }

    public static func trigger(accountId: Int64, peerId: Int64) -> InkTrigger {
        return InkTrigger(rawValue: defaults.string(forKey: chatKey("trigger", accountId: accountId, peerId: peerId)) ?? "") ?? .mention
    }

    public static func setTrigger(_ trigger: InkTrigger, accountId: Int64, peerId: Int64) {
        defaults.set(trigger.rawValue, forKey: chatKey("trigger", accountId: accountId, peerId: peerId))
    }

    public static func keywords(accountId: Int64, peerId: Int64) -> [String] {
        let raw = defaults.string(forKey: chatKey("keywords", accountId: accountId, peerId: peerId)) ?? ""
        return raw.split(separator: ",").map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }.filter { !$0.isEmpty }
    }

    public static func setKeywords(_ value: String, accountId: Int64, peerId: Int64) {
        defaults.set(value, forKey: chatKey("keywords", accountId: accountId, peerId: peerId))
    }

    public static func keywordText(accountId: Int64, peerId: Int64) -> String {
        return defaults.string(forKey: chatKey("keywords", accountId: accountId, peerId: peerId)) ?? ""
    }

    @discardableResult
    public static func saveAPIKey(_ apiKey: String) -> Bool {
        let trimmed = apiKey.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, let data = trimmed.data(using: .utf8) else {
            return false
        }
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: keychainAccount
        ]
        let attributes: [String: Any] = [
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        ]
        let status = SecItemAdd(query.merging(attributes) { _, new in new } as CFDictionary, nil)
        if status == errSecDuplicateItem {
            return SecItemUpdate(query as CFDictionary, attributes as CFDictionary) == errSecSuccess
        }
        return status == errSecSuccess
    }

    public static func apiKey() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: keychainAccount,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var result: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess,
              let data = result as? Data else {
            return nil
        }
        return String(data: data, encoding: .utf8)
    }

    public static func hasAPIKey() -> Bool {
        guard let key = apiKey() else {
            return false
        }
        return !key.isEmpty
    }

    public static func noteActivePeer(_ peerId: Int64?) {
        if let peerId {
            defaults.set(String(peerId), forKey: activePeerKey)
        } else {
            defaults.removeObject(forKey: activePeerKey)
        }
    }
}
