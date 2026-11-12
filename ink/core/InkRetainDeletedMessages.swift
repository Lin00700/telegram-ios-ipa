import Foundation
import Postbox

private let inkRetainLock = NSLock()

func inkAntiRecallEnabled() -> Bool {
    return UserDefaults.standard.bool(forKey: "ink.antiRecall.enabled")
}

private func inkRetentionURL() -> URL {
    let directory = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        .appendingPathComponent("Ink", isDirectory: true)
    try? FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
    return directory.appendingPathComponent("message-retention.json")
}

private func inkMessageKey(_ id: MessageId) -> String {
    return "\(id.peerId.toInt64()):\(id.namespace):\(id.id)"
}

func inkRememberRecalledMessage(transaction: Transaction, id: MessageId) {
    let text = transaction.getMessage(id)?.text ?? ""
    inkWriteRetention(key: inkMessageKey(id), kind: "recalled", text: text)
}

func inkRememberPreEditText(transaction: Transaction, id: MessageId, updated: StoreMessage) {
    guard let previous = transaction.getMessage(id) else {
        return
    }
    if previous.text == updated.text {
        return
    }
    inkWriteRetention(key: inkMessageKey(id), kind: "edit", text: previous.text)
}

private func inkWriteRetention(key: String, kind: String, text: String) {
    inkRetainLock.lock()
    defer { inkRetainLock.unlock() }
    let url = inkRetentionURL()
    var root: [String: Any] = [:]
    if let data = try? Data(contentsOf: url),
       let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] {
        root = object
    }
    if kind == "recalled" {
        var recalled = root["recalled"] as? [String] ?? []
        if !recalled.contains(key) {
            recalled.append(key)
        }
        if recalled.count > 2000 {
            recalled.removeFirst(recalled.count - 2000)
        }
        root["recalled"] = recalled
    } else {
        var edits = root["edits"] as? [String: String] ?? [:]
        edits[key] = String(text.prefix(4000))
        if edits.count > 800 {
            let overflow = edits.count - 800
            for old in Array(edits.keys.prefix(overflow)) {
                edits.removeValue(forKey: old)
            }
        }
        root["edits"] = edits
    }
    guard let data = try? JSONSerialization.data(withJSONObject: root) else {
        return
    }
    try? data.write(to: url, options: .atomic)
}
