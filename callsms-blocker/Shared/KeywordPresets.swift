import Foundation

enum KeywordPresets {
    static let defaultBlockKeywords = [
        "贷款", "借款额度", "放款", "下款", "无抵押", "套现",
        "中奖", "幸运用户", "领取奖金", "彩票兑奖",
        "涉嫌洗钱", "安全账户", "法院传票", "检察院", "公安局备案",
        "账号被冻结", "银行卡冻结", "异常登录", "身份已泄露",
        "刷单", "日结工资", "代开发票", "加微信办理",
        "退款理赔", "点击链接验证",
        "博彩", "网投", "棋牌充值"
    ]

    static let defaultBlockRegexes = [
        "(公安|检察院|法院).{0,12}(涉嫌|传票|逮捕|冻结)",
        "(账户|银行卡|信用卡).{0,8}(冻结|异常|盗刷)",
        "(中奖|彩票|幸运用户).{0,8}(领取|奖金|缴税)"
    ]

    static let defaultWhitelistKeywords = ["验证码", "取件码", "快递", "运单"]

    static let defaultTransactionKeywords = [
        "入账", "支出", "余额", "交易提醒", "账单",
        "借记卡", "信用卡消费",
        "已签收", "派送中", "取件", "运单", "菜鸟", "顺丰", "京东快递", "快递"
    ]

    static let defaultPromotionKeywords = [
        "优惠券", "限时折扣", "促销", "回T退订", "退订回T",
        "会员日", "满减", "广告推广"
    ]

    static let defaultVirtualPrefixes = ["162", "165", "167", "170", "171"]

    static let deliveryHints = ["快递", "签收", "派送", "取件", "运单", "菜鸟", "顺丰", "京东"]

    static func parseList(_ text: String, maxCount: Int, maxLength: Int, minLength: Int) -> [String] {
        var result: [String] = []
        var seen = Set<String>()
        for piece in text.split(whereSeparator: { $0.isNewline || $0 == "，" || $0 == "," || $0 == "、" }) {
            let word = piece.trimmingCharacters(in: .whitespacesAndNewlines)
            guard word.count >= minLength, word.count <= maxLength else { continue }
            let key = word.lowercased()
            guard seen.insert(key).inserted else { continue }
            result.append(word)
            if result.count == maxCount { break }
        }
        return result
    }
}

enum RegexSafety {
    static func allows(_ pattern: String) -> Bool {
        guard (1...80).contains(pattern.count) else { return false }
        let quantifiers = pattern.filter { "+*?{".contains($0) }.count
        if quantifiers > 4 { return false }
        let banned = ["(.*)", "(.+)", "(.?)", "(.*)+", "(.+)+", "(.*)*", "(.+)*"]
        if banned.contains(where: { pattern.contains($0) }) { return false }
        return (try? NSRegularExpression(pattern: pattern, options: [])) != nil
    }
}
