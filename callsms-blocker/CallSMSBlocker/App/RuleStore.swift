import CallKit
import Foundation
import SwiftUI

@MainActor
final class RuleStore: ObservableObject {
    @Published var rules: FilterRules {
        didSet { handleChange(from: oldValue) }
    }
    @Published var groupAvailable: Bool
    @Published var statusText = "还没有检查来电拦截扩展"
    @Published var alertMessage: String?
    @Published var silenceLinkOpened: Bool?
    let geo: GeoDatabase?
    let virtualPrefixes: [String]
    private var ready = false

    init() {
        geo = GeoDatabase.bundled()
        virtualPrefixes = Self.loadVirtualPrefixes()
        if let url = RuleFile.fileURL(), let data = try? Data(contentsOf: url) {
            rules = RuleFile.load(from: data)
            groupAvailable = true
        } else if RuleFile.containerURL() != nil {
            rules = FilterRules()
            groupAvailable = true
        } else {
            rules = FilterRules()
            groupAvailable = false
        }
        ready = true
        if groupAvailable {
            save()
        }
    }

    func binding<Value>(_ keyPath: WritableKeyPath<FilterRules, Value>) -> Binding<Value> {
        Binding(
            get: { self.rules[keyPath: keyPath] },
            set: { newValue in self.rules[keyPath: keyPath] = newValue }
        )
    }

    func setContactsGuidance(_ enabled: Bool) {
        rules.contactsOnlyGuidanceEnabled = enabled
        guard enabled else {
            silenceLinkOpened = nil
            return
        }
        Task {
            silenceLinkOpened = await SettingsOpener.openSilenceUnknownCallers()
        }
    }

    func setSegmentBlockEnabled(_ enabled: Bool) -> String? {
        guard enabled else {
            rules.segmentBlockEnabled = false
            return nil
        }
        var copy = rules
        copy.segmentBlockEnabled = true
        return commitCallChange(copy)
    }

    func setExpandVirtualSegments(_ enabled: Bool) -> String? {
        guard enabled else {
            rules.expandVirtualSegments = false
            return nil
        }
        var copy = rules
        copy.expandVirtualSegments = true
        return commitCallChange(copy)
    }

    func addBlockedNumber(_ raw: String) -> String? {
        guard let e164 = normalizedCallNumber(raw) else {
            return "请输入完整号码。中国大陆手机号写 11 位；座机带区号；境外号码以 + 和国家码开头。"
        }
        guard !rules.blockedNumbers.contains(where: { $0.e164 == e164 }) else {
            return "这个号码已经在拦截列表里。"
        }
        var copy = rules
        copy.blockedNumbers.append(StoredNumber(display: cleaned(raw), e164: e164))
        return commitCallChange(copy)
    }

    func addLabel(raw: String, label: String) -> String? {
        let trimmedLabel = label.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedLabel.isEmpty else { return "请填写来电上要显示的标注。" }
        guard let e164 = normalizedCallNumber(raw) else {
            return "请输入完整号码。中国大陆手机号写 11 位；座机带区号；境外号码以 + 和国家码开头。"
        }
        var copy = rules
        copy.labeledNumbers.removeAll { $0.e164 == e164 }
        copy.labeledNumbers.append(LabeledNumber(display: cleaned(raw), e164: e164, label: String(trimmedLabel.prefix(24))))
        return commitCallChange(copy)
    }

    func removeBlocked(e164: String) {
        rules.blockedNumbers.removeAll { $0.e164 == e164 }
    }

    func removeLabel(e164: String) {
        rules.labeledNumbers.removeAll { $0.e164 == e164 }
    }

    func addSegment(_ raw: String) -> String? {
        let prefix = digits(raw)
        guard PhoneNumber.isPrefix7(prefix) else { return "请输入 7 位手机号段，例如 1380013。第一位必须是 1。" }
        guard !rules.blockedSegments.contains(prefix) else { return "这个号段已经在列表里。" }
        var copy = rules
        copy.blockedSegments.append(prefix)
        return commitCallChange(copy)
    }

    func addVirtualSegment(_ raw: String) -> String? {
        let prefix = digits(raw)
        guard PhoneNumber.isPrefix7(prefix), PhoneNumber.isVirtualFamily(prefix) else {
            return "虚拟号段须是 162、165、167、170 或 171 开头的 7 位数字。"
        }
        guard !rules.virtualSegments.contains(prefix) else { return "这个虚拟号段已经在列表里。" }
        var copy = rules
        copy.virtualSegments.append(prefix)
        return commitCallChange(copy)
    }

    func removeSegment(_ prefix: String) {
        rules.blockedSegments.removeAll { $0 == prefix }
    }

    func removeVirtualSegment(_ prefix: String) {
        rules.virtualSegments.removeAll { $0 == prefix }
    }

    func replaceList(_ keyPath: WritableKeyPath<FilterRules, [String]>, text: String, maxCount: Int, minLength: Int) {
        rules[keyPath: keyPath] = KeywordPresets.parseList(text, maxCount: maxCount, maxLength: 40, minLength: minLength)
    }

    func replaceRegexes(_ text: String) -> Int {
        var kept: [String] = []
        var dropped = 0
        let pieces = text.split(whereSeparator: { $0.isNewline || $0 == "，" || $0 == "," })
        for piece in pieces {
            let pattern = piece.trimmingCharacters(in: .whitespacesAndNewlines)
            guard !pattern.isEmpty else { continue }
            if RegexSafety.allows(pattern), kept.count < 30 {
                kept.append(pattern)
            } else {
                dropped += 1
            }
        }
        rules.blockRegexes = kept
        return dropped
    }

