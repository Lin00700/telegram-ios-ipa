import Foundation
import Security

public enum CueAIProviderKind: String, Codable, CaseIterable, Equatable {
    case openAI = "openai"
    case anthropic = "anthropic"
    case gemini = "gemini"
    case openAICompatible = "openai-compatible"

    public var displayName: String {
        switch self {
        case .openAI: return "OpenAI"
        case .anthropic: return "Anthropic Claude"
        case .gemini: return "Google Gemini"
        case .openAICompatible: return "自定义 OpenAI-compatible"
        }
    }

    public var defaultEndpoint: String? {
        switch self {
        case .openAI: return "https://api.openai.com/v1"
        case .anthropic: return "https://api.anthropic.com"
        case .gemini: return "https://generativelanguage.googleapis.com"
        case .openAICompatible: return nil
        }
    }
}

public struct CueAIProfile: Codable, Equatable {
    public var id: String
    public var name: String
    public var endpoint: String
    public var model: String
    public var providerKind: CueAIProviderKind?
    public var systemPrompt: String?

    public init(id: String = UUID().uuidString, name: String, endpoint: String, model: String, providerKind: CueAIProviderKind? = nil, systemPrompt: String? = nil) {
        self.id = id
        self.name = name
        self.endpoint = endpoint
        self.model = model
        self.providerKind = providerKind
        self.systemPrompt = systemPrompt
    }
}

public struct CueAIChatOptions: Codable, Equatable {
    public var assignedProfileIDs: [String]
    public var autoReplyEnabled: Bool
    public var outboundConsentAccepted: Bool
    public var mentionOrReplyOnly: Bool

    public init(assignedProfileIDs: [String] = [], autoReplyEnabled: Bool = false, outboundConsentAccepted: Bool = false, mentionOrReplyOnly: Bool = true) {
        self.assignedProfileIDs = assignedProfileIDs
        self.autoReplyEnabled = autoReplyEnabled && outboundConsentAccepted
        self.outboundConsentAccepted = outboundConsentAccepted
        self.mentionOrReplyOnly = mentionOrReplyOnly
    }
}

public enum CueFeaturePreferences {
    private static let defaults = UserDefaults.standard
    private static let keychainService = "com.lin00700.unofficialchat.ai-provider"
    private static let prefix = "com.lin00700.unofficialchat.v1"

    private static func conversationKey(_ feature: String, accountId: Int64, peerId: Int64, threadId: Int64?) -> String {
        let thread = threadId.map(String.init) ?? "root"
        return "\(prefix).\(feature).\(accountId).\(peerId).\(thread)"
    }

    private static func profileListKey(accountId: Int64) -> String {
        return "\(prefix).ai-profiles.\(accountId)"
    }

    public static func isAutoTranslationEnabled(accountId: Int64, peerId: Int64, threadId: Int64?) -> Bool {
        return defaults.bool(forKey: conversationKey("translation.enabled", accountId: accountId, peerId: peerId, threadId: threadId))
    }

    public static func setAutoTranslationEnabled(_ enabled: Bool, accountId: Int64, peerId: Int64, threadId: Int64?) {
        defaults.set(enabled, forKey: conversationKey("translation.enabled", accountId: accountId, peerId: peerId, threadId: threadId))
    }

    public static func hasTranslationConsent(accountId: Int64, peerId: Int64, threadId: Int64?) -> Bool {
        return defaults.bool(forKey: conversationKey("translation.consent", accountId: accountId, peerId: peerId, threadId: threadId))
    }

    public static func setTranslationConsent(_ accepted: Bool, accountId: Int64, peerId: Int64, threadId: Int64?) {
        defaults.set(accepted, forKey: conversationKey("translation.consent", accountId: accountId, peerId: peerId, threadId: threadId))
    }

    public static func aiOptions(accountId: Int64, peerId: Int64, threadId: Int64?) -> CueAIChatOptions {
        let key = conversationKey("ai-chat.options", accountId: accountId, peerId: peerId, threadId: threadId)
        guard let data = defaults.data(forKey: key),
              let value = try? JSONDecoder().decode(CueAIChatOptions.self, from: data) else {
            return CueAIChatOptions()
        }
        return value
    }

    public static func setAIOptions(_ options: CueAIChatOptions, accountId: Int64, peerId: Int64, threadId: Int64?) {
        var safeOptions = options
        if safeOptions.autoReplyEnabled && !safeOptions.outboundConsentAccepted {
            safeOptions.autoReplyEnabled = false
        }
        let key = conversationKey("ai-chat.options", accountId: accountId, peerId: peerId, threadId: threadId)
        guard let data = try? JSONEncoder().encode(safeOptions) else {
            return
        }
        defaults.set(data, forKey: key)
    }

    public static func profiles(accountId: Int64) -> [CueAIProfile] {
        guard let data = defaults.data(forKey: profileListKey(accountId: accountId)),
              let values = try? JSONDecoder().decode([CueAIProfile].self, from: data) else {
            return []
        }
        return values
    }

    public static func nextAssignedProfile(accountId: Int64, peerId: Int64, threadId: Int64?) -> CueAIProfile? {
        let options = self.aiOptions(accountId: accountId, peerId: peerId, threadId: threadId)
        let assigned = self.profiles(accountId: accountId).filter { options.assignedProfileIDs.contains($0.id) }
        guard !assigned.isEmpty else {
            return nil
        }
        let rotationKey = conversationKey("ai-chat.rotation", accountId: accountId, peerId: peerId, threadId: threadId)
        let current = max(0, defaults.integer(forKey: rotationKey))
        let profile = assigned[current % assigned.count]
        defaults.set((current + 1) % assigned.count, forKey: rotationKey)
        return profile
    }

    public static func setProfiles(_ profiles: [CueAIProfile], accountId: Int64) {
        guard let data = try? JSONEncoder().encode(profiles) else {
            return
        }
        defaults.set(data, forKey: profileListKey(accountId: accountId))
    }

    public static func isSecureHTTPS(_ endpoint: String) -> Bool {
        guard let components = URLComponents(string: endpoint),
              components.scheme?.lowercased() == "https",
              let host = components.host, !host.isEmpty,
              components.user == nil, components.password == nil,
              components.fragment == nil else {
            return false
        }
        return true
    }

    @discardableResult
    public static func saveAPIKey(_ apiKey: String, accountId: Int64, profileId: String) -> Bool {
        guard !apiKey.isEmpty,
              let value = apiKey.data(using: .utf8) else {
            return false
        }
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: "\(accountId):\(profileId)"
        ]
        let attributes: [String: Any] = [
            kSecValueData as String: value,
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        ]
        let status = SecItemAdd(query.merging(attributes) { _, new in new } as CFDictionary, nil)
        if status == errSecDuplicateItem {
            return SecItemUpdate(query as CFDictionary, attributes as CFDictionary) == errSecSuccess
        }
        return status == errSecSuccess
    }

    public static func apiKey(accountId: Int64, profileId: String) -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: "\(accountId):\(profileId)",
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

    @discardableResult
    public static func deleteAPIKey(accountId: Int64, profileId: String) -> Bool {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: "\(accountId):\(profileId)"
        ]
        let status = SecItemDelete(query as CFDictionary)
        return status == errSecSuccess || status == errSecItemNotFound
    }
}
