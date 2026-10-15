# flydigi-dock-tools

**English** | [中文](#中文)

Tools for a Flydigi Vader 5 Pro (八爪鱼 5) and its CD2 charging dock on Windows:
read/change the pad's idle-sleep timer and the dock's switches.

* **Dock half: verified** on real hardware (CD2, firmware 0.0.3.9).
* **Pad half: experimental.** The framing here comes from the Apex 5; the Vader
  5 Pro's command collection (usage page 0xFFEE, report id 5, 64-byte reports)
  accepts writes but does not answer a third-party reader. For this pad, set the
  sleep timer in Flydigi's own software - that is what actually fixed the machine
  this repo came from.

---

## English

### The problem this fixes

A Flydigi pad left idle - typically sitting on the CD2 charging dock - leaves
the USB bus and comes straight back, over and over. Windows records every one of
those as a surprise removal:

~~~text
Device USB\\VID_37D7&PID_2401\\Flydigi_Vader_5_Pro has been surprise removed as it
is reported as missing on the bus.
~~~

Measured here: **every 15 minutes 09 seconds**, all night, with nobody touching
the pad - and 13 such events on one evening.

### The cause

The pad's own **idle-sleep timer**, factory default **15 minutes**. When it fires
the pad does not merely go quiet, it **leaves the USB bus**; the dock's charging
current then wakes it again a few seconds later, so the loop repeats forever.
This is why playing never triggers it: input keeps resetting the timer.

### The fix

Set the pad's sleep timer to **never**:

* In Flydigi's own software (Space Station - for the Vader 5 Pro that is the web
  Space Station 5.0): whatever its sleep picker is called, choose never/off.
* With this tool, if your pad answers: `python flydigi_dock.py pad-sleep 0`

> **Verified on this machine (2026-10-15):** the pad came up at 18:05:00; at
> 18:22:32 - 17 minutes 32 seconds later, well past the 15:09 cycle - there were
> **zero** surprise removals and all 13 of the pad's interfaces were still
> present. Before the change the same measurement produced a removal every 15:09.

### What else it can do

| Command | Status | What it does |
|---|---|---|
| `hid-list` | works | list every Flydigi HID interface (vendor 0x37D7) |
| `status` | **verified** | CD2 dock type, firmware, and its four switches |
| `off sleep` / `on sleep` | **verified** | dock: sleep while docked (Flydigi calls it "Intelligent ...") |
| `off led-sync` / `on led-sync` | **verified** | dock: lighting sync |
| `off close-with-system` / `on close-with-system` | **verified** | dock: close when the PC shuts down |
| `off animation` / `on animation` | **verified** | dock: animation while charging |
| `pad-status` | experimental | pad sleep timer, report rate, stick precision/sensitivity |
| `pad-sleep N` | experimental | set the pad's idle-sleep timer in minutes (0 = never, max 60) |
| `pad-restart` | experimental | restart the pad (command 29) |

`watch_drops.ps1` is the measurement tool: it logs every Kernel-PnP surprise
removal of a Flydigi device with the gap since the previous one, so a fix can be
proved instead of assumed.

~~~powershell
powershell -ExecutionPolicy Bypass -File watch_drops.ps1 -Minutes 30
~~~

### Pad support status

The Vader 5 Pro exposes seven HID collections. The interesting ones:

| Interface | Usage page | Reports | Behaviour |
|---|---|---|---|
| iface 2 | 0xFFA0 | 32-byte, unnumbered | accepts writes, never answers |
| iface 3 | 0xFFEE | **report id 5, 63-byte** in/out/feature | accepts writes, **echoes the packet back** instead of an ACK |

The echo means the transport is right but the Vader 5 Pro's command dialect is
not the Apex 5's, which is what
[openflydigi](https://github.com/mkaliaha/openflydigi) documents (that project
states plainly that no Vader 5 was ever tested). Reading the sleep timer back
would need a capture of what the web Space Station 5.0 sends. Until then the pad
commands here are implemented-but-unverified, and the honest way to change the
setting on this model is Flydigi's own software.

### Requirements

* Windows 10/11, Python 3.9+
* Flydigi software installed (this tool loads the `hidapi.dll` that ships with
  it). Point `FLYDIGI_HIDAPI` at another copy if yours lives elsewhere.
* No `pip install` at all.
* Admin rights and the Flydigi app + `Flydigi Space Station Service` stopped may
  be needed: while they run they poll the pad and take the replies.

### Verified on

| Item | Value |
|---|---|
| Pad | Flydigi Vader 5 Pro, USB\\VID_37D7&PID_2401 |
| Dock | Controller Charging Dock 2 Pro, USB\\VID_37D7&PID_6001, firmware 0.0.3.9 |
| Flydigi software | desktop Space Station 4.2.2.3 (the pad itself is only serviced by the web Space Station 5.0) |
| OS | Windows 11 |

### Protocol

