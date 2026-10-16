#!/usr/bin/env python3
# -*- coding: utf-8 -*-
r"""Flydigi CD2 dock + Vader 5 pad settings tool for Windows (dependency-free).

Why this exists
---------------
A Flydigi pad that is left idle - for example sitting on the CD2 charging dock -
disappears from the USB bus every 15 minutes and comes straight back.  Windows
records each one as a surprise removal:

    Device USB\VID_37D7&PID_2401\Flydigi_Vader_5_Pro has been surprise removed
    as it is reported as missing on the bus.

The cause is the pad's own sleep timer: the pad ships at 15 minutes and, per the
reverse-engineered protocol notes, "does not go quiet when it sleeps, it leaves
the USB bus".  Setting the timer to 0 ("never") stops the loop.

This tool reads and writes that timer, and also reads/changes the four switches
of the CD2 charging dock.  It uses the hidapi.dll that ships inside Flydigi
Space Station, so nothing has to be installed.

Verified on this machine (2026-10-15): Flydigi Vader 5 Pro over USB,
CD2 dock firmware 0.0.3.9, Space Station 4.2.2.3.

Protocol credit
---------------
Packet framing and command numbers come from the MIT-licensed project
openflydigi by Mikalai Kaliaha (https://github.com/mkaliaha/openflydigi),
verified there against real hardware.  This file is an independent,
Windows-only, dependency-free re-implementation of the small part needed here.

Framing
-------
Pad  (report id 0x03, 32-byte packets, no checksum):

    request : [0]=0x03 [1]=0x5A [2]=0xA5 [3]=cmd [4]=len [5..]=payload
    reply   : [0]=0x5A [1]=0xA5 [2]=cmd [3]=len [4..]=payload

Dock (report id 0x00, 64-byte packets, checksum at [3+len]):

    request : [0]=0x00 [1]=0x5A [2]=0xA5 [3]=cmd [4]=len(2+payload) [5..]=payload
    reply   : [0]=0x5A [1]=0xA5 [2]=cmd [3]=len [4..]=payload

Usage
-----
    python flydigi_dock.py hid-list
    python flydigi_dock.py pad-status
    python flydigi_dock.py pad-sleep 0          # 0 = never
    python flydigi_dock.py status               # CD2 dock switches
    python flydigi_dock.py off sleep            # dock: sleep while docked
    python flydigi_dock.py on  led-sync
"""

from __future__ import annotations

import argparse
import ctypes
import os
import sys
import time
from ctypes import POINTER, Structure, c_char_p, c_int, c_size_t, c_ushort, c_void_p, c_wchar_p

VID_FLYDIGI = 0x37D7
FAMILY_MASK = 0xF000
FAMILY_PAD = 0x2000             # pads / dongles
FAMILY_DOCK = 0x6000            # charging docks

MAGIC1, MAGIC2 = 0x5A, 0xA5

# The Vader 5 Pro's command collection is the vendor page 0xFFEE, and unlike
# the Apex 5 that openflydigi was written against it uses NUMBERED reports:
#
#     06 ee ff 09 00 a1 01  85 05  09 01  75 08 95 3f 81 02  ...  91 02  ...  b1 02
#     usage page 0xFFEE     report id 5      63-byte input, output, feature
#
# So one request is the classic 64-byte Flydigi packet: report id 5, then the
# 5A A5 envelope.  (The pad also exposes a 0xFFA0 collection with 32-byte
# unnumbered reports that accepts writes and never answers - not this one.)
PAD_PACKET_LEN = 64
PAD_REPORT_ID = 0x05
PAD_USAGE_PAGE = 0xFFEE
PAD_USAGE_PAGE = 0xFFA0         # the vendor command collection

DOCK_PACKET_LEN = 64
DOCK_REPORT_ID = 0x00

CMD_PAD_STATUS = 3
CMD_PAD_SLEEP = 23
CMD_PAD_RESTART = 29

SLEEP_MAX_MINUTES = 60

CMD_DOCK_HEARTBEAT = 1
REPORT_STATUS = 239              # unsolicited dock status, about 1 Hz
CMD_SLEEP_WHEN_CHARGING = 17
CMD_LED_SYNC = 18
CMD_CLOSE_WITH_SYSTEM = 19
CMD_SHOW_ANIMATION = 25

