import Foundation

enum AppIdentity {
    static let fallbackBundleID = "com.lin00700.callsmsblocker"
    static let fallbackGroupID = "group.com.lin00700.callsmsblocker"

    static var appGroupID: String {
        resolved("AppGroupIdentifier") ?? fallbackGroupID
    }

    static var callDirectoryExtensionID: String {
        resolved("CallDirectoryExtensionIdentifier") ?? "\(fallbackBundleID).CallDirectory"
    }

    static var messageFilterExtensionID: String {
        resolved("MessageFilterExtensionIdentifier") ?? "\(fallbackBundleID).MessageFilter"
    }

    private static func resolved(_ key: String) -> String? {
        guard let value = Bundle.main.object(forInfoDictionaryKey: key) as? String else { return nil }
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty, !trimmed.contains("$(") else { return nil }
        return trimmed
    }
}