Dock framing and command numbers are taken from the MIT-licensed
[openflydigi](https://github.com/mkaliaha/openflydigi) by Mikalai Kaliaha, which
reverse-engineered the vendor protocol and validated it against real hardware.

* Dock: report id 0, 64-byte packets, `5A A5 <cmd> <len=2+payload> <payload>
  <checksum>`, reply `5A A5 <cmd> <len> <payload>`.
* Pad (this implementation): report id 5, 64-byte packets, `5A A5 <cmd> <len>
  <payload>` - unverified, see above.

### Disclaimer

Unofficial. Not affiliated with, endorsed by, or supported by Flydigi. It writes
device settings over an undocumented protocol - read the code before running it.

MIT licensed.

---

## 中文

### 解决什么问题

飞智八爪鱼 5（Vader 5 Pro）放在 CD2 充电底座上待机时，会反复从 USB 总线上
消失再回来。Windows 每次都记一条"设备已意外移除"：

~~~text
Device USB\\VID_37D7&PID_2401\\Flydigi_Vader_5_Pro has been surprise removed as it
is reported as missing on the bus.
~~~

本机实测：**每 15 分 09 秒一次**，整夜无人操作也一样；有一晚记了 13 次。

### 原因

手柄自己的**空闲休眠定时器**，出厂默认 **15 分钟**。到点后手柄不是"静默"，
而是**直接离开 USB 总线**；底座充电电流几秒后把它唤醒，于是无限循环。
所以玩的时候不会触发——有输入就会重置计时。

### 修复

把手柄休眠时间改成**永不**：

* 用飞智官方软件（空间站；八爪鱼 5 只认**网页版空间站 5.0**）里的休眠/自动关机
  选项，选"永不"；
* 或用本工具（如果你的手柄回应命令）：`python flydigi_dock.py pad-sleep 0`

> **本机验证（2026-10-15）**：手柄 18:05:00 上线，到 18:22:32（**17 分 32 秒**，
> 早已越过 15:09 的周期）**零次掉线**，13 个接口全部在线。改之前同样的测法是
> 每 15 分 09 秒掉一次。

### 还能做什么

| 命令 | 状态 | 作用 |
|---|---|---|
| `hid-list` | 可用 | 列出所有飞智 HID 接口（VID 0x37D7） |
| `status` | **已实机验证** | CD2 底座型号、固件、四个开关 |
| `off sleep` / `on sleep` | **已实机验证** | 底座：停靠时休眠（飞智叫 "Intelligent ..."） |
| `off led-sync` / `on led-sync` | **已实机验证** | 底座：灯效同步 |
| `off close-with-system` / `on close-with-system` | **已实机验证** | 底座：随电脑关机一起关 |
| `off animation` / `on animation` | **已实机验证** | 底座：充电时播放动画 |
| `pad-status` | 实验中 | 手柄休眠时间、回报率、摇杆精度/灵敏度 |
| `pad-sleep N` | 实验中 | 设置手柄空闲休眠分钟数（0 = 永不，上限 60） |
| `pad-restart` | 实验中 | 重启手柄（命令 29） |

`watch_drops.ps1` 是验证工具：记录每次 Kernel-PnP"意外移除"事件及其间隔，
让"修好了"变成可测量的事实，而不是感觉。

~~~powershell
powershell -ExecutionPolicy Bypass -File watch_drops.ps1 -Minutes 30
~~~

### 手柄支持现状（诚实说明）

八爪鱼 5 暴露 7 个 HID 集合，其中两个像命令口：

| 接口 | Usage page | 报文 | 表现 |
|---|---|---|---|
| iface 2 | 0xFFA0 | 32 字节、无报告 ID | 能写进去，但从不回应 |
| iface 3 | 0xFFEE | **报告 ID 5、63 字节** 输入/输出/feature | 能写进去，但**把发出去的包原样回显**，不是应答 |

回显说明"通道找对了，方言不对"：八爪鱼 5 的命令集不是
[openflydigi](https://github.com/mkaliaha/openflydigi) 逆向的 Apex 5 那一套
（该项目自己也写明**从未在 Vader 5 上测试过**）。要回读休眠时间，需要抓一份
网页版空间站 5.0 的通信。在此之前，手柄相关命令属于"实现了但未验证"，这台
机器上真正生效的是官方软件里的设置。

### 依赖

* Windows 10/11 + Python 3.9+
* 已安装飞智软件（本工具直接调用其自带的 `hidapi.dll`，可用 `FLYDIGI_HIDAPI`
  指向别处）
* **不需要 pip 安装任何东西**
* 可能需要管理员权限，并先关掉飞智 App 与 `Flydigi Space Station Service`：
  它们在跑的时候会占着手柄、把回复抢走

### 实测环境

| 项 | 值 |
|---|---|
| 手柄 | 飞智八爪鱼 5 / Vader 5 Pro，USB\\VID_37D7&PID_2401 |
| 底座 | Controller Charging Dock 2 Pro，USB\\VID_37D7&PID_6001，固件 0.0.3.9 |
| 飞智软件 | 桌面版空间站 4.2.2.3（手柄本身只由网页版空间站 5.0 服务） |
| 系统 | Windows 11 |

### 协议来源

底座的报文格式与命令号来自 MIT 协议的
[openflydigi](https://github.com/mkaliaha/openflydigi)（作者 Mikalai Kaliaha）。

* 底座：报告 ID 0，64 字节包，`5A A5 <cmd> <len=2+payload> <payload> <checksum>`，
  回复 `5A A5 <cmd> <len> <payload>`。
* 手柄（本实现）：报告 ID 5，64 字节包，`5A A5 <cmd> <len> <payload>` —— 未验证。

### 免责声明

非官方项目，与飞智公司无关。工具会通过未公开协议写入设备设置，运行前请先读代码。

MIT 协议开源。

---

## License

MIT - see [LICENSE](LICENSE).
