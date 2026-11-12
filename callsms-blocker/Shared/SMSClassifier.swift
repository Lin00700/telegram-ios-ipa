import Foundation

enum SMSAction: String, Equatable {
    case none
    case allow
    case junk
    case transaction
    case promotion

    var title: String {
        switch self {
        case .none: return "不分类"
        case .allow: return "放行"
        case .junk: return "垃圾"
        case .transaction: return "交易"
        case .promotion: return "推广"
        }
    }
}

enum SMSTopic: Equatable {
    case none
    case finance
    case orders
    case promotion
}

struct SMSClassification: Equatable {
    var action: SMSAction
    var rule: String
    var detail: String
    var topic: SMSTopic
    /// What the enabled rules would do if the master switch were on.
    var ruleAction: SMSAction
    var ruleName: String

    static func untouched(detail: String) -> SMSClassification {
        SMSClassification(action: .none, rule: "未命中规则", detail: detail, topic: .none, ruleAction: .none, ruleName: "未命中规则")
    }
}

struct SMSClassifier {
    var rules: FilterRules
    var geo: GeoDatabase?

    func classify(sender: String?, body: String?) -> SMSClassification {
        let evaluated = evaluate(sender: sender, body: body)
        guard rules.smsEnabled else {
            return SMSClassification(
                action: .none,
                rule: "短信过滤总开关关闭",
                detail: evaluated.detail + "\n总开关关闭，扩展实际返回「不分类」。上面是打开后会命中的规则。",
                topic: .none,
                ruleAction: evaluated.action,
                ruleName: evaluated.rule
            )
        }
        return evaluated
    }

    private func evaluate(sender: String?, body: String?) -> SMSClassification {
        let senderText = sender ?? ""
        let bodyText = body ?? ""
        let areaCodes = geo?.areaCodes ?? []
        let parsed = PhoneNumber.parse(senderText, areaCodes: areaCodes)
        let hit = region(of: parsed)
        let detail = detailText(parsed: parsed, hit: hit)

        if rules.whitelistSendersEnabled && !rules.whitelistSenders.isEmpty {
            let key = PhoneNumber.senderKey(senderText, areaCodes: areaCodes)
            let allowed = rules.whitelistSenders.contains { PhoneNumber.senderKey($0, areaCodes: areaCodes) == key }
            if allowed {
                return make(.allow, "发件人白名单", detail, .none)
            }
        }

        if rules.whitelistKeywordsEnabled, let word = firstKeyword(in: bodyText, list: rules.whitelistKeywords) {
            return make(.allow, "白名单关键词「\(word)」", detail, .none)
        }

        if rules.onlyGuangdongSMS {
            if geo == nil {
                // Without the prefix table we cannot prove a sender is in Guangdong,
                // so this rule stays idle instead of junking every message.
            } else if !isGuangdong(parsed, hit: hit) {
                return make(.junk, "只接收广东短信", detail, .none)
            }
        }

        if rules.blockForeignSMS && isForeignLike(parsed.kind) {
            return make(.junk, "境外或非数字发件人", detail, .none)
        }

        if rules.provinceFilterEnabled, let hit, isSelectedRegion(hit) {
            return make(.junk, "省份或区号过滤", detail, .none)
        }

        if rules.blockVirtualSMS, case .mobile(let national) = parsed.kind {
            if let prefix = rules.virtualPrefixes.first(where: { isVirtualPrefix($0) && national.hasPrefix($0) }) {
                return make(.junk, "虚拟号段 \(prefix)", detail, .none)
            }
        }

        if rules.keywordFilterEnabled {
            if let word = firstKeyword(in: bodyText, list: rules.blockKeywords) {
                return make(.junk, "关键词「\(word)」", detail, .none)
            }
            if let pattern = firstRegex(in: bodyText, patterns: rules.blockRegexes) {
                return make(.junk, "正则「\(pattern)」", detail, .none)
            }
        }

        if rules.routeTransaction, let word = firstKeyword(in: bodyText, list: rules.transactionKeywords) {
            let topic: SMSTopic = KeywordPresets.deliveryHints.contains(where: { word.contains($0) }) ? .orders : .finance
            return make(.transaction, "交易关键词「\(word)」", detail, topic)
        }

        if rules.routePromotion, let word = firstKeyword(in: bodyText, list: rules.promotionKeywords) {
            return make(.promotion, "推广关键词「\(word)」", detail, .promotion)
        }

        return make(.none, "未命中规则", detail, .none)
    }

    private func make(_ action: SMSAction, _ rule: String, _ detail: String, _ topic: SMSTopic) -> SMSClassification {
        SMSClassification(action: action, rule: rule, detail: detail, topic: topic, ruleAction: action, ruleName: rule)
    }

    private func region(of parsed: ParsedSender) -> GeoHit? {
        switch parsed.kind {
        case .mobile(let national):
            guard let prefix = Int(national.prefix(7)) else { return nil }
            return geo?.lookup(prefix7: prefix)
        case .landline(let areaCode, _):
            return geo?.lookup(areaCode: areaCode)
        default:
            return nil
        }
    }

    private func isGuangdong(_ parsed: ParsedSender, hit: GeoHit?) -> Bool {
        switch parsed.kind {
        case .mobile, .landline:
            return hit?.province == "广东"
        default:
            return false
        }
    }

    private func isSelectedRegion(_ hit: GeoHit) -> Bool {
        rules.blockedProvinces.contains(hit.province) || rules.blockedAreaCodes.contains(hit.areaCode)
    }

    private func isForeignLike(_ kind: ParsedSender.Kind) -> Bool {
        switch kind {
        case .foreign, .alphanumeric:
            return true
        default:
            return false
        }
    }

    private func isVirtualPrefix(_ prefix: String) -> Bool {
        guard (3...7).contains(prefix.count) else { return false }
        return prefix.allSatisfy { $0 >= "0" && $0 <= "9" } && prefix.first == "1"
    }

    private func firstKeyword(in body: String, list: [String]) -> String? {
        guard !body.isEmpty else { return nil }
        let haystack = body.prefix(2000).lowercased()
        for word in list {
            let key = word.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
            guard key.count >= 2, haystack.contains(key) else { continue }
            return word
        }
        return nil
    }

    private func firstRegex(in body: String, patterns: [String]) -> String? {
        guard !body.isEmpty else { return nil }
        let sample = String(body.prefix(500))
        let range = NSRange(sample.startIndex..<sample.endIndex, in: sample)
        for pattern in patterns.prefix(30) {
            guard RegexSafety.allows(pattern), let expression = try? NSRegularExpression(pattern: pattern) else { continue }
            if expression.firstMatch(in: sample, options: [], range: range) != nil {
                return pattern
            }
        }
        return nil
    }

    private func detailText(parsed: ParsedSender, hit: GeoHit?) -> String {
        var lines = ["号码类型：\(parsed.summary)"]
        if let hit {
            lines.append("归属：\(hit.summary)")
        } else if geo == nil {
            lines.append("归属：号段表没有载入，省份和区号规则不会判断")
        } else {
            lines.append("归属：号段表里没有这条号码")
        }
        if case .landline(let areaCode, _) = parsed.kind, let hit, hit.city.contains("、") || hit.city.hasSuffix("等") {
            lines.append("区号 \(areaCode) 覆盖多个城市，这里显示该区号的主要城市。")
        }
        return lines.joined(separator: "\n")
    }
}
