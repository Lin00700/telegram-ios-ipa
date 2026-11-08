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

## 5. 打不开时

- 先确认 `cstrike/maps` 里能看到你从 Steam 拷来的 `.bsp`。IPA 本身不含地图。
- 启动参数不要漏掉 `-game cstrike`。
- 机器人没出来时，确认参数里有 `-dll @yapb`，并且没有把包内的 dylib 换成从网上下的别的库。
- 全能签重签后如果闪退，换一个不含额外能力的描述文件再签一次。
