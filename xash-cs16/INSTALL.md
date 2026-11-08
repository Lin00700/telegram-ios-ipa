# 用全能签安装，并放入自己的 Steam 游戏文件

IPA 里只有引擎和开源的 CS 1.6 客户端库，没有地图、模型、音效。需要你自己拥有 Steam 上的 Half-Life / Counter-Strike 1.6，再把资源拷进手机。

## 1. 下载

从本仓库 Actions 里下载成功的构建产物，解压后得到：

- `xash3d-fwgs-cs16-ios-arm64.ipa`
- `xash3d-fwgs-cs16-ios-arm64-dylibs.zip`（可选，库已经打进 IPA，一般不用再拷）

## 2. 全能签

1. 把 IPA 导入全能签。
2. 用你自己的证书签名。签名时把描述文件里的 Team ID 换成证书上的 Team ID。
3. 包名可以保持 `su.xash.engine`。如果提示冲突，改成你自己的反向域名。
4. 不要勾选 App Groups，也不要勾选 Push，除非证书里确实有对应能力。
5. 签名完成后安装到手机。系统若提示不受信任的开发者，到「设置 → 通用 → VPN 与设备管理」里信任该证书。

库在 `.app` 里面，和主程序一起被重签。不要把 dylib 单独放到「文件」App 的 Documents 里再指望游戏加载，那样经常过不了系统的库校验。

## 3. 拷贝 Steam 的 valve 和 cstrike

在电脑上从 Steam 安装目录取出这两个文件夹（常见路径）：

- `steamapps/common/Half-Life/valve`
- `steamapps/common/Half-Life/cstrike`

有的安装把 CS 放在 `Counter-Strike 1.6` 目录，同样只需要其中的 `cstrike`，以及 Half-Life 的 `valve`。

手机上打开「文件」App。这个 IPA 打开了文件共享，装好后能看到 **xash3d-fwgs**（或你改过的显示名）。把 `valve` 和 `cstrike` 拷进这个应用的目录，使结构类似：

```text
xash3d-fwgs/
  valve/      （地图、模型、音效、sprites 等）
  cstrike/    （CS 的 maps、models、sound、sprites 等）
```

Windows 版自带的 `dlls/*.dll`、`cl_dlls/*.dll` 可以留在拷贝里，引擎不会拿它们当 iOS 库。真正加载的是包内这些文件：

```text
cstrike/cl_dlls/client_ios_arm64.dylib
cstrike/cl_dlls/menu_ios_arm64.dylib
cstrike/dlls/yapb_ios_arm64.dylib
cstrike/dlls/cs_ios_arm64.dylib
cstrike/dlls/cs_arm64.dylib
cstrike/extras.pk3
```

`cs_arm64.dylib` 和 `cs_ios_arm64.dylib` 是同一份服务器库的两个文件名。YaPB 按前一个名字找，引擎按后一个名字找。

## 4. 启动

第一次打开游戏，启动参数框里应是：

```text
-game cstrike -dll @yapb
```

点 Start。`-dll @yapb` 会先加载机器人库，再由它加载 `cs_arm64.dylib`。

只玩半衰期时，把参数改成 `-game valve` 后再启动。参数会记在应用文档目录的 `settings.bin` 里，下次还会用这份。

语音聊天会向系统申请麦克风权限。

## 5. 画面铺满手机

上一版 IPA 的 Info.plist 写了启动画面名字，包里却没有对应文件，构建时把这个键删掉了。没有启动画面时，iOS 会把应用按老款 iPhone 的 3:2 画面（逻辑分辨率 480×320）缩放后摆在屏幕中间，左右是黑边。主菜单那张图本身会铺满引擎窗口，黑边在窗口外面。

这一版放进了真正的启动画面（`Launch.storyboardc`，另外写了 iOS 14 及以后使用的 `UILaunchScreen`）。引擎在 iPhone 上改用当前屏幕的尺寸，不再沿用上次记下的 3:2 宽高。画面铺到屏幕边缘，包括刘海那一侧。触控按钮仍默认避开刘海和底部横条（`touch_safearea 1`）。想让按钮也画进刘海区域时，在控制台输入 `touch_safearea 0`。

