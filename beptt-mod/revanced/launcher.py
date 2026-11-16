#!/usr/bin/env python3
"""Interactive local launcher; accepts a path dragged into Terminal."""
from pathlib import Path
import datetime
import shlex
import subprocess
import sys

root = Path(__file__).resolve().parent
try:
    print("BePTT ReVanced 圖片網址黑名單 patcher\n")
    print("請拖入新版官方 APK／XAPK，再按 Enter。沿用私人簽章與既有設定，不會自動安裝。")
    raw = input("檔案路徑：").strip()
    paths = shlex.split(raw)
    if len(paths) != 1: raise ValueError("請一次選一個 APK 或 XAPK")
    source = Path(paths[0]).expanduser().resolve()
    if not source.is_file(): raise ValueError("找不到這個檔案")
    suffix = source.suffix.lower()
    if suffix not in (".apk", ".xapk"): raise ValueError("請選擇 .apk 或 .xapk")
    out = root / "已套用" / ("BePTT-patched-" + datetime.datetime.now().strftime("%Y%m%d-%H%M%S") + suffix)
    subprocess.run([sys.executable, str(root / "patch_beptt.py"), str(source), "--out", str(out)], check=True)
    print("\n請以覆蓋更新方式安裝輸出檔，不要先解除安裝原有改版。")
except (ValueError, subprocess.CalledProcessError) as error:
    print("\n未完成：", error)
finally:
    input("\n按 Enter 關閉視窗。")
