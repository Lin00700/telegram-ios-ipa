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
              let apiKey = CueFeaturePreferences.apiKey(accountId: accountId, profileId: profile.id),
              let url = Self.completionsURL(for: profile.endpoint) else {
            completion(nil)
            return
        }

        var messages: [[String: String]] = []
        if let prompt = profile.systemPrompt?.trimmingCharacters(in: .whitespacesAndNewlines), !prompt.isEmpty {
            messages.append(["role": "system", "content": String(prompt.prefix(2000))])
        }
        messages.append(["role": "user", "content": text])

        let body: [String: Any] = [
            "model": profile.model,
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 800
        ]
        guard let bodyData = try? JSONSerialization.data(withJSONObject: body) else {
            completion(nil)
            return
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 25
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        request.httpBody = bodyData

        self.session.dataTask(with: request) { data, response, error in
            guard error == nil,
                  let response = response as? HTTPURLResponse,
                  (200 ..< 300).contains(response.statusCode),
                  let data,
                  data.count <= 1024 * 1024,
                  let root = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let choices = root["choices"] as? [[String: Any]],
                  let message = choices.first?["message"] as? [String: Any],
                  let content = message["content"] as? String else {
                completion(nil)
                return
            }
            let reply = content.trimmingCharacters(in: .whitespacesAndNewlines)
            completion(reply.isEmpty ? nil : String(reply.prefix(4000)))
        }.resume()
    }

    private static func completionsURL(for endpoint: String) -> URL? {
        guard var components = URLComponents(string: endpoint),
              components.scheme?.lowercased() == "https",
              components.user == nil,
              components.password == nil,
              components.fragment == nil else {
            return nil
        }
        var path = components.path.trimmingCharacters(in: CharacterSet(charactersIn: "/"))
        if path.isEmpty {
            path = "v1"
        }
        if !path.hasSuffix("chat/completions") {
            if !path.hasSuffix("v1") {
                path += "/v1"
            }
            path += "/chat/completions"
        }
        components.path = "/" + path
        return components.url
    }
}
