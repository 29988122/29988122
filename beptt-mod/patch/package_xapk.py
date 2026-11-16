#!/usr/bin/env python3
"""Align every APK to 16 KiB, sign all splits with one personal key, verify.

Creates a local XAPK only. Never uploads keys or APKs and never installs.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import zipfile


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("xapk", type=Path)
    p.add_argument("base", type=Path)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--build-tools", type=Path, required=True)
    p.add_argument("--java-home", type=Path, required=True)
    p.add_argument("--keystore", type=Path, required=True)
    p.add_argument("--alias", required=True)
    p.add_argument("--password-file", type=Path, required=True)
    args = p.parse_args()
    args.work.mkdir(parents=True, exist_ok=False)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, JAVA_HOME=str(args.java_home.resolve()))
    certificates = set()
    entries = {}
    with zipfile.ZipFile(args.xapk) as original:
        manifest = json.loads(original.read("manifest.json"))
        for split in manifest["split_apks"]:
            name = split["file"]
            if Path(name).name != name or not name.endswith(".apk"):
                raise ValueError("Unexpected split filename")
            raw = args.work / ("raw-" + name)
            raw.write_bytes(args.base.read_bytes() if split["id"] == "base" else original.read(name))
            aligned = args.work / ("aligned-" + name)
            signed = args.work / name
            subprocess.run([str(args.build_tools / "zipalign"), "-f", "-P", "16", "4", str(raw), str(aligned)], check=True)
            subprocess.run([str(args.build_tools / "apksigner"), "sign", "--ks", str(args.keystore),
                            "--ks-key-alias", args.alias, "--ks-pass", "file:" + str(args.password_file),
                            "--v4-signing-enabled", "false", "--out", str(signed), str(aligned)], env=env, check=True)
            subprocess.run([str(args.build_tools / "zipalign"), "-c", "-P", "16", "4", str(signed)], check=True)
            verify = subprocess.run([str(args.build_tools / "apksigner"), "verify", "--verbose", "--print-certs", str(signed)], env=env, check=True, capture_output=True, text=True)
            certificates.update(line for line in verify.stdout.splitlines() if "certificate SHA-256 digest:" in line)
            (args.work / (name + ".verify.txt")).write_text(verify.stdout + verify.stderr)
            entries[name] = signed.read_bytes()
            print("Verified signature and 16 KiB alignment:", name)
        if len(certificates) != 1:
            raise RuntimeError("Splits have different certificates")
        manifest["total_size"] = sum(map(len, entries.values()))
        entries["manifest.json"] = json.dumps(manifest, ensure_ascii=False, indent=2).encode()
        entries["icon.png"] = original.read("icon.png")
    with zipfile.ZipFile(args.out, "w", compression=zipfile.ZIP_DEFLATED) as out:
        for name, data in entries.items(): out.writestr(name, data)
    print("Created", args.out)
    print(next(iter(certificates)))


if __name__ == "__main__":
    main()
