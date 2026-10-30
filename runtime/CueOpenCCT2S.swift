import Foundation

public final class CueOpenCCT2S {
    public static let shared = CueOpenCCT2S()

    private final class TrieNode {
        var children: [Character: TrieNode] = [:]
        var value: String?
    }

    private let normalization = TrieNode()
    private let phrases = TrieNode()
    private let extendedCharacters = TrieNode()
    private let characters = TrieNode()

    private init() {
        self.loadDictionary("CueOpenCC_CJK_Compatibility_Ideographs", into: self.normalization)
        self.loadDictionary("CueOpenCC_TSPhrases", into: self.phrases)
        self.loadDictionary("CueOpenCC_TSCharactersExt", into: self.extendedCharacters)
        self.loadDictionary("CueOpenCC_TSCharacters", into: self.characters)
    }

    public func convert(_ text: String) -> String {
        guard !text.isEmpty else {
            return text
        }
        let normalized = self.applyTrie(self.normalization, to: text)
        return self.applyConversionChain(to: normalized)
    }

    private func loadDictionary(_ resourceName: String, into root: TrieNode) {
        guard let url = Bundle.main.url(forResource: resourceName, withExtension: "txt"),
              let contents = try? String(contentsOf: url, encoding: .utf8) else {
            return
        }
        for line in contents.split(whereSeparator: \.isNewline) {
            guard !line.hasPrefix("#"),
                  let separator = line.firstIndex(of: "\t") else {
                continue
            }
            let key = String(line[..<separator])
            let valuesText = line[line.index(after: separator)...]
            guard !key.isEmpty,
                  let value = valuesText.split(whereSeparator: \.isWhitespace).first,
                  !value.isEmpty else {
                continue
            }
            self.insert(key: key, value: String(value), into: root)
        }
    }

    private func insert(key: String, value: String, into root: TrieNode) {
        guard !key.isEmpty else {
            return
        }
        var node = root
        for character in key {
            if let child = node.children[character] {
                node = child
            } else {
                let child = TrieNode()
                node.children[character] = child
                node = child
            }
        }
        node.value = value
    }

    private func longestMatch(in text: String, from start: String.Index, root: TrieNode) -> (end: String.Index, value: String)? {
        var index = start
        var node = root
        var best: (String.Index, String)?
        while index < text.endIndex, let child = node.children[text[index]] {
            node = child
            index = text.index(after: index)
            if let value = node.value {
                best = (index, value)
            }
        }
        guard let best else {
            return nil
        }
        return (best.0, best.1)
    }

    private func applyTrie(_ root: TrieNode, to text: String) -> String {
        var output = String()
        output.reserveCapacity(text.utf8.count)
        var index = text.startIndex
        while index < text.endIndex {
            if let match = self.longestMatch(in: text, from: index, root: root) {
                output.append(contentsOf: match.value)
                index = match.end
            } else {
                output.append(text[index])
                index = text.index(after: index)
            }
        }
        return output
    }

    private func applyConversionChain(to text: String) -> String {
        var output = String()
        output.reserveCapacity(text.utf8.count)
        var index = text.startIndex
        while index < text.endIndex {
            if let match = self.longestMatch(in: text, from: index, root: self.phrases) {
                output.append(contentsOf: match.value)
                index = match.end
            } else if let match = self.longestMatch(in: text, from: index, root: self.extendedCharacters) {
                output.append(contentsOf: match.value)
                index = match.end
            } else if let match = self.longestMatch(in: text, from: index, root: self.characters) {
                output.append(contentsOf: match.value)
                index = match.end
            } else {
                output.append(text[index])
                index = text.index(after: index)
            }
        }
        return output
    }
}
