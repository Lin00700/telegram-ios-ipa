# 来电短信过滤

一个装在自己手机上的短信过滤和来电黑名单。界面是简体中文。所有过滤开关默认关闭。

主应用把规则写进 App Group。短信过滤扩展和来电拦截扩展只读这份规则。短信扩展不联网，也不把短信写回共享目录。

最低系统是 iOS 16。IPA 由 GitHub Actions 在 macOS 上打出，未签名，用全能签和你自己的证书重签。本机不需要打 IPA。

## 目录

```
callsms-blocker/
  CallSMSBlocker/            SwiftUI 主应用
  MessageFilter/             ILMessageFilterExtension
  CallDirectory/             CXCallDirectoryProvider
  Shared/                    规则、号码归一化、号段表、分类器
  Resources/                 压缩后的 7 位号段表
  LogicTests/                不依赖模拟器的逻辑测试
  scripts/build-unsigned-ipa.sh
  INSTALL.md
CallSMSBlocker.xcodeproj
```

工作流是 `.github/workflows/build-callsms-ipa.yml`。它只构建这个目录，不改 Telegram 客户端，也不改 xash-cs16。

## 怎么构建

在 GitHub 上打开 Actions → **Build CallSMS unsigned IPA** → Run workflow。

可选输入：

- `app_display_name`，默认「来电短信过滤」
- `app_bundle_id`，默认 `com.lin00700.callsmsblocker`

运行器标签是 `xcode-27`，和本仓库的 unsigned IPA 工作流相同。先在 Ubuntu 上跑契约测试和号段表测试，再在 macOS 上编译逻辑测试并打未签名 IPA。

产物在同一次运行的 artifact 里：

- `CallSMSBlocker-unsigned.ipa`
- `CallSMSBlocker-unsigned.ipa.sha256`
- `INSTALL.md`（会把这次的 bundle id 和名称写进去）
- `build-validation.json`
- `entitlements/`（三个包共用的 App Group）

安装步骤见 [INSTALL.md](INSTALL.md)。

本地可以先跑：

```bash
python3 -m unittest discover -s callsms-blocker/tests -v
```

改完源文件后，如果增删了 Swift 文件，运行 `python3 callsms-blocker/scripts/generate_xcodeproj.py`。

## 短信开关

这些开关默认都是关的。扩展只处理未知发件人的短信和彩信。

| 开关 | 打开后 |
| --- | --- |
| 启用短信过滤 | 总开关。关闭时返回「不分类」 |
| 拦截境外短信 | 非 86 国家码，以及含字母或汉字的发件人，标为垃圾。+86、86、11 位手机号、端口号和短号按国内处理 |
| 按省份 / 区号过滤 | 用本地 7 位号段表拦截选中的省，或选中的区号 |
| 只接收广东短信 | 非广东号码标为垃圾。白名单仍然优先 |
| 拦截虚拟号段 | 默认前缀 162 / 165 / 167 / 170 / 171。这些号段里也有正常用户 |
| 关键词与正则拦截 | 内置可编辑的中文诈骗和营销词库，命中后标为垃圾 |
| 白名单关键词 | 默认含验证码、取件码、快递、运单，优先于上面的拦截规则 |
| 发件人白名单 | 指定发件人直接放行 |
| 银行与快递归为交易信息 | 没被标成垃圾时归入交易。交易仍可能通知 |
| 营销信息归为推广 | 没被标成垃圾时归入推广。推广仍可能通知 |

「模拟」页用同一套规则演算发件人和正文。扩展不能把日志写回来，这是可靠的调试入口。系统里还要到「设置 > 信息 > 未知与过滤信息 > 过滤未知发件人」选中本应用，而且全机只能有一个短信过滤扩展。

## 来电开关

Call Directory 只能提交去重、升序的完整号码（E.164 数字，不带 +）。没有按国家、省份、区号或通配符拦截的接口，来电时也不会再回调。

| 开关 | 打开后 |
| --- | --- |
| 启用来电拦截 | 总开关。关闭时扩展清空已提交的拦截和标注 |
| 按 7 位号段展开拦截 | 每个号段展开成 10,000 个号码 |
| 展开已选虚拟号段 | 把选中的 162/165/167/170/171 号段按同样方式展开 |
| 只接通讯录来电 | 只是引导。跳到「设置 > 电话」，并说明要打开「静音未知来电」 |

另外可以手动添加要拦截或只标注的完整号码。

硬上限是 1,000,000 条（号段、单独号码和标注一起算）。大约最多 100 个 7 位号段。界面会显示当前选择会占用多少条；超过上限时扩展一条都不提交，避免只拦截排序后的前半段。

做不到，界面里也写明了：

- 一键拦截全部境外来电
- 拦截某一个省的全部手机号
- 拦截整个座机区号（010、0755）
- 「只接广东来电」白名单
- 识破伪造的来电显示

不使用 iOS 18 实时来电显示查询。那个接口需要苹果另行批准的托管权限和 PIR 服务器，自签无法使用。

「只接通讯录来电」要靠系统的「设置 > 电话 > 静音未知来电」：通讯录联系人、最近拨出的号码和 Siri 建议会响铃，其他陌生号码静音。应用不读取通讯录。

来电扩展要在「设置 > 电话 > 来电拦截与身份识别」里打开，然后由应用调用 `reloadExtension`。

## 号段数据

`Resources/prefix_ranges.dat` 来自 [ls0f/phone](https://github.com/ls0f/phone) 的 `phone.dat`（数据头 2312，README 声明 MIT），压成约 13 万段定长区间。短信扩展按区间二分查找，不加载 Core ML。2024 年以后新放的号段可能查不到。许可和出处见 [NOTICE.md](NOTICE.md)。

## 参考

规则引擎、词库和界面是为本仓库写的，没有整文件复制这些项目：

- [boommanpro/ios-sms-guard](https://github.com/boommanpro/ios-sms-guard)（MIT）：本地中文规则、预设和模拟器
- [afterxleep/Bouncer](https://github.com/afterxleep/Bouncer)（MIT）：`ILMessageFilter` 的成熟形态
- [ekrmsnr/smspam](https://github.com/ekrmsnr/smspam)（MIT）：同一个工程里的短信过滤和 Call Directory，增量更新时先清空再按升序提交
- [Rex-xingjl/CallKitDemo](https://github.com/Rex-xingjl/CallKitDemo)：Call Directory 只接受完整号码并保持升序

号段展开和 100 万条硬顶是按这个应用的限制实现的。没有使用 `apple/live-caller-id-lookup-example`。