DOCK_TYPES = {
    0: "Controller Charging Dock 2 Pro",
    1: "Controller Charging Dock 2 Pro EVA .ver",
    2: "Honkai: Star Rail Castorice Charging Dock",
    3: "Genshin Impact Skirk Charging Dock",
    4: "Elysia Elite Charging Dock",
}

DOCK_FLAGS = {
    "sleep": (CMD_SLEEP_WHEN_CHARGING, "sleep_when_charging", "sleep while docked (Flydigi: Intelligent ...)"),
    "led-sync": (CMD_LED_SYNC, "led_sync", "lighting sync"),
    "close-with-system": (CMD_CLOSE_WITH_SYSTEM, "close_with_system", "close when the PC shuts down"),
    "animation": (CMD_SHOW_ANIMATION, "show_animation_when_charging", "show animation while charging"),
}

HIDAPI_CANDIDATES = [
    os.environ.get("FLYDIGI_HIDAPI", ""),
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "hidapi.dll"),
    "D:/Flydigi Space Station/hidapi.dll",
    "C:/Program Files/Flydigi Space Station/hidapi.dll",
    "C:/Program Files (x86)/Flydigi Space Station/hidapi.dll",
    "hidapi.dll",
]


# --------------------------------------------------------------------------
# hidapi bindings (ctypes, no pip packages)
# --------------------------------------------------------------------------
class HIDDeviceInfo(Structure):
    pass


HIDDeviceInfo._fields_ = [
    ("path", c_char_p),
    ("vendor_id", c_ushort),
    ("product_id", c_ushort),
    ("serial_number", c_wchar_p),
    ("release_number", c_ushort),
    ("manufacturer_string", c_wchar_p),
    ("product_string", c_wchar_p),
    ("usage_page", c_ushort),
    ("usage", c_ushort),
    ("interface_number", c_int),
    ("next", POINTER(HIDDeviceInfo)),
]

LIB = None


def load_hidapi():
    """Load hidapi from the first place that has it, and wire up the prototypes."""
    tried = []
    for cand in HIDAPI_CANDIDATES:
        if not cand:
            continue
        tried.append(cand)
        if cand != "hidapi.dll" and not os.path.exists(cand):
            continue
        try:
            found = ctypes.CDLL(cand)
            break
        except OSError:
            continue
    else:
        raise SystemExit(
            "hidapi.dll not found. Install Flydigi Space Station, or point "
            "FLYDIGI_HIDAPI at hidapi.dll." + chr(10) + "Tried:" + chr(10) + "  "
            + (chr(10) + "  ").join(tried)
        )
    found.hid_init.restype = c_int
    found.hid_enumerate.restype = POINTER(HIDDeviceInfo)
    found.hid_enumerate.argtypes = [c_ushort, c_ushort]
    found.hid_free_enumeration.argtypes = [POINTER(HIDDeviceInfo)]
    found.hid_open_path.restype = c_void_p
    found.hid_open_path.argtypes = [c_char_p]
    found.hid_close.argtypes = [c_void_p]
    found.hid_write.argtypes = [c_void_p, c_char_p, c_size_t]
    found.hid_write.restype = c_int
    found.hid_read_timeout.argtypes = [c_void_p, c_char_p, c_size_t, c_int]
    found.hid_read_timeout.restype = c_int
    found.hid_error.restype = c_wchar_p
    found.hid_error.argtypes = [c_void_p]
    found.hid_init()
    return found


def lib():
    global LIB
    if LIB is None:
        LIB = load_hidapi()
    return LIB


def enumerate_flydigi(family=None):
    """Every Flydigi HID interface on the bus, or only one product family."""
    result = []
    head = lib().hid_enumerate(0, 0)
    node = head
    try:
        while node:
            info = node.contents
            if info.vendor_id == VID_FLYDIGI and (family is None or (info.product_id & FAMILY_MASK) == family):
                result.append(
                    {
                        "path": info.path,
                        "pid": info.product_id,
                        "product": info.product_string or "",
                        "manufacturer": info.manufacturer_string or "",
                        "usage_page": info.usage_page,
                        "usage": info.usage,
                        "interface": info.interface_number,
                    }
                )
            node = info.next
    finally:
        if head:
            lib().hid_free_enumeration(head)
    return result


