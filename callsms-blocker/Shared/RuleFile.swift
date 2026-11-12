import Foundation

enum RuleFile {
    static let fileName = "rules.json"

    static func load(from data: Data) -> FilterRules {
        guard let decoded = try? JSONDecoder().decode(FilterRules.self, from: data) else {
            return FilterRules()
        }
        return decoded.clamped()
    }

    static func loadFromAppGroup() -> FilterRules {
        guard let url = fileURL(), let data = try? Data(contentsOf: url) else {
            return FilterRules()
        }
        return load(from: data)
    }

    static func fileURL() -> URL? {
        containerURL()?.appendingPathComponent(fileName)
    }

    static func containerURL() -> URL? {
        FileManager.default.containerURL(forSecurityApplicationGroupIdentifier: AppIdentity.appGroupID)
    }

    static func encode(_ rules: FilterRules) throws -> Data {
        let encoder = JSONEncoder()
        encoder.outputFormatting = [.prettyPrinted, .sortedKeys]
        return try encoder.encode(rules.clamped())
    }
}
