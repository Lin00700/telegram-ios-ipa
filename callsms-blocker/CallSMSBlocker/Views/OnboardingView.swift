import SwiftUI

struct OnboardingView: View {
    var showsDone = false
    var onDone: () -> Void = {}

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                Text("这是装在你自己手机上的短信过滤和来电黑名单。所有开关默认关闭。它不联网，也不上传短信或通话。")

                group("短信过滤") {
                    Text("系统路径：设置 > 信息 > 未知与过滤信息 > 过滤未知发件人，选择本应用。")
                    Text("全机同时只能启用一个短信过滤扩展。只有不在通讯录里的短信和彩信会进来，而且扩展必须当场给出结果。它不能联网，也不能把短信写进共享目录，所以请用「模拟」页查看命中了哪条规则。")
                    Text("垃圾短信通常不通知。交易和推广只是分类，仍可能提醒。")
                }

                group("来电拦截") {
                    Text("系统路径：设置 > 电话 > 来电拦截与身份识别，打开本应用。然后回到应用里打开总开关，让它重新载入号码。")
                    Text("这里只能提交完整号码。不能一键拦截境外来电，不能拦截整个省或整个座机区号，也不能做「只接广东来电」。它也不识破伪造的来电显示。")
                    Text("不使用 iOS 18 实时来电显示查询，因为那需要付费开发者计划里另行批准的托管权限和 PIR 服务器，自签无法使用。")
                }

                group("只接通讯录来电") {
                    Text("应用自己做不到通讯录白名单。请打开系统开关：设置 > 电话 > 静音未知来电。")
                    Text("打开后，通讯录联系人、你最近拨出过的号码和 Siri 建议会响铃，其他陌生号码静音。来电页里的同名开关只会跳转到这里，并写明它不是本应用的过滤规则。")
                }

                group("签名") {
                    Text("安装包是未签名的。用全能签和你自己的证书给主应用、短信过滤扩展、来电拦截扩展签上同一个身份，并保留 App Group。免费证书大约 7 天后过期，过期后两个扩展会失效。")
                    DataSourceNote()
                }

                if showsDone {
                    Button("开始使用", action: onDone)
                        .buttonStyle(.borderedProminent)
                }
            }
            .padding()
        }
        .navigationTitle("说明")
    }

    private func group(_ title: String, @ViewBuilder content: () -> some View) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title).font(.headline)
            content()
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
    }
}

private struct DataSourceNote: View {
    var body: some View {
        Text(note)
    }

    private var note: String {
        guard let url = Bundle.main.url(forResource: "SOURCE", withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let object = try? JSONSerialization.jsonObject(with: data) as? [String: Any] else {
            return "手机号归属地是随应用打包的本地号段表。"
        }
        let version = object["upstream_version_header"] as? String ?? ""
        let ranges = object["ranges"] as? Int ?? 0
        return "手机号归属地来自 ls0f/phone 的 phone.dat（数据头 \(version)，README 声明为 MIT），压缩成 \(ranges) 段区间。2024 年以后新放出来的号段可能查不到。"
    }
}
