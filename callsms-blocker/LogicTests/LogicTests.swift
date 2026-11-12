import XCTest

final class CRC32Tests: XCTestCase {
    func testKnownVector() {
        XCTAssertEqual(CRC32.ieee(Data("123456789".utf8)), 0xCBF43926)
    }
}

final class PhoneNumberTests: XCTestCase {
    private let areas: Set<String> = ["010", "020", "0755"]

    func testDomesticMobiles() {
        XCTAssertEqual(PhoneNumber.parse("13800138000", areaCodes: areas).kind, .mobile(national: "13800138000"))
        XCTAssertEqual(PhoneNumber.parse("+86 138-0013-8000", areaCodes: areas).kind, .mobile(national: "13800138000"))
        XCTAssertEqual(PhoneNumber.parse("8613800138000", areaCodes: areas).kind, .mobile(national: "13800138000"))
        XCTAssertEqual(PhoneNumber.parse("008613800138000", areaCodes: areas).kind, .mobile(national: "13800138000"))
    }

    func testForeignAndServiceAndLandline() {
        XCTAssertEqual(PhoneNumber.parse("+44 7911 123456", areaCodes: areas).kind, .foreign(digits: "447911123456"))
        XCTAssertEqual(PhoneNumber.parse("00442079460958", areaCodes: areas).kind, .foreign(digits: "442079460958"))
        XCTAssertEqual(PhoneNumber.parse("BANK", areaCodes: areas).kind, .alphanumeric("BANK"))
        XCTAssertEqual(PhoneNumber.parse("10086", areaCodes: areas).kind, .service(national: "10086"))
        XCTAssertEqual(PhoneNumber.parse("95588", areaCodes: areas).kind, .service(national: "95588"))
        XCTAssertEqual(PhoneNumber.parse("106900001234", areaCodes: areas).kind, .service(national: "106900001234"))
        XCTAssertEqual(
            PhoneNumber.parse("0755-12345678", areaCodes: areas).kind,
            .landline(areaCode: "0755", subscriber: "12345678")
        )
        XCTAssertEqual(
            PhoneNumber.parse("01012345678", areaCodes: areas).kind,
            .landline(areaCode: "010", subscriber: "12345678")
        )
    }

    func testCallDigits() {
        XCTAssertEqual(PhoneNumber.callDigits(from: "13800138000", areaCodes: areas), "8613800138000")
        XCTAssertEqual(PhoneNumber.callDigits(from: "075512345678", areaCodes: areas), "8675512345678")
        XCTAssertEqual(PhoneNumber.callDigits(from: "+1 202 555 0123", areaCodes: areas), "12025550123")
    }
}

final class RuleDefaultsTests: XCTestCase {
    func testMissingKeysStayOff() throws {
        let rules = try JSONDecoder().decode(FilterRules.self, from: Data("{}".utf8))
        XCTAssertFalse(rules.smsEnabled)
        XCTAssertFalse(rules.blockForeignSMS)
        XCTAssertFalse(rules.provinceFilterEnabled)
        XCTAssertFalse(rules.onlyGuangdongSMS)
        XCTAssertFalse(rules.blockVirtualSMS)
        XCTAssertFalse(rules.keywordFilterEnabled)
        XCTAssertFalse(rules.whitelistKeywordsEnabled)
        XCTAssertFalse(rules.whitelistSendersEnabled)
        XCTAssertFalse(rules.routeTransaction)
        XCTAssertFalse(rules.routePromotion)
        XCTAssertFalse(rules.callBlockingEnabled)
        XCTAssertFalse(rules.segmentBlockEnabled)
        XCTAssertFalse(rules.expandVirtualSegments)
        XCTAssertFalse(rules.contactsOnlyGuidanceEnabled)
        XCTAssertEqual(rules.whitelistKeywords, KeywordPresets.defaultWhitelistKeywords)
    }
}

final class ClassifierTests: XCTestCase {
    func testForeignVirtualKeywordAndWhitelist() throws {
        let database = try Fixtures.database()
        var rules = FilterRules()
        rules.smsEnabled = true
        rules.blockForeignSMS = true
        let foreign = SMSClassifier(rules: rules, geo: database).classify(sender: "+447911123456", body: "hello")
        XCTAssertEqual(foreign.action, .junk)
        XCTAssertEqual(foreign.rule, "境外或非数字发件人")

        let mobile = SMSClassifier(rules: rules, geo: database).classify(sender: "13800138000", body: "hello")
        XCTAssertNotEqual(mobile.action, .junk)

        let service = SMSClassifier(rules: rules, geo: database).classify(sender: "10086", body: "hello")
        XCTAssertNotEqual(service.action, .junk)

        rules.blockVirtualSMS = true
        let virtual = SMSClassifier(rules: rules, geo: database).classify(sender: "17012345678", body: "hello")
        XCTAssertEqual(virtual.action, .junk)
        XCTAssertTrue(virtual.rule.contains("虚拟号段"))

        rules.whitelistKeywordsEnabled = true
        let kept = SMSClassifier(rules: rules, geo: database).classify(sender: "+447911123456", body: "您的验证码是 123456")
        XCTAssertEqual(kept.action, .allow)
        XCTAssertTrue(kept.rule.contains("白名单关键词"))

        rules.keywordFilterEnabled = true
        rules.blockForeignSMS = false
        rules.blockVirtualSMS = false
        rules.whitelistKeywordsEnabled = false
        let scam = SMSClassifier(rules: rules, geo: database).classify(sender: "13800138000", body: "恭喜您中奖了")
        XCTAssertEqual(scam.action, .junk)
    }

