#!/usr/bin/env python3
"""Manually patch a BePTT APK/XAPK with ReVanced and a persistent personal key.

No APK download, device installation, uninstall, or key generation is performed.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile
import zipfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("local-config.json"))
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    for key in ("cli", "bundle", "build_tools", "keystore", "revanced_keystore", "password_file", "packager"):
        if config.get(key) and not Path(config[key]).is_absolute():
            config[key] = str((args.config.resolve().parent / config[key]).resolve())
    required = ("cli", "bundle", "java_home", "build_tools", "keystore", "revanced_keystore", "password_file", "alias", "signer_sha256")
    for key in required:
        if not config.get(key): raise SystemExit("Missing local configuration: " + key)
    for key in ("cli", "bundle", "keystore", "revanced_keystore", "password_file"):
        if not Path(config[key]).is_file(): raise SystemExit("Required local file is missing: " + key)
    if args.out.exists(): raise SystemExit("Output already exists; choose a new output name")
    args.out.parent.mkdir(parents=True, exist_ok=True)
    work_root = config.get("work_root")
    if work_root: Path(work_root).mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix="beptt-revanced-", dir=work_root))
    env = dict(os.environ, JAVA_HOME=str(Path(config["java_home"]).resolve()))
    java = Path(config["java_home"]) / "bin/java"
    tools = Path(config["build_tools"])
    source = args.input.resolve()
    is_xapk = source.suffix.lower() == ".xapk"
    if is_xapk:
        with zipfile.ZipFile(source) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            if manifest.get("package_name") != "y_studio.ka5983.ptt2": raise SystemExit("Not a BePTT XAPK")
            bases = [s["file"] for s in manifest["split_apks"] if s["id"] == "base"]
            if len(bases) != 1 or Path(bases[0]).name != bases[0]: raise SystemExit("Invalid base entry")
            base = work / "original-base.apk"
            base.write_bytes(archive.read(bases[0]))
        if args.out.suffix.lower() != ".xapk": raise SystemExit("XAPK input requires .xapk output")
    else:
        if source.suffix.lower() != ".apk" or args.out.suffix.lower() != ".apk": raise SystemExit("Use .apk → .apk or .xapk → .xapk")
        base = source
    badging = subprocess.run([str(tools / "aapt"), "dump", "badging", str(base)], env=env, check=True, capture_output=True, text=True).stdout
    if "package: name='y_studio.ka5983.ptt2'" not in badging: raise SystemExit("Not a BePTT APK")
    print(badging.splitlines()[0], flush=True)
    signed_base = work / "revanced-base.apk"
    secret_args = work / "cli-private.args"
    password = Path(config["password_file"]).read_text().strip()
    # Picocli argument files keep credentials out of the process argument list.
    values = ["-p", config["bundle"], "-b", "-o", str(signed_base), "-t", str(work / "cli-temp"),
              "--keystore", config["revanced_keystore"],
              "--keystore-entry-alias", config["alias"], "--keystore-entry-password", password, str(base)]
    secret_args.touch(mode=0o600)
    secret_args.write_text("\n".join(json.dumps(value, ensure_ascii=False) for value in values) + "\n")
    try:
        # -b applies only to our locally supplied custom .rvp, without a remote
        # provenance signature. It does not change APK or device verification.
        result = subprocess.run([str(java), "-jar", config["cli"], "patch", "@" + str(secret_args)], env=env,
                                capture_output=True, text=True)
        output = result.stdout + result.stderr
        (work / "revanced.log").write_text(output)
        print(output, flush=True)
        if result.returncode != 0 or "BePTT URL filter: validated structural matches;" not in output or '"BePTT exact image URL blacklist" succeeded' not in output:
            raise SystemExit("Patch did not succeed; no deliverable was packaged. See " + str(work / "revanced.log"))
    finally:
        secret_args.unlink(missing_ok=True)
    if not signed_base.exists(): raise SystemExit("ReVanced produced no patched base; nothing packaged")
    if is_xapk:
        packager = Path(config["packager"]) if config.get("packager") else Path(__file__).resolve().parent.parent / "patch/package_xapk.py"
        subprocess.run(["python3", str(packager), str(source), str(signed_base), "--work", str(work / "signed"),
                        "--out", str(args.out), "--build-tools", config["build_tools"], "--java-home", config["java_home"],
                        "--keystore", config["keystore"], "--alias", config["alias"], "--password-file", config["password_file"]], env=env, check=True)
        verify_base = work / "signed" / bases[0]
    else:
        aligned = work / "aligned.apk"
        subprocess.run([str(tools / "zipalign"), "-f", "-P", "16", "4", str(signed_base), str(aligned)], check=True)
        subprocess.run([str(tools / "apksigner"), "sign", "--ks", config["keystore"], "--ks-key-alias", config["alias"],
                        "--ks-pass", "file:" + config["password_file"], "--v4-signing-enabled", "false", "--out", str(args.out), str(aligned)], env=env, check=True)
        verify_base = args.out
    verified = subprocess.run([str(tools / "apksigner"), "verify", "--print-certs", str(verify_base)], env=env, check=True, capture_output=True, text=True).stdout
    digest_line = next(line for line in verified.splitlines() if "certificate SHA-256 digest:" in line)
    digest = digest_line.split(":", 1)[1].strip()
    if digest.lower() != config["signer_sha256"].lower():
        args.out.unlink()
        raise SystemExit("Signing certificate changed; output removed to prevent an incompatible update")
    print("\n完成：", args.out.resolve())
    print("已確認沿用原簽章。設定檔及黑名單未重設；本工具未安裝或解除安裝 App。")
    print("建置紀錄：", work)


if __name__ == "__main__":
    main()
