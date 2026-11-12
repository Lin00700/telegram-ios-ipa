import Foundation

struct StoredNumber: Codable, Equatable, Hashable {
    var display: String
    var e164: String
}

struct LabeledNumber: Codable, Equatable, Hashable {
    var display: String
    var e164: String
    var label: String
}

struct FilterRules: Codable, Equatable {
    var schema: Int = 1
    var smsEnabled: Bool = false
    var blockForeignSMS: Bool = false
    var provinceFilterEnabled: Bool = false
    var blockedProvinces: [String] = []
    var blockedAreaCodes: [String] = []
    var onlyGuangdongSMS: Bool = false
    var blockVirtualSMS: Bool = false
    var virtualPrefixes: [String] = KeywordPresets.defaultVirtualPrefixes
    var keywordFilterEnabled: Bool = false
    var blockKeywords: [String] = KeywordPresets.defaultBlockKeywords
    var blockRegexes: [String] = KeywordPresets.defaultBlockRegexes
    var whitelistKeywordsEnabled: Bool = false
    var whitelistKeywords: [String] = KeywordPresets.defaultWhitelistKeywords
    var whitelistSendersEnabled: Bool = false
    var whitelistSenders: [String] = []
    var routeTransaction: Bool = false
    var transactionKeywords: [String] = KeywordPresets.defaultTransactionKeywords
    var routePromotion: Bool = false
    var promotionKeywords: [String] = KeywordPresets.defaultPromotionKeywords
    var callBlockingEnabled: Bool = false
    var blockedNumbers: [StoredNumber] = []
    var labeledNumbers: [LabeledNumber] = []
    var segmentBlockEnabled: Bool = false
    var blockedSegments: [String] = []
    var expandVirtualSegments: Bool = false
    var virtualSegments: [String] = []
    var contactsOnlyGuidanceEnabled: Bool = false

    enum CodingKeys: String, CodingKey {
        case schema
        case smsEnabled
        case blockForeignSMS
        case provinceFilterEnabled
        case blockedProvinces
        case blockedAreaCodes
        case onlyGuangdongSMS
        case blockVirtualSMS
        case virtualPrefixes
        case keywordFilterEnabled
        case blockKeywords
        case blockRegexes
        case whitelistKeywordsEnabled
        case whitelistKeywords
        case whitelistSendersEnabled
        case whitelistSenders
        case routeTransaction
        case transactionKeywords
        case routePromotion
        case promotionKeywords
        case callBlockingEnabled
        case blockedNumbers
        case labeledNumbers
        case segmentBlockEnabled
        case blockedSegments
        case expandVirtualSegments
        case virtualSegments
        case contactsOnlyGuidanceEnabled
    }

