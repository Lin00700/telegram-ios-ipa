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

    private func translateLanguage(for languageTag: String) -> TranslateLanguage? {
        let code = languageTag.split(separator: "-", maxSplits: 1).first.map { String($0).lowercased() } ?? ""
        switch code {
        case "af": return .afrikaans
        case "ar": return .arabic
        case "be": return .belarusian
        case "bg": return .bulgarian
        case "bn": return .bengali
        case "ca": return .catalan
        case "cs": return .czech
        case "cy": return .welsh
        case "da": return .danish
        case "de": return .german
        case "el": return .greek
        case "en": return .english
        case "eo": return .esperanto
        case "es": return .spanish
        case "et": return .estonian
        case "fa": return .persian
        case "fi": return .finnish
        case "fr": return .french
        case "ga": return .irish
        case "gl": return .galician
        case "gu": return .gujarati
        case "he", "iw": return .hebrew
        case "hi": return .hindi
        case "hr": return .croatian
        case "ht": return .haitianCreole
        case "hu": return .hungarian
        case "id": return .indonesian
        case "is": return .icelandic
        case "it": return .italian
        case "ja": return .japanese
        case "ka": return .georgian
        case "kn": return .kannada
        case "ko": return .korean
        case "lt": return .lithuanian
        case "lv": return .latvian
        case "mk": return .macedonian
        case "mr": return .marathi
        case "ms": return .malay
        case "mt": return .maltese
        case "nl": return .dutch
        case "no", "nb", "nn": return .norwegian
        case "pl": return .polish
        case "pt": return .portuguese
        case "ro": return .romanian
        case "ru": return .russian
        case "sk": return .slovak
        case "sl": return .slovenian
        case "sq": return .albanian
        case "sv": return .swedish
        case "sw": return .swahili
        case "ta": return .tamil
        case "te": return .telugu
        case "th": return .thai
        case "tl", "fil": return .tagalog
        case "tr": return .turkish
        case "uk": return .ukrainian
        case "ur": return .urdu
        case "vi": return .vietnamese
        case "zh": return .chinese
        default: return nil
        }
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

        guard let sourceLanguage = self.translateLanguage(for: detectedLanguage) else {
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