    func testOnlyGuangdongAndMasterSwitch() throws {
        let database = try Fixtures.database()
        let guangdong = try XCTUnwrap(database.firstPrefix { $0 == "广东" })
        let elsewhere = try XCTUnwrap(database.firstPrefix { $0 != "广东" })
        var rules = FilterRules()
        rules.smsEnabled = true
        rules.onlyGuangdongSMS = true
        let classifier = SMSClassifier(rules: rules, geo: database)
        let allowed = classifier.classify(sender: Self.national(guangdong), body: "你好")
        XCTAssertNotEqual(allowed.action, .junk)
        let blocked = classifier.classify(sender: Self.national(elsewhere), body: "你好")
        XCTAssertEqual(blocked.action, .junk)
        XCTAssertEqual(blocked.rule, "只接收广东短信")

        rules.smsEnabled = false
        rules.blockForeignSMS = true
        let dormant = SMSClassifier(rules: rules, geo: database).classify(sender: "+447911123456", body: "hi")
        XCTAssertEqual(dormant.action, .none)
        XCTAssertEqual(dormant.ruleAction, .junk)
    }

    func testTransactionDoesNotOverrideJunk() throws {
        let database = try Fixtures.database()
        var rules = FilterRules()
        rules.smsEnabled = true
        rules.keywordFilterEnabled = true
        rules.routeTransaction = true
        let result = SMSClassifier(rules: rules, geo: database).classify(sender: "95588", body: "您的贷款已放款，余额已更新")
        XCTAssertEqual(result.action, .junk)
    }

    private static func national(_ prefix: Int) -> String {
        String(prefix) + "0000"
    }
}

final class CallListTests: XCTestCase {
    func testSegmentExpansionIsSortedAndDeduplicated() {
        var rules = FilterRules()
        rules.callBlockingEnabled = true
        rules.segmentBlockEnabled = true
        rules.blockedSegments = ["1380013", "1380013"]
        rules.blockedNumbers = [StoredNumber(display: "13800138000", e164: "8613800138000")]
        let plan = CallListBuilder.plan(for: rules)
        XCTAssertEqual(plan.segmentCount, 1)
        XCTAssertEqual(plan.blockingCount, 10_000)
        XCTAssertFalse(plan.overCap)

        var numbers: [Int64] = []
        CallListBuilder.enumerateBlocking(rules) { numbers.append($0) }
        XCTAssertEqual(numbers.count, 10_000)
        XCTAssertEqual(numbers.first, Int64(8_613_800_130_000))
        XCTAssertEqual(numbers.last, Int64(8_613_800_139_999))
        XCTAssertEqual(numbers.filter { $0 == Int64(8_613_800_138_000) }.count, 1)
        XCTAssertTrue(zip(numbers, numbers.dropFirst()).allSatisfy { $0 < $1 })
    }

    func testHardCapSubmitsNothing() {
        var rules = FilterRules()
        rules.callBlockingEnabled = true
        rules.segmentBlockEnabled = true
        rules.blockedSegments = (0..<101).map { String(1_700_000 + $0) }
        let plan = CallListBuilder.plan(for: rules)
        XCTAssertTrue(plan.overCap)
        XCTAssertGreaterThan(plan.totalEntries, CallPlan.cap)
        var emitted = 0
        CallListBuilder.enumerateBlocking(rules) { _ in emitted += 1 }
        XCTAssertEqual(emitted, 0)
    }

    func testGuidanceToggleDoesNotCreateEntries() {
        var rules = FilterRules()
        rules.callBlockingEnabled = true
        rules.contactsOnlyGuidanceEnabled = true
        let plan = CallListBuilder.plan(for: rules)
        XCTAssertEqual(plan.totalEntries, 0)
        var emitted = 0
        CallListBuilder.enumerateBlocking(rules) { _ in emitted += 1 }
        CallListBuilder.enumerateLabels(rules) { _, _ in emitted += 1 }
        XCTAssertEqual(emitted, 0)
    }

    func testMasterSwitchOffSubmitsNothingButStillCounts() {
        var rules = FilterRules()
        rules.segmentBlockEnabled = true
        rules.blockedSegments = ["1380013"]
        let plan = CallListBuilder.plan(for: rules)
        XCTAssertEqual(plan.blockingCount, 10_000)
        var emitted = 0
        CallListBuilder.enumerateBlocking(rules) { _ in emitted += 1 }
        XCTAssertEqual(emitted, 0)
    }
}

final class GeoDatabaseTests: XCTestCase {
    func testTableLooksUpKnownPrefixes() throws {
        let database = try Fixtures.database()
        XCTAssertTrue(database.provinces.contains("广东"))
        XCTAssertTrue(database.provinces.contains("北京"))
        let jinan = try XCTUnwrap(database.lookup(prefix7: 1_300_000))
        XCTAssertEqual(jinan.province, "山东")
        XCTAssertEqual(jinan.areaCode, "0531")
        let shenzhen = try XCTUnwrap(database.areas.first { $0.code == "0755" })
        XCTAssertEqual(database.provinces[shenzhen.provinceIndex], "广东")
        XCTAssertTrue(shenzhen.city.contains("深圳"))
        let xilin = try XCTUnwrap(database.lookup(prefix7: 1_303_045))
        XCTAssertEqual(xilin.province, "内蒙古")
        XCTAssertEqual(xilin.areaCode, "0479")
        XCTAssertNil(database.lookup(prefix7: 1_000_000))
        let guangdong = try XCTUnwrap(database.firstPrefix { $0 == "广东" })
        XCTAssertEqual(database.lookup(prefix7: guangdong)?.province, "广东")
    }
}

private enum Fixtures {
    static func database() throws -> GeoDatabase {
        let bundle = Bundle(for: GeoDatabaseTests.self)
        let url = try XCTUnwrap(bundle.url(forResource: "prefix_ranges", withExtension: "dat"))
        return try GeoDatabase(contentsOf: url)
    }
}