# --------------------------------------------------------------------------
# packet helpers
# --------------------------------------------------------------------------
def locate(data):
    """Index of the 5A A5 magic inside a read buffer, or -1.

    Windows hidapi may or may not prepend the report-id byte, so never assume a
    reply starts at offset 0.
    """
    for i in range(0, max(0, len(data) - 1)):
        if data[i] == MAGIC1 and data[i + 1] == MAGIC2:
            return i
    return -1


class Handle:
    """One open HID interface, with the write/read dance both devices share."""

    packet_len = 0
    report_id = 0

    def __init__(self, path):
        self.path = path
        self.handle = lib().hid_open_path(path)
        if not self.handle:
            raise SystemExit(
                "could not open %s. Close Flydigi Space Station (tray icon "
                "included) and retry." % path
            )

    def close(self):
        if self.handle:
            lib().hid_close(self.handle)
            self.handle = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def build(self, cmd_id, payload=b""):
        raise NotImplementedError

    def read(self, timeout_ms=300):
        buf = ctypes.create_string_buffer(256)
        n = lib().hid_read_timeout(self.handle, buf, len(buf), timeout_ms)
        if n <= 0:
            return None
        return bytes(buf.raw[:n])

    def command(self, cmd_id, payload=b"", wait=0.6):
        """Send one packet and collect every reply that arrives inside 'wait'."""
        lib().hid_write(self.handle, self.build(cmd_id, payload), self.packet_len)
        deadline = time.time() + wait
        seen = []
        while time.time() < deadline:
            data = self.read(int(max(1, (deadline - time.time()) * 1000)))
            if data is None:
                continue
            at = locate(data)
            if at >= 0:
                seen.append(data[at:])
        return seen

    def ask(self, cmd_id, payload=b"", wait=0.6):
        for data in self.command(cmd_id, payload, wait=wait):
            if len(data) > 3 and data[2] == cmd_id:
                return data
        raise SystemExit("no reply to command %d" % cmd_id)


class Pad(Handle):
    packet_len = PAD_PACKET_LEN
    report_id = PAD_REPORT_ID

    def build(self, cmd_id, payload=b""):
        buf = bytearray(PAD_PACKET_LEN)
        buf[0] = PAD_REPORT_ID
        buf[1] = MAGIC1
        buf[2] = MAGIC2
        buf[3] = cmd_id
        buf[4] = len(payload)
        buf[5 : 5 + len(payload)] = payload
        return bytes(buf)

    def settings(self):
        """Command 3: capabilities, sleep minutes, report rate, sticks."""
        data = self.ask(CMD_PAD_STATUS)
        return {
            "sleep_minutes": data[9],
            "report_rate": data[10],
            "precision": data[11],
            "sensitivity": data[12],
            "supported": data[5] | (data[7] << 8),
            "enabled": data[6] | (data[8] << 8),
        }

    def set_sleep_minutes(self, minutes):
        minutes = max(0, min(SLEEP_MAX_MINUTES, int(minutes)))
        self.command(CMD_PAD_SLEEP, bytes((minutes,)))


class Dock(Handle):
    packet_len = DOCK_PACKET_LEN
    report_id = DOCK_REPORT_ID

    def build(self, cmd_id, payload=b""):
        buf = bytearray(self.packet_len)
        buf[0] = self.report_id
        buf[1] = MAGIC1
        buf[2] = MAGIC2
        buf[3] = cmd_id
        buf[4] = 2 + len(payload)
        buf[5 : 5 + len(payload)] = payload
        buf[3 + buf[4]] = sum(buf[3 : 3 + buf[4]]) & 0xFF
        return bytes(buf)

    def info(self):
        data = self.ask(CMD_DOCK_HEARTBEAT)
        firmware = "%d.%d.%d.%d" % (data[16] >> 4, data[16] & 0xF, data[17] >> 4, data[17] & 0xF)
        if set(firmware) <= {"0", "."}:
            firmware = None
        return {
            "device_type": data[6],
            "device_name": DOCK_TYPES.get(data[6], "unknown type %d" % data[6]),
            "chip_type": data[15] & 0xF,
            "firmware": firmware,
            "sleep_when_charging": data[18] == 1,
            "led_sync": data[19] == 1,
            "close_with_system": data[20] == 1,
            "show_animation_when_charging": data[21] == 1,
        }

    def set_flag(self, cmd_id, enable, wait=0.6):
        self.command(cmd_id, bytes((1 if enable else 0,)), wait=wait)


