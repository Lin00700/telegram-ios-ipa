import SwiftUI

struct SimulatorView: View {
    @EnvironmentObject private var store: RuleStore
    @State private var sender = ""
    @State private var bodyText = ""
    @State private var result: SMSClassification?

    var body: some View {
        Form {
            Section {
                Text("短信扩展不能把判断结果写回应用，所以这里用同一套规则当场演算。它不会发出短信。")
                    .font(.subheadline)
                TextField("发件人，例如 +8613800138000", text: $sender)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                TextField("短信正文", text: $bodyText, axis: .vertical)
                    .lineLimit(3...8)
                Button("判断") {
                    result = SMSClassifier(rules: store.rules, geo: store.geo).classify(sender: sender, body: bodyText)
                }
            }

            if let result {
                Section("结果") {
                    LabeledContent("系统将收到", value: result.action.title)
                    LabeledContent("本次规则", value: result.rule)
                    if result.action != result.ruleAction {
                        LabeledContent("打开总开关后", value: "\(result.ruleAction.title) · \(result.ruleName)")
                    }
                    Text(result.detail)
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .navigationTitle("模拟")
    }
}
