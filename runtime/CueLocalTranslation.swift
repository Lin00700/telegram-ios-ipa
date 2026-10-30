import Foundation
import NaturalLanguage
import MLKitTranslate

public struct CueTranslationMessageKey: Hashable {
    public let accountId: Int64
    public let peerId: Int64
    public let threadId: Int64?
    public let namespace: Int32
    public let messageId: Int32

    public init(accountId: Int64, peerId: Int64, threadId: Int64?, namespace: Int32, messageId: Int32) {
        self.accountId = accountId
        self.peerId = peerId
        self.threadId = threadId
        self.namespace = namespace
        self.messageId = messageId
    }
}

public final class CueTranslationStore {
    public static let shared = CueTranslationStore()

    private struct ConversationKey: Hashable {
        let accountId: Int64
        let peerId: Int64
        let threadId: Int64?
    }

    private let lock = NSLock()
    private var translations: [CueTranslationMessageKey: String] = [:]
    private var insertionOrder: [CueTranslationMessageKey] = []
    private var queued: [CueTranslationMessageKey: Int] = [:]
    private var generations: [ConversationKey: Int] = [:]
    private let maximumEntries = 512

    private init() {
    }

    @discardableResult
    public func claim(_ key: CueTranslationMessageKey) -> Int? {
        self.lock.lock()
        defer { self.lock.unlock() }
        guard self.translations[key] == nil, self.queued[key] == nil else {
            return nil
        }
        let conversation = ConversationKey(accountId: key.accountId, peerId: key.peerId, threadId: key.threadId)
        let generation = self.generations[conversation, default: 0]
        self.queued[key] = generation
        return generation
    }

    public func isCurrent(_ key: CueTranslationMessageKey, generation: Int) -> Bool {
        self.lock.lock()
        defer { self.lock.unlock() }
        let conversation = ConversationKey(accountId: key.accountId, peerId: key.peerId, threadId: key.threadId)
        return self.generations[conversation, default: 0] == generation
    }

    public func value(for key: CueTranslationMessageKey) -> String? {
        self.lock.lock()
        defer { self.lock.unlock() }
        return self.translations[key]
    }

    public func removeTranslations(accountId: Int64, peerId: Int64, threadId: Int64?) {
        self.lock.lock()
        let conversation = ConversationKey(accountId: accountId, peerId: peerId, threadId: threadId)
        self.generations[conversation, default: 0] += 1
        let matchingKeys = self.translations.keys.filter { key in
            key.accountId == accountId && key.peerId == peerId && key.threadId == threadId
        }
        for key in matchingKeys {
            self.translations.removeValue(forKey: key)
            self.queued.removeValue(forKey: key)
        }
        let matchingQueuedKeys = self.queued.keys.filter { key in
            key.accountId == accountId && key.peerId == peerId && key.threadId == threadId
        }
        for key in matchingQueuedKeys {
            self.queued.removeValue(forKey: key)
        }
        self.insertionOrder.removeAll { key in
            key.accountId == accountId && key.peerId == peerId && key.threadId == threadId
        }
        self.lock.unlock()
    }

    public func finish(_ key: CueTranslationMessageKey, generation: Int, translatedText: String?) {
        self.lock.lock()
        guard self.queued[key] == generation else {
            self.lock.unlock()
            return
        }
        self.queued.removeValue(forKey: key)
        let conversation = ConversationKey(accountId: key.accountId, peerId: key.peerId, threadId: key.threadId)
        guard self.generations[conversation, default: 0] == generation else {
            self.lock.unlock()
            return
        }
        if let translatedText, !translatedText.isEmpty {
            if self.translations[key] == nil {
                self.insertionOrder.append(key)
            }
            self.translations[key] = translatedText
            while self.insertionOrder.count > self.maximumEntries {
                let evicted = self.insertionOrder.removeFirst()
                self.translations.removeValue(forKey: evicted)
            }
        }
        self.lock.unlock()
    }
}

public final class CueLocalTranslationService {
    public static let shared = CueLocalTranslationService()

    private let modelLock = NSLock()
    private var translatorLanguageTag: String?
    private var cachedTranslator: Translator?

    private init() {
    }

    public func translateToSimplifiedChinese(_ text: String, completion: @escaping (String?) -> Void) {
        let input = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !input.isEmpty, input.count <= 4096 else {
            completion(nil)
            return
        }

        let recognizer = NLLanguageRecognizer()
        recognizer.processString(input)
        guard let detectedLanguage = recognizer.dominantLanguage?.rawValue,
              !detectedLanguage.isEmpty,
              detectedLanguage != "und" else {
            completion(nil)
            return
        }

        if detectedLanguage.lowercased().hasPrefix("zh") {
            let simplified = CueOpenCCT2S.shared.convert(input)
            completion(simplified == input || simplified.isEmpty ? nil : simplified)
            return
        }

        guard let sourceLanguage = TranslateLanguage.fromLanguageTag(detectedLanguage) else {
            completion(nil)
            return
        }

        let options = TranslatorOptions(sourceLanguage: sourceLanguage, targetLanguage: .chinese)
        self.modelLock.lock()
        let translator: Translator
        if self.translatorLanguageTag == detectedLanguage, let cachedTranslator = self.cachedTranslator {
            translator = cachedTranslator
        } else {
            translator = Translator.translator(options: options)
            self.translatorLanguageTag = detectedLanguage
            self.cachedTranslator = translator
        }
        self.modelLock.unlock()

        let conditions = ModelDownloadConditions(allowsCellularAccess: false, allowsBackgroundDownloading: true)
        translator.downloadModelIfNeeded(with: conditions) { [weak self] error in
            guard error == nil, let self else {
                completion(nil)
                return
            }
            translator.translate(input) { translatedText, error in
                guard error == nil, let translatedText, !translatedText.isEmpty else {
                    completion(nil)
                    return
                }
                let simplified = CueOpenCCT2S.shared.convert(translatedText)
                completion(simplified.isEmpty ? nil : simplified)
            }
        }
    }
}
