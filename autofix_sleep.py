#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Wait for the pad to appear, then set its idle-sleep timer to "never".

Handy when the pad is asleep (and therefore not on the USB bus) and you do not
want to sit there waiting to run flydigi_dock.py pad-sleep 0 by hand.

    python autofix_sleep.py [--minutes 0] [--timeout-min 45] [--log autofix.log]
"""
from __future__ import annotations

import argparse
import datetime
import sys
import time

import flydigi_dock as fd


def log(path, message):
    line = "%s  %s" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), message)
    print(line, flush=True)
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line + chr(10))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--minutes", type=int, default=0, help="0 = never sleep (default)")
    p.add_argument("--timeout-min", type=float, default=45.0)
    p.add_argument("--interval", type=float, default=3.0)
    p.add_argument("--log", default="autofix.log")
    args = p.parse_args()

    deadline = time.time() + args.timeout_min * 60
    log(args.log, "watching for a Flydigi pad (VID 37D7, PID 2xxx, usage page 0xFFA0) ...")
    while time.time() < deadline:
        try:
            d = fd.pick_pad()
        except SystemExit:
            time.sleep(args.interval)
            continue

        log(args.log, "pad appeared: %s" % d["path"].decode("utf-8", "replace"))
        try:
            with fd.Pad(d["path"]) as pad:
                before = pad.settings()["sleep_minutes"]
                log(args.log, "sleep timer before: %s" % ("never" if before == 0 else "%d min" % before))
                if before == args.minutes:
                    log(args.log, "already correct - nothing to do")
                    return 0
                pad.set_sleep_minutes(args.minutes)
                time.sleep(0.5)
                after = pad.settings()["sleep_minutes"]
        except SystemExit as exc:
            log(args.log, "could not use the pad: %s" % exc)
            time.sleep(args.interval)
            continue

        log(args.log, "sleep timer after : %s" % ("never" if after == 0 else "%d min" % after))
        if after == args.minutes:
            log(args.log, "FIXED")
            return 0
        log(args.log, "the pad did not take the new value")
        return 2

    log(args.log, "timed out waiting for the pad")
    return 1


if __name__ == "__main__":
    sys.exit(main())