请安装这一版 IPA，不要继续用上一版。包名还是 `su.xash.engine`，覆盖安装即可，已经拷进「文件」的 `valve` 和 `cstrike` 还在。

## 6. 中文菜单

会变成中文的，是主菜单和它打开的那些设置页（按钮文字和右侧说明）。这些句子是这份打包自己写的，放在 IPA 里的 `resource/mainui_schinese.txt` 和 `resource/mainui_tchinese.txt`，不是 Valve 的中文包。

不会变成中文的：

- 游戏里的 HUD、聊天、无线电、买枪菜单、击杀提示、控制台。它们用的是引擎点阵字，没有中日韩字形。Xash 官方也说明，完整的中日韩界面要等矢量字做完，这里没有做那一层。
- 地图说明、武器名、任务文本。那些在你自己的 `cstrike` / `valve` 资源里。这个 IPA 不附带、也不下载那些文件。
- 主菜单上原来那套橙色英文图片按钮。只有放了下面的字体之后，才会改成用文字画出来。

### 字体

菜单用 stb 读一款 TrueType。把你自己有权使用的 `.ttf` 放到应用目录里，路径必须是：

```text
cstrike/gfx/fonts/chinese.ttf
```

`valve/gfx/fonts/chinese.ttf` 也可以。字体要带你想显示的汉字；如果还想同时看英文，它也要有拉丁字母。思源黑体、Noto Sans SC 这类 TrueType 可以。`.ttc` 字体集和只有 CFF 轮廓的 `.otf` 经常读不出来，请先转成单个 `.ttf`。字库很大也没关系，第一次打开菜单时会慢一下。

没有这个文件时，主菜单继续显示英文图片按钮。语言已经切到中文的话，右侧说明可能是空白，因为点阵字画不出汉字。

### 语言参数

手机系统语言是简体中文时，启动参数框会在原来的参数后面加上 `-language schinese`。繁体（含台湾、香港、澳门）则是 `-language tchinese`。原来的 `-game cstrike -dll @yapb` 仍然要留着。第一次看到多出来的 `-language` 时直接点 Start，它会写进 `settings.bin`。

不想用中文时，把那一项改成 `-language english` 再启动。只删掉 `-language` 的话，中文系统下次还会再补上。

`-language` 还会挂上本地化目录。如果你自己有这些文件夹，把它们和 `cstrike`、`valve` 放在同一层：

```text
xash3d-fwgs/
  valve/
  valve_schinese/
  cstrike/
  cstrike_schinese/
  cstrike/gfx/fonts/chinese.ttf
```

自己的菜单译文可以放在 `cstrike/resource/cstrike_schinese.txt`（繁体把 `schinese` 换成 `tchinese`）。它的格式和引擎的 lang 文件一样，同一条词条会盖过 IPA 里自带的译文。`cstrike/resource/gameui_schinese.txt`、`valve/resource/valve_schinese.txt` 也会被读到。这些文件只能用你已经拥有的，不要把来路不明的中文整合包放进这个仓库。

## 7. 打不开时

- 先确认 `cstrike/maps` 里能看到你从 Steam 拷来的 `.bsp`。IPA 本身不含地图。
- 启动参数不要漏掉 `-game cstrike`。
- 机器人没出来时，确认参数里有 `-dll @yapb`，并且没有把包内的 dylib 换成从网上下的别的库。
- 全能签重签后如果闪退，换一个不含额外能力的描述文件再签一次。
- 装了这一版仍有左右黑边时，确认装上的是新的 IPA（对照产物里的 sha256），不要还开着上一版。
- 菜单仍是英文图片时，确认 `cstrike/gfx/fonts/chinese.ttf` 在，并且启动参数里有 `-language schinese` 或 `-language tchinese`。
