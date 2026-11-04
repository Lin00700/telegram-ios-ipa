import Foundation

public struct InkRetentionNote: Equatable {
    public var recalled: Bool
    public var previousText: String?
}

public enum InkRetention {
    public static func note(peerId: Int64, namespace: Int32, messageId: Int32) -> InkRetentionNote? {
        guard InkPreferences.antiRecall else {
            return nil
        }
        let key = "\(peerId):\(namespace):\(messageId)"
        let root = load()
        let recalled = (root["recalled"] as? [String])?.contains(key) ?? false
        let previous = (root["edits"] as? [String: String])?[key]
        if !recalled && (previous == nil || previous?.isEmpty == true) {
            return nil
        }
        return InkRetentionNote(recalled: recalled, previousText: previous)
    }

    public static func translation(peerId: Int64, namespace: Int32, messageId: Int32) -> String? {
        let key = "\(peerId):\(namespace):\(messageId)"
        return (load()["translations"] as? [String: String])?[key]
    }

    public static func saveTranslation(peerId: Int64, namespace: Int32, messageId: Int32, text: String) {
        let key = "\(peerId):\(namespace):\(messageId)"
        var root = load()
        var translations = root["translations"] as? [String: String] ?? [:]
        translations[key] = text
            if translations.count > 800 {
                let overflow = translations.count - 800
                for old in Array(translations.keys.prefix(overflow)) {
                    translations.removeValue(forKey: old)
                }
            }
        root["translations"] = translations
        store(root)
    }

    private static let lock = NSLock()

    static func fileURL() -> URL {
        let directory = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("Ink", isDirectory: true)
        try? FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        return directory.appendingPathComponent("message-retention.json")
    }

    private static func load() -> [String: Any] {
        lock.lock()
        defer { lock.unlock() }
        guard let data = try? Data(contentsOf: fileURL()),
              let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return [:]
        }
        return object
    }

    private static func store(_ root: [String: Any]) {
        lock.lock()
        defer { lock.unlock() }
        guard let data = try? JSONSerialization.data(withJSONObject: root, options: [.prettyPrinted]) else {
            return
        }
        try? data.write(to: fileURL(), options: .atomic)
    }
}
