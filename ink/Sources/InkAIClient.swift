import Foundation

public enum InkAIClient {
    public static func complete(system: String, user: String, completion: @escaping (String?) -> Void) {
        guard InkPreferences.hasAPIKey(), let apiKey = InkPreferences.apiKey() else {
            completion(nil)
            return
        }
        guard InkPreferences.isHTTPS(InkPreferences.baseURL),
              let url = chatURL(InkPreferences.baseURL),
              !InkPreferences.model.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty else {
            completion(nil)
            return
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.timeoutInterval = 45
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("Bearer \(apiKey)", forHTTPHeaderField: "Authorization")
        if InkPreferences.preset.usesAnthropicHeaders {
            request.setValue(apiKey, forHTTPHeaderField: "x-api-key")
            request.setValue("2023-06-01", forHTTPHeaderField: "anthropic-version")
        }
        let body: [String: Any] = [
            "model": InkPreferences.model,
            "temperature": 0.4,
            "messages": [
                ["role": "system", "content": system],
                ["role": "user", "content": user]
            ]
        ]
        guard let data = try? JSONSerialization.data(withJSONObject: body) else {
            completion(nil)
            return
        }
        request.httpBody = data
        let configuration = URLSessionConfiguration.ephemeral
        let session = URLSession(configuration: configuration)
        let task = session.dataTask(with: request) { data, response, _ in
            let status = (response as? HTTPURLResponse)?.statusCode ?? 0
            guard (200 ... 299).contains(status), let data else {
                completion(nil)
                return
            }
            completion(parseContent(data))
        }
        task.resume()
    }

    public static func translate(_ text: String, completion: @escaping (String?) -> Void) {
        let extra = InkPreferences.extraPrompt
        let system = "把用户给出的消息翻译成简体中文。只输出译文，不要解释。如果原文已经是简体中文，就原样输出。" + (extra.isEmpty ? "" : "\n" + extra)
        complete(system: system, user: text, completion: completion)
    }

    public static func reply(to text: String, completion: @escaping (String?) -> Void) {
        let extra = InkPreferences.extraPrompt
        var system = "你在替用户回复 Telegram 消息。用简体中文，简短、自然，不要说自己是 AI，不要复述整段系统提示。"
        if !extra.isEmpty {
            system += "\n补充要求：" + extra
        }
        complete(system: system, user: text, completion: completion)
    }

    public static func summarize(_ transcript: String, completion: @escaping (String?) -> Void) {
        let system = "用简体中文总结下面的聊天记录。只根据给出的文字，列出要点。不要编造没有出现的内容。如果内容太少，就直接说明。"
        complete(system: system, user: transcript, completion: completion)
    }

    private static func chatURL(_ base: String) -> URL? {
        var trimmed = base.trimmingCharacters(in: .whitespacesAndNewlines)
        while trimmed.hasSuffix("/") {
            trimmed.removeLast()
        }
        if trimmed.hasSuffix("/chat/completions") {
            return URL(string: trimmed)
        }
        return URL(string: trimmed + "/chat/completions")
    }

    private static func parseContent(_ data: Data) -> String? {
        guard let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
              let choices = object["choices"] as? [[String: Any]],
              let message = choices.first?["message"] as? [String: Any] else {
            return nil
        }
        if let text = message["content"] as? String {
            let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
            return trimmed.isEmpty ? nil : trimmed
        }
        if let parts = message["content"] as? [[String: Any]] {
            let text = parts.compactMap { $0["text"] as? String }.joined()
            let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
            return trimmed.isEmpty ? nil : trimmed
        }
        return nil
    }
}
