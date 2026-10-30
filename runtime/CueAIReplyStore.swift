import Foundation

public final class CueAIReplyStore {
    public static let shared = CueAIReplyStore()

    private struct ConversationKey: Hashable {
        let accountId: Int64
        let peerId: Int64
        let threadId: Int64?
    }

    private let lock = NSLock()
    private var pending = Set<CueTranslationMessageKey>()
    private var completed = Set<CueTranslationMessageKey>()
    private var completedOrder: [CueTranslationMessageKey] = []
    private var lastReplyAt: [ConversationKey: Date] = [:]
    private let maximumEntries = 512

    private init() {
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
