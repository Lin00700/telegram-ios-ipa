import SwiftUI

struct SMSFilterView: View {
    @EnvironmentObject private var store: RuleStore
    @State private var messagesLinkFailed = false

    var body: some View {
        Form {
            if !store.groupAvailable {
                Section {
                    Text("没有可用的 App Group。模拟器仍可演算规则，但短信扩展读不到你在这里保存的开关。重签时要给主应用和两个扩展带上同一个 group。")
                        .foregroundStyle(.red)
                }
            }

            Section {
                Toggle("启用短信过滤", isOn: store.binding(\.smsEnabled))
            } footer: {
                Text("关闭时，扩展对每条未知短信都返回「不分类」，不会把短信丢进垃圾箱。系统里仍要手动选中本应用，而且全机只能有一个短信过滤扩展。")
            }

            Section("系统开关") {
                Text("设置 > 信息 > 未知与过滤信息 > 过滤未知发件人，然后选择本应用。通讯录联系人和 iMessage 不会进入这个扩展。")
                Button("尝试打开「信息」设置") {
                    Task {
                        messagesLinkFailed = await !SettingsOpener.openMessagesSettings()
                    }
                }
                if messagesLinkFailed {
                    Text("系统没有接受跳转。请按上面的路径手动打开。")
                        .foregroundStyle(.secondary)
                }
            }

            Section {
                Toggle("拦截境外短信", isOn: store.binding(\.blockForeignSMS))
            } footer: {
                Text("发件人带有非 86 国家码，或发件人里含有字母、汉字时，标为垃圾。+86、86 和 11 位手机号按国内号码处理；10086、95 开头、106 端口号不当作境外。这只看系统显示的发件人，不能判断号码是不是伪造的。")
            }

            Section {
                Toggle("按省份 / 区号过滤", isOn: store.binding(\.provinceFilterEnabled))
                NavigationLink("省份（\(store.rules.blockedProvinces.count)）") { ProvincePicker() }
                NavigationLink("区号（\(store.rules.blockedAreaCodes.count)）") { AreaCodePicker() }
            } footer: {
                Text("省份会拦截归属该省的手机短信，以及该省座机。单独勾选区号会拦截这个区号的座机，以及号段表里标了这个区号的手机短信。来电拦截做不到同样的事。同一区号下的多个城市（例如 028）会显示在一起。")
            }

            Section {
                Toggle("只接收广东短信", isOn: store.binding(\.onlyGuangdongSMS))
            } footer: {
                Text("只放行归属广东的手机号和广东座机。其他省份、境外号码、端口号和字母发件人都会标为垃圾。白名单关键词和发件人白名单仍然优先，所以验证码可以留下来。这个模式只对短信有效，来电没有对应的白名单接口。")
            }

            Section {
                Toggle("拦截虚拟号段", isOn: store.binding(\.blockVirtualSMS))
                NavigationLink("编辑前缀") {
                    TextListEditor(
                        title: "虚拟号前缀",
                        footer: "每行一个，3 到 7 位，需以 1 开头。短信按前缀判断，不用展开成完整号码。",
                        initial: store.rules.virtualPrefixes,
                        preset: KeywordPresets.defaultVirtualPrefixes
                    ) { text in
                        store.replaceVirtualPrefixes(text)
                    }
                }
            } footer: {
                Text("默认包含 162、165、167、170、171。这些号段里也有正常用户，所以默认关闭。来电侧不能按这 3 位一次拦截，只能在数量上限内挑选 7 位号段。")
            }

            Section {
                Toggle("关键词与正则拦截", isOn: store.binding(\.keywordFilterEnabled))
                NavigationLink("拦截关键词") {
                    TextListEditor(
                        title: "拦截关键词",
                        footer: "每行一个，至少 2 个字。内置词库覆盖贷款、中奖、公检法、异常登录和刷单，可以改。",
                        initial: store.rules.blockKeywords,
                        preset: KeywordPresets.defaultBlockKeywords
                    ) { text in
                        store.replaceList(\.blockKeywords, text: text, maxCount: 200, minLength: 2)
                    }
                }
                NavigationLink("正则") {
                    TextListEditor(
                        title: "拦截正则",
                        footer: "每行一条。过长、无法编译，或包含嵌套通配的表达式会被丢掉。",
                        initial: store.rules.blockRegexes,
                        preset: KeywordPresets.defaultBlockRegexes
                    ) { text in
                        let dropped = store.replaceRegexes(text)
                        if dropped > 0 {
                            store.alertMessage = "有 \(dropped) 条正则没有保存。它们太长、无法编译，或包含不受限制的通配。"
                        }
                    }
                }
            } footer: {
                Text("命中后标为垃圾。垃圾是这几类里通常不响铃的一类。")
            }

            Section {
                Toggle("白名单关键词", isOn: store.binding(\.whitelistKeywordsEnabled))
                NavigationLink("编辑白名单关键词") {
                    TextListEditor(
                        title: "白名单关键词",
                        footer: "命中后直接放行，优先于境外、广东、省份、虚拟号和拦截关键词。",
                        initial: store.rules.whitelistKeywords,
                        preset: KeywordPresets.defaultWhitelistKeywords
                    ) { text in
                        store.replaceList(\.whitelistKeywords, text: text, maxCount: 100, minLength: 2)
                    }
                }
                Toggle("发件人白名单", isOn: store.binding(\.whitelistSendersEnabled))
                NavigationLink("编辑发件人") {
                    TextListEditor(
                        title: "发件人白名单",
                        footer: "每行一个号码或发件人名称。开关关闭时列表不生效。",
                        initial: store.rules.whitelistSenders,
                        preset: []
                    ) { text in
                        store.replaceList(\.whitelistSenders, text: text, maxCount: 500, minLength: 1)
                    }
                }
            } footer: {
                Text("用来避开验证码、取件码和快递被误伤。默认关闭，需要你自己打开。")
            }

            Section {
                Toggle("银行与快递归为交易信息", isOn: store.binding(\.routeTransaction))
                NavigationLink("交易关键词") {
                    TextListEditor(
                        title: "交易关键词",
                        footer: "只有没被标成垃圾时才会归为交易。交易信息仍可能通知。",
                        initial: store.rules.transactionKeywords,
                        preset: KeywordPresets.defaultTransactionKeywords
                    ) { text in
                        store.replaceList(\.transactionKeywords, text: text, maxCount: 100, minLength: 2)
                    }
                }
                Toggle("营销信息归为推广", isOn: store.binding(\.routePromotion))
                NavigationLink("推广关键词") {
                    TextListEditor(
                        title: "推广关键词",
                        footer: "推广信息仍可能通知。想静音就改用关键词拦截，让它变成垃圾。",
                        initial: store.rules.promotionKeywords,
                        preset: KeywordPresets.defaultPromotionKeywords
                    ) { text in
                        store.replaceList(\.promotionKeywords, text: text, maxCount: 100, minLength: 2)
                    }
                }
            } footer: {
                Text("垃圾短信通常不通知。交易和推广只是分类，系统仍可能提醒。")
            }
        }
        .navigationTitle("短信")
    }
}
