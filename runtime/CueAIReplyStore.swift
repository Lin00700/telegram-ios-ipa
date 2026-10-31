import Foundation

public final class CueAIReplyStore {
    public static let shared = CueAIReplyStore()

    private struct ConversationKey: Hashable {
        let accountId: Int64
        let peerId: Int64
        let threadId: Int64?
    }

    private struct GeneratedReplyKey: Hashable {
        let accountId: Int64
        let peerId: Int64
        let textDigest: UInt64
    }

    private let lock = NSLock()
    private var pending = Set<CueTranslationMessageKey>()
    private var completed = Set<CueTranslationMessageKey>()
    private var completedOrder: [CueTranslationMessageKey] = []
    private var lastReplyAt: [ConversationKey: Date] = [:]
    private var generatedReplyExpirations: [GeneratedReplyKey: Date] = [:]
    private let maximumEntries = 512

    private init() {
    }

    public func rememberGeneratedReply(accountId: Int64, peerId: Int64, text: String, validity: TimeInterval = 120.0) {
        let normalized = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !normalized.isEmpty else {
            return
        }
        let key = GeneratedReplyKey(accountId: accountId, peerId: peerId, textDigest: Self.digest(normalized))
        let now = Date()
        self.lock.lock()
        self.generatedReplyExpirations = self.generatedReplyExpirations.filter { $0.value > now }
        self.generatedReplyExpirations[key] = now.addingTimeInterval(validity)
        if self.generatedReplyExpirations.count > 256,
           let oldest = self.generatedReplyExpirations.min(by: { $0.value < $1.value })?.key {
            self.generatedReplyExpirations.removeValue(forKey: oldest)
        }
        self.lock.unlock()
    }

    public func consumeGeneratedReply(accountId: Int64, peerId: Int64, text: String) -> Bool {
        let normalized = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !normalized.isEmpty else {
            return false
        }
        let key = GeneratedReplyKey(accountId: accountId, peerId: peerId, textDigest: Self.digest(normalized))
        let now = Date()
        self.lock.lock()
        self.generatedReplyExpirations = self.generatedReplyExpirations.filter { $0.value > now }
        let matched = self.generatedReplyExpirations.removeValue(forKey: key) != nil
        self.lock.unlock()
        return matched
    }

    private static func digest(_ text: String) -> UInt64 {
        var value: UInt64 = 14_695_981_039_346_656_037
        for byte in text.utf8 {
            value = (value ^ UInt64(byte)) &* 1_099_511_628_211
        }
        return value
    }

    @discardableResult
    public func claim(_ key: CueTranslationMessageKey, minimumInterval: TimeInterval = 20.0) -> Bool {
        self.lock.lock()
        defer { self.lock.unlock() }

        guard !self.pending.contains(key), !self.completed.contains(key) else {
            return false
        }

        let conversation = ConversationKey(accountId: key.accountId, peerId: key.peerId, threadId: key.threadId)
        if let previousReply = self.lastReplyAt[conversation], Date().timeIntervalSince(previousReply) < minimumInterval {
            return false
        }

        self.lastReplyAt[conversation] = Date()
        self.pending.insert(key)
        return true
    }

    public func finish(_ key: CueTranslationMessageKey, sent: Bool) {
        self.lock.lock()
        self.pending.remove(key)
        if sent {
            if self.completed.insert(key).inserted {
                self.completedOrder.append(key)
            }
            let conversation = ConversationKey(accountId: key.accountId, peerId: key.peerId, threadId: key.threadId)
            self.lastReplyAt[conversation] = Date()
            while self.completedOrder.count > self.maximumEntries {
                let evicted = self.completedOrder.removeFirst()
                self.completed.remove(evicted)
            }
            if self.lastReplyAt.count > self.maximumEntries {
                let retained = Set(self.completedOrder.map {
                    ConversationKey(accountId: $0.accountId, peerId: $0.peerId, threadId: $0.threadId)
                })
                self.lastReplyAt = self.lastReplyAt.filter { retained.contains($0.key) }
            }
        }
        self.lock.unlock()
    }
}