# --------------------------------------------------------------------------
# picking a device
# --------------------------------------------------------------------------
def pick_pad(path=None):
    """The pad's vendor command interface: family 0x2xxx, usage page 0xFFEE."""
    candidates = [d for d in enumerate_flydigi(FAMILY_PAD) if d["usage_page"] == PAD_USAGE_PAGE]
    if not candidates:
        candidates = [d for d in enumerate_flydigi(FAMILY_PAD) if d["usage_page"] >= 0xFF00]
    if not candidates:
        raise SystemExit(
            "no Flydigi pad (VID 37D7, PID 2xxx, usage page 0x%04X) found. "
            "Is the pad connected?" % PAD_USAGE_PAGE
        )
    if path:
        for d in candidates:
            if path.lower() in d["path"].decode("utf-8", "replace").lower():
                return d
        raise SystemExit("no pad whose HID path contains %r" % path)
    return candidates[-1]


def pick_dock(path=None):
    docks = enumerate_flydigi(FAMILY_DOCK)
    if not docks:
        raise SystemExit("no Flydigi dock (VID 37D7, PID 6xxx) found on the HID bus.")
    if path:
        for d in docks:
            if path.lower() in d["path"].decode("utf-8", "replace").lower():
                return d
        raise SystemExit("no dock whose HID path contains %r" % path)
    return docks[0]


# --------------------------------------------------------------------------
# commands
# --------------------------------------------------------------------------
def cmd_hid_list(args):
    devices = enumerate_flydigi()
    if not devices:
        print("no Flydigi HID interfaces found")
        return 1
    for d in devices:
        fam = "pad " if (d["pid"] & FAMILY_MASK) == FAMILY_PAD else ("dock" if (d["pid"] & FAMILY_MASK) == FAMILY_DOCK else "?   ")
        print("%s pid=0x%04X usage_page=0x%04X usage=0x%04X iface=%s  %s"
              % (fam, d["pid"], d["usage_page"], d["usage"], d["interface"], d["product"]))
    return 0


def cmd_pad_status(args):
    d = pick_pad(args.device)
    with Pad(d["path"]) as pad:
        s = pad.settings()
    minutes = s["sleep_minutes"]
    print("pad sleep : %s" % ("never" if minutes == 0 else "%d minutes" % minutes))
    print("report rate: %s" % s["report_rate"])
    print("precision  : %s   sensitivity: %s" % (s["precision"], s["sensitivity"]))
    print("features   : supported=0x%04X enabled=0x%04X" % (s["supported"], s["enabled"]))
    if minutes == 0:
        print()
        print("Sleep is already disabled - the pad will not leave the USB bus when idle.")
    return 0


def cmd_pad_sleep(args):
    minutes = int(args.minutes)
    d = pick_pad(args.device)
    with Pad(d["path"]) as pad:
        before = pad.settings()["sleep_minutes"]
        if before == minutes:
            print("sleep time is already %d - nothing sent." % minutes)
            return 0
        print("before: sleep after %s" % ("never" if before == 0 else "%d minutes" % before))
        pad.set_sleep_minutes(minutes)
        time.sleep(0.4)
        after = pad.settings()["sleep_minutes"]
    print("after : sleep after %s" % ("never" if after == 0 else "%d minutes" % after))
    if after != max(0, min(SLEEP_MAX_MINUTES, minutes)):
        print("WARNING: the pad did not take the new value (command 23).")
        return 2
    print("OK")
    return 0


