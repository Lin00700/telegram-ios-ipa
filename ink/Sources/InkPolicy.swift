import Foundation

public enum InkAutoReplyPolicy {
    public static func shouldReply(master: Bool, chatEnabled: Bool, trigger: InkTrigger, text: String, mentioned: Bool, isBot: Bool, isOutgoing: Bool, keywords: [String]) -> Bool {
        if !master || !chatEnabled || isBot || isOutgoing {
            return false
        }
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty {
            return false
        }
        switch trigger {
        case .all:
            return true
        case .mention:
            return mentioned
        case .keyword:
            let lower = trimmed.lowercased()
            return keywords.contains { keyword in
                !keyword.isEmpty && lower.contains(keyword.lowercased())
            }
        }
    }
}

public enum InkRateLimit {
    public static func allow(now: TimeInterval, history: [TimeInterval], minInterval: TimeInterval, maxCount: Int, window: TimeInterval) -> (allowed: Bool, history: [TimeInterval]) {
        let recent = history.filter { now - $0 < window && now - $0 >= 0 }
        if let last = recent.max(), now - last < minInterval {
            return (false, recent)
        }
        if recent.count >= maxCount {
            return (false, recent)
        }
        return (true, recent + [now])
    }
}
