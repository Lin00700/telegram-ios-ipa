import SwiftUI

struct CallBlockView: View {
    @EnvironmentObject private var store: RuleStore
    @State private var numberText = ""
    @State private var labelText = ""
    @State private var segmentText = ""
    @State private var virtualText = ""

    var body: some View {
        Form {
            limitations
            contactsGuidance
            master
            manualNumbers
            segments
            virtualSegments
        }
        .navigationTitle("来电")
        .onAppear { store.refreshCallStatus() }
    }

    private var plan: CallPlan {
        CallListBuilder.plan(for: store.rules)
    }

    private var limitations: some View {
        Section {
            VStack(alignment: .leading, spacing: 8) {
                Label("来电拦截做不到这些", systemImage: "exclamationmark.triangle")
                    .font(.headline)
                Text("系统只接受事先排好序的完整号码，没有按国家、省份、区号或通配符拦截的接口，电话打进来时也不会再问一次本应用。")
                Text("· 不能一键拦截全部境外来电\n· 不能拦截某一个省的全部手机号\n· 不能拦截整个座机区号，例如 010 或 0755\n· 不能做「只接广东来电」白名单\n· 不能识破伪造的来电显示，只按系统给出的号码处理")
                Text("不使用 iOS 18「实时来电显示查询」。那个能力需要苹果另行批准的托管权限和 PIR 服务器，自签安装用不了。")
            }
            .font(.subheadline)
        }
    }

    private var contactsGuidance: some View {
        Section {
            Toggle("只接通讯录来电", isOn: contactsBinding)
            Text("这是系统功能引导，不是本应用的黑名单。来电拦截扩展只能提交要拦截的号码，做不出「只有通讯录才响铃」的白名单。")
            Text("打开 iPhone 的「静音未知来电」后，通讯录联系人、你最近拨出过的号码，以及 Siri 建议会正常响铃，其他陌生号码会被静音。这些来电仍会出现在最近通话里。")
            Text("路径：设置 > 电话 > 静音未知来电")
                .fontWeight(.semibold)
            Button("打开「设置 > 电话」") {
                Task {
                    store.silenceLinkOpened = await SettingsOpener.openSilenceUnknownCallers()
                }
            }
            if store.silenceLinkOpened == false {
                Text("系统没有接受跳转链接。请按上面的三步手动打开「静音未知来电」。")
                    .foregroundStyle(.secondary)
            }
        } header: {
            Text("只接通讯录来电（系统功能引导）")
        } footer: {
            Text("本应用不读取、不修改通讯录。这个开关只记住你想使用系统静音，并尝试跳到「电话」设置。")
        }
    }

    private var contactsBinding: Binding<Bool> {
        Binding(
            get: { store.rules.contactsOnlyGuidanceEnabled },
            set: { store.setContactsGuidance($0) }
        )
    }

    private var master: some View {
        Section {
            Toggle("启用来电拦截", isOn: store.binding(\.callBlockingEnabled))
            Text(store.statusText)
                .font(.footnote)
                .foregroundStyle(.secondary)
            Button("打开「来电拦截与身份识别」") {
                store.openCallDirectorySettings()
            }
            Button("重新载入号码列表") {
                store.reloadCallDirectory()
            }
        } footer: {
            Text("总开关关闭时，扩展会清空已经提交的拦截和标注，不拦截任何号码。号码很多时，系统更新可能要一两分钟。请先在「设置 > 电话 > 来电拦截与身份识别」里打开本应用。")
        }
    }