def cmd_dock_status(args):
    d = pick_dock(args.device)
    with Dock(d["path"]) as dock:
        info = dock.info()
    print("dock      : %s (type %d, chip %s)" % (info["device_name"], info["device_type"], info["chip_type"]))
    print("firmware  : %s" % (info["firmware"] or "not reported"))
    print()
    for key in sorted(DOCK_FLAGS):
        _cmd, field, label = DOCK_FLAGS[key]
        print("  %-32s %-4s %s" % (field, "ON" if info[field] else "off", label))
    return 0


def cmd_dock_watch(args):
    """Watch the dock's unsolicited status: is a pad seated, and its battery.

    The dock reports "docked" once a second.  If that flag flickers, the pad is
    not making reliable contact with the dock's pins - which is what makes the
    pad's USB connection drop and come back over and over.
    """
    d = pick_dock(args.device)
    end = time.time() + args.seconds
    last = None
    changes = 0
    with Dock(d["path"]) as dock:
        while time.time() < end:
            data = dock.read(500)
            if not data:
                continue
            at = locate(data)
            if at < 0:
                continue
            pkt = data[at:]
            if pkt[2] != REPORT_STATUS or len(pkt) < 9:
                continue
            state = (bool(pkt[7]), pkt[8])
            if state != last:
                changes += 1
                note = "" if last is None else "   <- changed"
                print("%s  docked=%-5s battery=%d%s"
                      % (time.strftime("%H:%M:%S"), state[0], state[1], note))
                last = state
    print()
    print("dock state changes in %ds: %d" % (args.seconds, changes))
    if changes > 2:
        print("The docked flag is flickering: reseat the pad, clean the pins.")
    return 0


def cmd_dock_set(args, enable):
    cmd_id, field, label = DOCK_FLAGS[args.flag]
    d = pick_dock(args.device)
    with Dock(d["path"]) as dock:
        before = dock.info()
        if before["device_type"] not in DOCK_TYPES:
            raise SystemExit(
                "refusing to write: this device reports charger type %d, not a CD2."
                % before["device_type"]
            )
        if before[field] == enable:
            print("%s is already %s - nothing sent." % (field, "ON" if enable else "off"))
            return 0
        print("before: %s = %s" % (field, "ON" if before[field] else "off"))
        dock.set_flag(cmd_id, enable)
        time.sleep(0.4)
        after = dock.info()
    print("after : %s = %s" % (field, "ON" if after[field] else "off"))
    if after[field] != enable:
        print("WARNING: the switch did not change; the firmware may ignore command %d." % cmd_id)
        return 2
    print("OK")
    return 0


def cmd_pad_restart(args):
    d = pick_pad(args.device)
    with Pad(d["path"]) as pad:
        pad.command(CMD_PAD_RESTART)
    print("restart command sent")
    return 0


def main(argv=None):
    p = argparse.ArgumentParser(description="Flydigi pad/dock settings tool (Windows, no dependencies)")
    p.add_argument("--device", help="substring of the HID path, when several devices are attached")
    sub = p.add_subparsers(dest="action", required=True)

    sub.add_parser("hid-list", help="every Flydigi HID interface").set_defaults(func=cmd_hid_list)

    sub.add_parser("pad-status", help="pad sleep timer and settings").set_defaults(func=cmd_pad_status)
    sp = sub.add_parser("pad-sleep", help="set the pad's idle-sleep timer in minutes (0 = never)")
    sp.add_argument("minutes", type=int)
    sp.set_defaults(func=cmd_pad_sleep)
    sub.add_parser("pad-restart", help="restart the pad (command 29)").set_defaults(func=cmd_pad_restart)

    sub.add_parser("status", help="CD2 dock firmware and switches").set_defaults(func=cmd_dock_status)
    sp = sub.add_parser("dock-watch", help="watch the dock's docked/battery status")
    sp.add_argument("--seconds", type=float, default=45.0)
    sp.set_defaults(func=cmd_dock_watch)
    for name, enable in (("off", False), ("on", True)):
        sp = sub.add_parser(name, help="turn a dock switch %s" % name)
        sp.add_argument("flag", choices=sorted(DOCK_FLAGS))
        sp.set_defaults(func=lambda a, e=enable: cmd_dock_set(a, e))

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
