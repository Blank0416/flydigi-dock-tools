# flydigi-dock-tools

**English** | [中文](#中文)

Read and change the idle-sleep timer of a Flydigi pad and the switches of a
Flydigi CD2 charging dock, from Windows, with **no dependencies**.

---

## English

### The problem this fixes

A Flydigi Vader 5 Pro (八爪鱼 5) that is left idle - typically sitting on the CD2
charging dock - disappears from the USB bus and comes straight back, over and
over. Windows records every one of those as a surprise removal:

~~~text
Device USB\\VID_37D7&PID_2401\\Flydigi_Vader_5_Pro has been surprise removed as it
is reported as missing on the bus.
~~~

Observed on real hardware: **every 15 minutes 09 seconds**, all night long, with
nobody touching the pad. Device Manager shows the pad fine in between, and a
second device with a yellow "no driver" triangle (`...&MI_00`, USB class FF) is
unrelated - that vendor interface has no driver by design.

### The cause

The pad's own **idle-sleep timer**, which ships at **15 minutes**. When it fires,
the pad does not merely go quiet: it **leaves the USB bus**. Docking/charging
current then brings it back a few seconds later, so the cycle repeats forever.

### The fix

~~~text
python flydigi_dock.py pad-sleep 0        # 0 = never sleep
~~~

That is one command byte (23) to the pad. The tool reads the value back to
confirm. To restore the factory behaviour: `pad-sleep 15`.

You can also do it in Flydigi Space Station (whatever its own sleep picker is
called); this tool exists because that picker is easy to miss and does not tell
you what the setting actually does to the USB bus.

### What else it can do

| Command | What it does |
|---|---|
| `hid-list` | list every Flydigi HID interface (vendor 0x37D7) Windows exposes |
| `pad-status` | pad sleep timer, report rate, stick precision/sensitivity, feature bits |
| `pad-sleep N` | set the pad's idle-sleep timer in minutes (0 = never, max 60) |
| `pad-restart` | restart the pad (command 29) |
| `status` | CD2 dock type, firmware, and its four switches |
| `off sleep` / `on sleep` | dock: sleep while docked (Flydigi calls it "Intelligent ...") |
| `off led-sync` / `on led-sync` | dock: lighting sync |
| `off close-with-system` / `on close-with-system` | dock: close when the PC shuts down |
| `off animation` / `on animation` | dock: animation while charging |

### Requirements

- Windows 10/11, Python 3.9+
- Flydigi Space Station installed (this tool loads the `hidapi.dll` that ships
  with it). Point `FLYDIGI_HIDAPI` at another copy if yours lives elsewhere.
- No `pip install` at all.

If a device is held exclusively by another program, close Flydigi Space Station
(tray icon included) and retry.

### Verified on

| Item | Value |
|---|---|
| Pad | Flydigi Vader 5 Pro, USB\VID_37D7&PID_2401 |
| Dock | Controller Charging Dock 2 Pro, USB\VID_37D7&PID_6001, firmware 0.0.3.9 |
| Space Station | 4.2.2.3 |
| OS | Windows 11 |

### Protocol

Framing and command numbers are taken from the MIT-licensed
[openflydigi](https://github.com/mkaliaha/openflydigi) project by Mikalai
Kaliaha, which reverse-engineered the vendor protocol and validated it against
real hardware. See the module docstring for the packet layouts.

### Disclaimer

Unofficial. Not affiliated with, endorsed by, or supported by Flydigi. It writes
device settings over an undocumented protocol - read the code before running it,
and keep in mind that a failed write is recoverable by re-writing the setting or
restarting the pad (command 29 / power cycle).

MIT licensed.

---

## 中文

### 解决什么问题

飞智八爪鱼 5（Vader 5 Pro）放在 CD2 充电底座上待机时，会**每隔约 15 分钟**从
USB 总线上消失一次又立刻回来，Windows 每次都记一条"设备已意外移除"：

~~~text
Device USB\\VID_37D7&PID_2401\\Flydigi_Vader_5_Pro has been surprise removed as it
is reported as missing on the bus.
~~~

实测：整夜无人操作也是 **15 分 09 秒**一次；中途设备管理器里手柄一切正常。
设备管理器里那个带黄色感叹号的"没有驱动程序"（`...&MI_00`，USB Class FF）是
另一个厂商接口，本来就没有驱动，与此无关。

### 原因

**手柄自己的空闲休眠定时器**，出厂默认 **15 分钟**。到点后手柄不是"静默"，
而是**直接离开 USB 总线**；底座/充电电流几秒后又把它唤醒枚举，于是无限循环。

### 修复

~~~text
python flydigi_dock.py pad-sleep 0        # 0 = 永不休眠
~~~

就是给手柄发一条命令（命令号 23），工具会回读确认。想恢复出厂行为：
`pad-sleep 15`。

也可以直接在飞智空间站里改（它自己的"休眠时间/自动关机"选项），这个工具存在
是因为那个开关很容易被忽略，而且它不会告诉你这个设置会断开 USB。

### 还能做什么

| 命令 | 作用 |
|---|---|
| `hid-list` | 列出 Windows 上所有飞智 HID 接口（VID 0x37D7） |
| `pad-status` | 手柄休眠时间、回报率、摇杆精度/灵敏度、功能位 |
| `pad-sleep N` | 设置手柄空闲休眠分钟数（0 = 永不，上限 60） |
| `pad-restart` | 重启手柄（命令 29） |
| `status` | CD2 底座型号、固件版本与四个开关 |
| `off sleep` / `on sleep` | 底座：停靠时休眠（飞智叫 "Intelligent ..."） |
| `off led-sync` / `on led-sync` | 底座：灯效同步 |
| `off close-with-system` / `on close-with-system` | 底座：随电脑关机一起关 |
| `off animation` / `on animation` | 底座：充电时播放动画 |

### 依赖

- Windows 10/11 + Python 3.9+
- 已安装飞智空间站（本工具直接调用它自带的 `hidapi.dll`，可用 `FLYDIGI_HIDAPI`
  指向别处的副本）
- **完全不需要 pip 安装任何东西**

设备被别的程序独占时打不开：先退出飞智空间站（含托盘图标）再试。

### 实测环境

| 项 | 值 |
|---|---|
| 手柄 | 飞智八爪鱼 5 / Vader 5 Pro，USB\VID_37D7&PID_2401 |
| 底座 | Controller Charging Dock 2 Pro，USB\VID_37D7&PID_6001，固件 0.0.3.9 |
| 空间站 | 4.2.2.3 |
| 系统 | Windows 11 |

### 协议来源

报文格式与命令号来自 MIT 协议的
[openflydigi](https://github.com/mkaliaha/openflydigi)（作者 Mikalai Kaliaha），
该项目逆向并实机验证了这套厂商协议。报文结构见本文件顶部模块注释。

### 免责声明

非官方项目，与飞智公司无关，未获其授权或支持。工具会通过未公开协议写入设备
设置——运行前请先读代码；写坏了可以重新写入原值或重启手柄（命令 29 / 断电）。

MIT 协议开源。

---

## License

MIT - see [LICENSE](LICENSE).