    init() {}

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        schema = try container.decodeIfPresent(Int.self, forKey: .schema) ?? 1
        smsEnabled = try container.decodeIfPresent(Bool.self, forKey: .smsEnabled) ?? false
        blockForeignSMS = try container.decodeIfPresent(Bool.self, forKey: .blockForeignSMS) ?? false
        provinceFilterEnabled = try container.decodeIfPresent(Bool.self, forKey: .provinceFilterEnabled) ?? false
        blockedProvinces = try container.decodeIfPresent([String].self, forKey: .blockedProvinces) ?? []
        blockedAreaCodes = try container.decodeIfPresent([String].self, forKey: .blockedAreaCodes) ?? []
        onlyGuangdongSMS = try container.decodeIfPresent(Bool.self, forKey: .onlyGuangdongSMS) ?? false
        blockVirtualSMS = try container.decodeIfPresent(Bool.self, forKey: .blockVirtualSMS) ?? false
        virtualPrefixes = try container.decodeIfPresent([String].self, forKey: .virtualPrefixes) ?? KeywordPresets.defaultVirtualPrefixes
        keywordFilterEnabled = try container.decodeIfPresent(Bool.self, forKey: .keywordFilterEnabled) ?? false
        blockKeywords = try container.decodeIfPresent([String].self, forKey: .blockKeywords) ?? KeywordPresets.defaultBlockKeywords
        blockRegexes = try container.decodeIfPresent([String].self, forKey: .blockRegexes) ?? KeywordPresets.defaultBlockRegexes
        whitelistKeywordsEnabled = try container.decodeIfPresent(Bool.self, forKey: .whitelistKeywordsEnabled) ?? false
        whitelistKeywords = try container.decodeIfPresent([String].self, forKey: .whitelistKeywords) ?? KeywordPresets.defaultWhitelistKeywords
        whitelistSendersEnabled = try container.decodeIfPresent(Bool.self, forKey: .whitelistSendersEnabled) ?? false
        whitelistSenders = try container.decodeIfPresent([String].self, forKey: .whitelistSenders) ?? []
        routeTransaction = try container.decodeIfPresent(Bool.self, forKey: .routeTransaction) ?? false
        transactionKeywords = try container.decodeIfPresent([String].self, forKey: .transactionKeywords) ?? KeywordPresets.defaultTransactionKeywords
        routePromotion = try container.decodeIfPresent(Bool.self, forKey: .routePromotion) ?? false
        promotionKeywords = try container.decodeIfPresent([String].self, forKey: .promotionKeywords) ?? KeywordPresets.defaultPromotionKeywords
        callBlockingEnabled = try container.decodeIfPresent(Bool.self, forKey: .callBlockingEnabled) ?? false
        blockedNumbers = try container.decodeIfPresent([StoredNumber].self, forKey: .blockedNumbers) ?? []
        labeledNumbers = try container.decodeIfPresent([LabeledNumber].self, forKey: .labeledNumbers) ?? []
        segmentBlockEnabled = try container.decodeIfPresent(Bool.self, forKey: .segmentBlockEnabled) ?? false
        blockedSegments = try container.decodeIfPresent([String].self, forKey: .blockedSegments) ?? []
        expandVirtualSegments = try container.decodeIfPresent(Bool.self, forKey: .expandVirtualSegments) ?? false
        virtualSegments = try container.decodeIfPresent([String].self, forKey: .virtualSegments) ?? []
        contactsOnlyGuidanceEnabled = try container.decodeIfPresent(Bool.self, forKey: .contactsOnlyGuidanceEnabled) ?? false
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(schema, forKey: .schema)
        try container.encode(smsEnabled, forKey: .smsEnabled)
        try container.encode(blockForeignSMS, forKey: .blockForeignSMS)
        try container.encode(provinceFilterEnabled, forKey: .provinceFilterEnabled)
        try container.encode(blockedProvinces, forKey: .blockedProvinces)
        try container.encode(blockedAreaCodes, forKey: .blockedAreaCodes)
        try container.encode(onlyGuangdongSMS, forKey: .onlyGuangdongSMS)
        try container.encode(blockVirtualSMS, forKey: .blockVirtualSMS)
        try container.encode(virtualPrefixes, forKey: .virtualPrefixes)
        try container.encode(keywordFilterEnabled, forKey: .keywordFilterEnabled)
        try container.encode(blockKeywords, forKey: .blockKeywords)
        try container.encode(blockRegexes, forKey: .blockRegexes)
        try container.encode(whitelistKeywordsEnabled, forKey: .whitelistKeywordsEnabled)
        try container.encode(whitelistKeywords, forKey: .whitelistKeywords)
        try container.encode(whitelistSendersEnabled, forKey: .whitelistSendersEnabled)
        try container.encode(whitelistSenders, forKey: .whitelistSenders)
        try container.encode(routeTransaction, forKey: .routeTransaction)
        try container.encode(transactionKeywords, forKey: .transactionKeywords)
        try container.encode(routePromotion, forKey: .routePromotion)
        try container.encode(promotionKeywords, forKey: .promotionKeywords)
        try container.encode(callBlockingEnabled, forKey: .callBlockingEnabled)
        try container.encode(blockedNumbers, forKey: .blockedNumbers)
        try container.encode(labeledNumbers, forKey: .labeledNumbers)
        try container.encode(segmentBlockEnabled, forKey: .segmentBlockEnabled)
        try container.encode(blockedSegments, forKey: .blockedSegments)
        try container.encode(expandVirtualSegments, forKey: .expandVirtualSegments)
        try container.encode(virtualSegments, forKey: .virtualSegments)
        try container.encode(contactsOnlyGuidanceEnabled, forKey: .contactsOnlyGuidanceEnabled)
    }

    func clamped() -> FilterRules {
        var copy = self
        copy.blockedProvinces = uniqueTrimmed(blockedProvinces, maxCount: 40, maxLength: 16)
        copy.blockedAreaCodes = uniqueTrimmed(blockedAreaCodes, maxCount: 400, maxLength: 8).filter { $0.allSatisfy { $0 >= "0" && $0 <= "9" } }
        copy.virtualPrefixes = uniqueDigits(virtualPrefixes, minLength: 3, maxLength: 7, maxCount: 30)
        copy.blockKeywords = uniqueTrimmed(blockKeywords, maxCount: 200, maxLength: 40).filter { $0.count >= 2 }
        copy.blockRegexes = uniqueTrimmed(blockRegexes, maxCount: 30, maxLength: 80).filter(RegexSafety.allows)
        copy.whitelistKeywords = uniqueTrimmed(whitelistKeywords, maxCount: 100, maxLength: 40).filter { $0.count >= 2 }
        copy.whitelistSenders = uniqueTrimmed(whitelistSenders, maxCount: 500, maxLength: 40)
        copy.transactionKeywords = uniqueTrimmed(transactionKeywords, maxCount: 100, maxLength: 40).filter { $0.count >= 2 }
        copy.promotionKeywords = uniqueTrimmed(promotionKeywords, maxCount: 100, maxLength: 40).filter { $0.count >= 2 }
        copy.blockedSegments = uniqueDigits(blockedSegments, minLength: 7, maxLength: 7, maxCount: 100).filter(PhoneNumber.isPrefix7)
        copy.virtualSegments = uniqueDigits(virtualSegments, minLength: 7, maxLength: 7, maxCount: 100).filter { PhoneNumber.isPrefix7($0) && PhoneNumber.isVirtualFamily($0) }
        copy.blockedNumbers = clampedNumbers(blockedNumbers)
        copy.labeledNumbers = clampedLabels(labeledNumbers)
        return copy
    }

    private func uniqueTrimmed(_ values: [String], maxCount: Int, maxLength: Int) -> [String] {
        var result: [String] = []
        var seen = Set<String>()
        for value in values {
            let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !trimmed.isEmpty, trimmed.count <= maxLength else { continue }
            guard seen.insert(trimmed).inserted else { continue }
            result.append(trimmed)
            if result.count == maxCount { break }
        }
        return result
    }

    private func uniqueDigits(_ values: [String], minLength: Int, maxLength: Int, maxCount: Int) -> [String] {
        var result: [String] = []
        var seen = Set<String>()
        for value in values {
            let digits = value.filter { $0 >= "0" && $0 <= "9" }
            guard (minLength...maxLength).contains(digits.count), seen.insert(digits).inserted else { continue }
            result.append(digits)
            if result.count == maxCount { break }
        }
        return result
    }

    private func clampedNumbers(_ values: [StoredNumber]) -> [StoredNumber] {
        var result: [StoredNumber] = []
        var seen = Set<String>()
        for value in values {
            guard let number = Int64(value.e164), number > 0, (3...15).contains(value.e164.count) else { continue }
            guard value.e164.allSatisfy({ $0 >= "0" && $0 <= "9" }), seen.insert(value.e164).inserted else { continue }
            let display = value.display.trimmingCharacters(in: .whitespacesAndNewlines)
            result.append(StoredNumber(display: display.isEmpty ? value.e164 : String(display.prefix(40)), e164: value.e164))
            if result.count == 2000 { break }
        }
        return result
    }

    private func clampedLabels(_ values: [LabeledNumber]) -> [LabeledNumber] {
        var result: [LabeledNumber] = []
        var seen = Set<String>()
        for value in values {
            guard let number = Int64(value.e164), number > 0, (3...15).contains(value.e164.count) else { continue }
            guard value.e164.allSatisfy({ $0 >= "0" && $0 <= "9" }) else { continue }
            let label = String(value.label.trimmingCharacters(in: .whitespacesAndNewlines).prefix(24))
            guard !label.isEmpty, !label.contains(where: \.isNewline), seen.insert(value.e164).inserted else { continue }
            let display = value.display.trimmingCharacters(in: .whitespacesAndNewlines)
            result.append(LabeledNumber(display: display.isEmpty ? value.e164 : String(display.prefix(40)), e164: value.e164, label: label))
            if result.count == 2000 { break }
        }
        return result
    }
}