    private var manualNumbers: some View {
        Section {
            TextField("完整号码", text: $numberText)
                .keyboardType(.phonePad)
            TextField("标注（只标注时填写）", text: $labelText)
            Button("加入拦截") { commit(store.addBlockedNumber(numberText)) }
            Button("只标注、不拦截") { commit(store.addLabel(raw: numberText, label: labelText)) }
            if store.rules.blockedNumbers.isEmpty {
                Text("还没有单独拦截的号码。")
                    .foregroundStyle(.secondary)
            }
            ForEach(store.rules.blockedNumbers, id: \.e164) { item in
                HStack {
                    VStack(alignment: .leading) {
                        Text(item.display)
                        Text(shown(item.e164))
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    Button("删除", role: .destructive) {
                        store.removeBlocked(e164: item.e164)
                    }
                }
            }
            if !store.rules.labeledNumbers.isEmpty {
                Text("标注")
                    .font(.headline)
            }
            ForEach(store.rules.labeledNumbers, id: \.e164) { item in
                HStack {
                    VStack(alignment: .leading) {
                        Text(item.display)
                        Text("\(shown(item.e164)) · \(item.label)")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    Button("删除", role: .destructive) {
                        store.removeLabel(e164: item.e164)
                    }
                }
            }
        } header: {
            Text("指定号码")
        } footer: {
            Text("短号能不能生效，取决于来电时系统显示的是不是同一个数字。境外号码请带 + 和国家码。")
        }
    }

    private var segments: some View {
        Section {
            Toggle("按 7 位号段展开拦截", isOn: segmentBinding)
            TextField("7 位号段，例如 1380013", text: $segmentText)
                .keyboardType(.numberPad)
            Button("加入号段") { commit(store.addSegment(segmentText)) }
            budget
            ForEach(store.rules.blockedSegments, id: \.self) { prefix in
                HStack {
                    Text(prefix)
                    Text("→ 10,000 个号码")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                    Spacer()
                    Button("删除", role: .destructive) { store.removeSegment(prefix) }
                }
            }
        } header: {
            Text("手机号段")
        } footer: {
            Text("一个 7 位号段会展开成 10,000 个带 86 的完整号码。不能用它拦截整个省，也不能拦截 010、0755 这种座机区号。")
        }
    }

    private var virtualSegments: some View {
        Section {
            Toggle("展开已选虚拟号段", isOn: virtualBinding)
            TextField("7 位虚拟号段", text: $virtualText)
                .keyboardType(.numberPad)
            Button("加入虚拟号段") { commit(store.addVirtualSegment(virtualText)) }
            NavigationLink("从 2023 年清单里查找") {
                VirtualSegmentSearch(prefixes: store.virtualPrefixes) { prefix in
                    commit(store.addVirtualSegment(prefix))
                }
            }
            ForEach(store.rules.virtualSegments, id: \.self) { prefix in
                HStack {
                    Text(prefix)
                    Spacer()
                    Button("删除", role: .destructive) { store.removeVirtualSegment(prefix) }
                }
            }
        } header: {
            Text("虚拟号段")
        } footer: {
            Text("短信可以按 170 这类前缀直接判断。来电必须展开成完整号码，所以和上面的号段共用 1,000,000 条上限。170/171/162/165/167 里也有正常用户。")
        }
    }

    private var budget: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("按当前开关将提交 \(plan.totalEntries) 条，上限 \(CallPlan.cap)。")
            Text("号段 \(plan.segmentCount) 个，号段以外的号码 \(max(0, plan.blockingCount - plan.segmentCount * CallPlan.numbersPerSegment)) 个，标注 \(plan.labelCount) 条。还可以再加约 \(plan.remainingSegments) 个号段。")
                .font(.footnote)
                .foregroundStyle(plan.overCap ? .red : .secondary)
        }
    }

    private var segmentBinding: Binding<Bool> {
        Binding(
            get: { store.rules.segmentBlockEnabled },
            set: { enabled in
                if let message = store.setSegmentBlockEnabled(enabled) {
                    store.alertMessage = message
                }
            }
        )
    }

    private var virtualBinding: Binding<Bool> {
        Binding(
            get: { store.rules.expandVirtualSegments },
            set: { enabled in
                if let message = store.setExpandVirtualSegments(enabled) {
                    store.alertMessage = message
                }
            }
        )
    }

    private func commit(_ message: String?) {
        if let message {
            store.alertMessage = message
        } else {
            numberText = ""
            labelText = ""
            segmentText = ""
            virtualText = ""
        }
    }

    private func shown(_ e164: String) -> String {
        e164.count >= 8 ? "+\(e164)" : e164
    }
}
