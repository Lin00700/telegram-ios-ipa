import Foundation

struct ParsedSender: Equatable {
    enum Kind: Equatable {
        case empty
        case alphanumeric(String)
        case foreign(digits: String)
        case mobile(national: String)
        case landline(areaCode: String, subscriber: String)
        case service(national: String)
        case unknown(digits: String)
    }

    var kind: Kind

    var summary: String {
        switch kind {
        case .empty:
            return "空发件人"
        case .alphanumeric(let text):
            return "非数字发件人 \(text)"
        case .foreign(let digits):
            return "境外号码 +\(digits)"
        case .mobile(let national):
            return "中国手机 \(national)"
        case .landline(let areaCode, let subscriber):
            return "座机 \(areaCode)-\(subscriber)"
        case .service(let national):
            return "端口或短号 \(national)"
        case .unknown(let digits):
            return "无法归类的数字 \(digits)"
        }
    }
}

enum PhoneNumber {
    static func parse(_ raw: String, areaCodes: Set<String>) -> ParsedSender {
        let trimmed = raw.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty {
            return ParsedSender(kind: .empty)
        }
        if trimmed.contains(where: { $0.isLetter }) {
            return ParsedSender(kind: .alphanumeric(trimmed))
        }

        var international = trimmed.hasPrefix("+")
        var digits = asciiDigits(trimmed)
        if digits.isEmpty {
            return ParsedSender(kind: .unknown(digits: trimmed))
        }
        if digits.hasPrefix("00") {
            international = true
            digits.removeFirst(2)
        }

        if digits.hasPrefix("86"), let national = nationalKind(String(digits.dropFirst(2)), areaCodes: areaCodes), isDomestic(national) {
            return ParsedSender(kind: national)
        }
        if international {
            return ParsedSender(kind: .foreign(digits: digits))
        }
        if let national = nationalKind(digits, areaCodes: areaCodes) {
            return ParsedSender(kind: national)
        }
        return ParsedSender(kind: .unknown(digits: digits))
    }

    static func callDigits(from raw: String, areaCodes: Set<String>) -> String? {
        switch parse(raw, areaCodes: areaCodes).kind {
        case .mobile(let national):
            return "86" + national
        case .landline(let areaCode, let subscriber):
            return "86" + String(areaCode.dropFirst()) + subscriber
        case .foreign(let digits):
            guard (8...15).contains(digits.count) else { return nil }
            return digits
        case .service(let national):
            guard (3...20).contains(national.count) else { return nil }
            return national
        default:
            return nil
        }
    }

    static func senderKey(_ raw: String, areaCodes: Set<String>) -> String {
        switch parse(raw, areaCodes: areaCodes).kind {
        case .mobile(let national):
            return "m:" + national
        case .landline(let areaCode, let subscriber):
            return "l:\(areaCode):\(subscriber)"
        case .foreign(let digits):
            return "f:" + digits
        case .service(let national):
            return "s:" + national
        case .alphanumeric(let text):
            return "a:" + text.lowercased()
        case .empty:
            return "e:"
        case .unknown(let digits):
            return "u:" + digits
        }
    }

    private static func isDomestic(_ kind: ParsedSender.Kind) -> Bool {
        switch kind {
        case .mobile, .landline, .service:
            return true
        default:
            return false
        }
    }

    private static func nationalKind(_ national: String, areaCodes: Set<String>) -> ParsedSender.Kind? {
        if isMobile(national) {
            return .mobile(national: national)
        }
        if let landline = matchLandline(national, areaCodes: areaCodes) {
            return .landline(areaCode: landline.areaCode, subscriber: landline.subscriber)
        }
        if isService(national) {
            return .service(national: national)
        }
        return nil
    }

    static func isMobile(_ national: String) -> Bool {
        guard national.count == 11, national.first == "1", national.allSatisfy(isDigit) else { return false }
        guard let second = national.dropFirst().first?.wholeNumberValue else { return false }
        return (3...9).contains(second)
    }

    static func isPrefix7(_ text: String) -> Bool {
        guard text.count == 7, text.allSatisfy(isDigit), text.first == "1" else { return false }
        guard let second = text.dropFirst().first?.wholeNumberValue else { return false }
        return (3...9).contains(second)
    }

    static func isVirtualFamily(_ prefix7: String) -> Bool {
        ["162", "165", "167", "170", "171"].contains { prefix7.hasPrefix($0) }
    }

    private static func matchLandline(_ national: String, areaCodes: Set<String>) -> (areaCode: String, subscriber: String)? {
        let candidates = national.hasPrefix("0") ? [national] : [national, "0" + national]
        for candidate in candidates {
            for length in [4, 3] {
                guard candidate.count >= length + 7 else { continue }
                let code = String(candidate.prefix(length))
                let subscriber = String(candidate.dropFirst(length))
                guard areaCodes.contains(code), (7...8).contains(subscriber.count), subscriber.allSatisfy(isDigit) else { continue }
                return (code, subscriber)
            }
        }
        return nil
    }

    private static func isService(_ national: String) -> Bool {
        let count = national.count
        if national.hasPrefix("106"), (8...20).contains(count) { return true }
        if national.hasPrefix("95"), (5...8).contains(count) { return true }
        if national.hasPrefix("96"), (5...8).contains(count) { return true }
        if national.hasPrefix("100"), (5...6).contains(count) { return true }
        if national.hasPrefix("12"), (5...6).contains(count) { return true }
        if (3...6).contains(count), !national.hasPrefix("1"), !national.hasPrefix("0") { return true }
        return false
    }

    private static func asciiDigits(_ text: String) -> String {
        var digits = ""
        for character in text {
            guard let value = character.wholeNumberValue, (0...9).contains(value) else { continue }
            digits.append(Character(String(value)))
        }
        return digits
    }

    private static func isDigit(_ character: Character) -> Bool {
        character >= "0" && character <= "9"
    }
}
