import Foundation

public final class CueAIReplyService {
    public static let shared = CueAIReplyService()

    private let session: URLSession

    private init() {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.timeoutIntervalForRequest = 25
        configuration.timeoutIntervalForResource = 30
        configuration.urlCache = nil
        configuration.requestCachePolicy = .reloadIgnoringLocalCacheData
        self.session = URLSession(configuration: configuration)
    }

    public func generateReply(
        incomingText: String,
        accountId: Int64,
        peerId: Int64,
        threadId: Int64?,
        completion: @escaping (String?) -> Void
    ) {
        let text = incomingText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, text.count <= 4096,
              let profile = CueFeaturePreferences.nextAssignedProfile(accountId: accountId, peerId: peerId, threadId: threadId),
              CueFeaturePreferences.isSecureHTTPS(profile.endpoint),
              let apiKey = CueFeaturePreferences.apiKey(accountId: accountId, profileId: profile.id) else {
            completion(nil)
            return
        }

        let providerKind = profile.providerKind ?? .openAICompatible
        guard let url = Self.requestURL(for: profile, kind: providerKind),
              let body = Self.requestBody(text: text, profile: profile, kind: providerKind),
              let bodyData = try? JSONSerialization.data(withJSONObject: body) else {
            completion(nil)
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 25
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = bodyData
        switch providerKind {
        case .openAI, .openAICompatible:
            request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        case .anthropic:
            request.setValue(apiKey, forHTTPHeaderField: "x-api-key")
            request.setValue("2023-06-01", forHTTPHeaderField: "anthropic-version")
        case .gemini:
            request.setValue(apiKey, forHTTPHeaderField: "x-goog-api-key")
        }

        self.session.dataTask(with: request) { data, response, error in
            guard error == nil,
                  let response = response as? HTTPURLResponse,
                  (200 ..< 300).contains(response.statusCode),
                  let data, data.count <= 1024 * 1024,
                  let rawReply = Self.extractText(from: data, kind: providerKind) else {
                completion(nil)
                return
            }
            let reply = rawReply.trimmingCharacters(in: .whitespacesAndNewlines)
            completion(reply.isEmpty ? nil : String(reply.prefix(4000)))
        }.resume()
    }

    private static func requestBody(text: String, profile: CueAIProfile, kind: CueAIProviderKind) -> [String: Any]? {
        let systemPrompt: String?
        if let configuredPrompt = profile.systemPrompt?.trimmingCharacters(in: .whitespacesAndNewlines), !configuredPrompt.isEmpty {
            systemPrompt = String(configuredPrompt.prefix(2000))
        } else {
            systemPrompt = nil
        }
        switch kind {
        case .openAI, .openAICompatible:
            var messages: [[String: String]] = []
            if let systemPrompt, !systemPrompt.isEmpty {
                messages.append(["role": "system", "content": systemPrompt])
            }
            messages.append(["role": "user", "content": text])
            return [
                "model": profile.model,
                "messages": messages,
                "temperature": 0.7,
                "max_tokens": 800
            ]
        case .anthropic:
            var body: [String: Any] = [
                "model": profile.model,
                "messages": [["role": "user", "content": text]],
                "temperature": 0.7,
                "max_tokens": 800
            ]
            if let systemPrompt, !systemPrompt.isEmpty {
                body["system"] = systemPrompt
            }
            return body
        case .gemini:
            var body: [String: Any] = [
                "contents": [[
                    "role": "user",
                    "parts": [["text": text]]
                ]],
                "generationConfig": [
                    "temperature": 0.7,
                    "maxOutputTokens": 800
                ]
            ]
            if let systemPrompt, !systemPrompt.isEmpty {
                body["systemInstruction"] = ["parts": [["text": systemPrompt]]]
            }
            return body
        }
    }

    private static func requestURL(for profile: CueAIProfile, kind: CueAIProviderKind) -> URL? {
        guard var components = URLComponents(string: profile.endpoint),
              components.scheme?.lowercased() == "https",
              let host = components.host, !host.isEmpty,
              components.user == nil,
              components.password == nil,
              components.fragment == nil else {
            return nil
        }

        var path = components.path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        switch kind {
        case .openAI, .openAICompatible:
            if !path.hasSuffix("chat/completions") {
                if !path.hasSuffix("v1") {
                    path = path.isEmpty ? "v1" : path + "/v1"
                }
                path += "/chat/completions"
            }
        case .anthropic:
            if !path.hasSuffix("messages") {
                if !path.hasSuffix("v1") {
                    path = path.isEmpty ? "v1" : path + "/v1"
                }
                path += "/messages"
            }
        case .gemini:
            if !(path.contains("/models/") && path.hasSuffix("generateContent")) {
                if !path.hasSuffix("v1beta") && !path.hasSuffix("v1") {
                    path = path.isEmpty ? "v1beta" : path + "/v1beta"
                }
                var allowed = CharacterSet.alphanumerics
                allowed.insert(charactersIn: "-_.")
                guard let model = profile.model.addingPercentEncoding(withAllowedCharacters: allowed) else {
                    return nil
                }
                path += "/models/\(model):generateContent"
            }
        }
        components.path = "/" + path
        return components.url
    }

    private static func extractText(from data: Data, kind: CueAIProviderKind) -> String? {
        guard let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return nil
        }
        switch kind {
        case .openAI, .openAICompatible:
            guard let choices = root["choices"] as? [[String: Any]],
                  let message = choices.first?["message"] as? [String: Any] else {
                return nil
            }
            return message["content"] as? String
        case .anthropic:
            guard let blocks = root["content"] as? [[String: Any]] else {
                return nil
            }
            return blocks
                .filter { ($0["type"] as? String) == "text" }
                .compactMap { $0["text"] as? String }
                .joined()
        case .gemini:
            guard let candidates = root["candidates"] as? [[String: Any]],
                  let content = candidates.first?["content"] as? [String: Any],
                  let parts = content["parts"] as? [[String: Any]] else {
                return nil
            }
            return parts.compactMap { $0["text"] as? String }.joined()
        }
    }
}