    func replaceVirtualPrefixes(_ text: String) {
        rules.virtualPrefixes = KeywordPresets.parseList(text, maxCount: 30, maxLength: 7, minLength: 3).filter {
            $0.allSatisfy { $0 >= "0" && $0 <= "9" } && $0.first == "1"
        }
    }

    func refreshCallStatus() {
        let identifier = AppIdentity.callDirectoryExtensionID
        CXCallDirectoryManager.sharedInstance.getEnabledStatusForExtension(withIdentifier: identifier) { status, error in
            Task { @MainActor in
                if let error {
                    self.statusText = "无法读取扩展状态：\(Self.describe(error))"
                    return
                }
                switch status {
                case .enabled:
                    self.statusText = "系统已打开来电拦截扩展。"
                case .disabled:
                    self.statusText = "扩展未启用。请到「设置 > 电话 > 来电拦截与身份识别」打开本应用。"
                default:
                    self.statusText = "扩展状态未知。请到系统设置里确认开关。"
                }
            }
        }
    }

    func reloadCallDirectory() {
        let identifier = AppIdentity.callDirectoryExtensionID
        statusText = "正在让系统重新读取号码列表…"
        CXCallDirectoryManager.sharedInstance.reloadExtension(withIdentifier: identifier) { error in
            Task { @MainActor in
                if let error {
                    self.statusText = "列表没有更新：\(Self.describe(error))"
                } else {
                    self.refreshCallStatus()
                    self.statusText = "系统已接受这次更新。号段很多时，电话 App 可能还要一两分钟才生效。"
                }
            }
        }
    }

    func openCallDirectorySettings() {
        CXCallDirectoryManager.sharedInstance.openSettings { error in
            Task { @MainActor in
                if let error {
                    self.alertMessage = "无法打开系统设置：\(Self.describe(error))。请手动前往「设置 > 电话 > 来电拦截与身份识别」。"
                }
            }
        }
    }

    func save() {
        guard groupAvailable, let url = RuleFile.fileURL() else { return }
        do {
            let data = try RuleFile.encode(rules)
            try data.write(to: url, options: .atomic)
        } catch {
            alertMessage = "规则没能写入 App Group。扩展仍会使用上一次成功保存的内容。"
        }
    }

    private func handleChange(from old: FilterRules) {
        guard ready else { return }
        save()
        if callPayloadChanged(old, rules) {
            reloadCallDirectory()
        }
    }

    private func callPayloadChanged(_ old: FilterRules, _ new: FilterRules) -> Bool {
        old.callBlockingEnabled != new.callBlockingEnabled
            || old.blockedNumbers != new.blockedNumbers
            || old.labeledNumbers != new.labeledNumbers
            || old.segmentBlockEnabled != new.segmentBlockEnabled
            || old.blockedSegments != new.blockedSegments
            || old.expandVirtualSegments != new.expandVirtualSegments
            || old.virtualSegments != new.virtualSegments
    }

    private func commitCallChange(_ copy: FilterRules) -> String? {
        if CallListBuilder.plan(for: copy).overCap {
            return "这样会超过 1,000,000 条上限。每个 7 位号段会展开成 10,000 个完整号码，大约最多 100 个号段。"
        }
        rules = copy
        return nil
    }

    private func normalizedCallNumber(_ raw: String) -> String? {
        guard let digits = PhoneNumber.callDigits(from: raw, areaCodes: geo?.areaCodes ?? []), let number = Int64(digits), number > 0 else {
            return nil
        }
        return digits
    }

    private func cleaned(_ raw: String) -> String {
        String(raw.trimmingCharacters(in: .whitespacesAndNewlines).prefix(40))
    }

    private func digits(_ raw: String) -> String {
        raw.filter { $0 >= "0" && $0 <= "9" }
    }

    private static func loadVirtualPrefixes() -> [String] {
        guard let url = Bundle.main.url(forResource: "virtual_prefixes", withExtension: "txt"),
              let text = try? String(contentsOf: url, encoding: .utf8) else {
            return []
        }
        return text.split(whereSeparator: \.isNewline).map(String.init)
    }

    private static func describe(_ error: Error) -> String {
        let nsError = error as NSError
        guard nsError.domain == CXErrorDomainCallDirectoryManager,
              let code = CXErrorCodeCallDirectoryManagerError.Code(rawValue: nsError.code) else {
            return "系统返回了错误（\(nsError.domain) \(nsError.code)）"
        }
        switch code {
        case .noExtensionFound:
            return "找不到来电拦截扩展。安装包需要同时带上主应用和 CallDirectory，并用同一个证书签名"
        case .extensionDisabled:
            return "请先在「设置 > 电话 > 来电拦截与身份识别」打开本应用"
        case .entriesOutOfOrder:
            return "号码没有按升序提交"
        case .duplicateEntries:
            return "号码列表里有重复项"
        case .maximumEntriesExceeded:
            return "超过了系统能接收的条数"
        case .currentlyLoading:
            return "系统正在加载上一次的列表，请稍后再试"
        case .loadingInterrupted:
            return "加载被打断，请再试一次"
        default:
            return "错误代码 \(nsError.code)"
        }
    }
}
