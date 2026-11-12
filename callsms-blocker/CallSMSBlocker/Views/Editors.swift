import SwiftUI

enum RegionOrder {
    static let provinces = [
        "北京", "天津", "河北", "山西", "内蒙古", "辽宁", "吉林", "黑龙江",
        "上海", "江苏", "浙江", "安徽", "福建", "江西", "山东", "河南",
        "湖北", "湖南", "广东", "广西", "海南", "重庆", "四川", "贵州",
        "云南", "西藏", "陕西", "甘肃", "青海", "宁夏", "新疆"
    ]

    static func sortedProvinces(_ names: [String]) -> [String] {
        names.sorted { left, right in
            let leftIndex = provinces.firstIndex(of: left) ?? 1_000
            let rightIndex = provinces.firstIndex(of: right) ?? 1_000
            if leftIndex != rightIndex { return leftIndex < rightIndex }
            return left < right
        }
    }
}

struct ProvincePicker: View {
    @EnvironmentObject private var store: RuleStore
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        List(RegionOrder.sortedProvinces(store.geo?.provinces ?? []), id: \.self) { province in
            Button {
                toggle(province)
            } label: {
                HStack {
                    Text(province)
                    Spacer()
                    if store.rules.blockedProvinces.contains(province) {
                        Image(systemName: "checkmark")
                    }
                }
            }
            .foregroundStyle(.primary)
        }
        .navigationTitle("选择省份")
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button("完成") { dismiss() }
            }
        }
    }

    private func toggle(_ province: String) {
        if store.rules.blockedProvinces.contains(province) {
            store.rules.blockedProvinces.removeAll { $0 == province }
        } else {
            store.rules.blockedProvinces.append(province)
        }
    }
}

struct AreaCodePicker: View {
    @EnvironmentObject private var store: RuleStore
    @Environment(\.dismiss) private var dismiss
    @State private var query = ""

    var body: some View {
        List(filtered, id: \.code) { area in
            Button {
                toggle(area.code)
            } label: {
                HStack {
                    VStack(alignment: .leading) {
                        Text(area.code)
                        Text("\(store.geo?.provinces[area.provinceIndex] ?? "") · \(area.city)")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                    Spacer()
                    if store.rules.blockedAreaCodes.contains(area.code) {
                        Image(systemName: "checkmark")
                    }
                }
            }
            .foregroundStyle(.primary)
        }
        .searchable(text: $query, prompt: "区号或城市")
        .navigationTitle("选择区号")
        .toolbar {
            ToolbarItem(placement: .confirmationAction) {
                Button("完成") { dismiss() }
            }
        }
    }

    private var filtered: [GeoDatabase.Area] {
        let areas = store.geo?.areas ?? []
        let needle = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !needle.isEmpty else { return areas }
        return areas.filter { area in
            let province = store.geo?.provinces[area.provinceIndex] ?? ""
            return area.code.contains(needle) || area.city.contains(needle) || province.contains(needle)
        }
    }

    private func toggle(_ code: String) {
        if store.rules.blockedAreaCodes.contains(code) {
            store.rules.blockedAreaCodes.removeAll { $0 == code }
        } else {
            store.rules.blockedAreaCodes.append(code)
        }
    }
}

struct TextListEditor: View {
    let title: String
    let footer: String
    let preset: String
    @State private var text: String
    var onSave: (String) -> Void
    @Environment(\.dismiss) private var dismiss

    init(title: String, footer: String, initial: [String], preset: [String], onSave: @escaping (String) -> Void) {
        self.title = title
        self.footer = footer
        self.preset = preset.joined(separator: "\n")
        _text = State(initialValue: initial.joined(separator: "\n"))
        self.onSave = onSave
    }

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 8) {
                Text(footer)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .padding(.horizontal)
                TextEditor(text: $text)
                    .font(.body)
                    .padding(.horizontal, 8)
            }
            .navigationTitle(title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("取消") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("保存") {
                        onSave(text)
                        dismiss()
                    }
                }
                ToolbarItem(placement: .bottomBar) {
                    Button("填入内置内容") { text = preset }
                }
            }
        }
    }
}

struct VirtualSegmentSearch: View {
    let prefixes: [String]
    var onPick: (String) -> Void
    @State private var query = ""
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        List(matches, id: \.self) { prefix in
            Button(prefix) {
                onPick(prefix)
                dismiss()
            }
        }
        .searchable(text: $query, prompt: "至少输入 3 位，例如 170")
        .navigationTitle("查找虚拟号段")
        .overlay {
            if matches.isEmpty {
                Text(emptyMessage)
                    .font(.footnote)
                    .foregroundStyle(.secondary)
                    .padding()
            }
        }
    }

    private var matches: [String] {
        let digits = query.filter { $0 >= "0" && $0 <= "9" }
        guard digits.count >= 3 else { return [] }
        return Array(prefixes.lazy.filter { $0.hasPrefix(digits) }.prefix(40))
    }

    private var emptyMessage: String {
        let digits = query.filter { $0 >= "0" && $0 <= "9" }
        if prefixes.isEmpty {
            return "安装包里没有虚拟号段清单。仍可以手动输入 162、165、167、170、171 开头的 7 位号段。"
        }
        if digits.count < 3 {
            return "输入至少 3 位数字后再查找。清单只覆盖 2023 年底已放号的号段。"
        }
        return "没有找到这个前缀。可以回到上一页手动输入 7 位号段。"
    }
}
