#!/usr/bin/env python3
"""Patch only the verified BePTT 7.3.0 base. Keep original resources/splits.

Tools are explicit local paths; this script downloads nothing and never installs.
The output is unsigned and must be aligned/signed with the splits afterwards.
"""
import argparse
import hashlib
import pathlib
import subprocess
import zipfile

BASE_SHA256 = "c8a3fd72d976c8960a8234e59ca8604fa76cdf2ade59f42171178f243f016190"


def replace_once(path, old, new):
    text = path.read_text()
    if text.count(old) != 1:
        raise RuntimeError(f"Unexpected patch anchor in {path.name}; refusing to patch")
    path.write_text(text.replace(old, new, 1))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base", type=pathlib.Path)
    parser.add_argument("--work", required=True, type=pathlib.Path)
    parser.add_argument("--android-jar", required=True, type=pathlib.Path)
    parser.add_argument("--r8-jar", required=True, type=pathlib.Path)
    parser.add_argument("--java-home", required=True, type=pathlib.Path)
    parser.add_argument("--apktool", default="apktool")
    args = parser.parse_args()
    if hashlib.sha256(args.base.read_bytes()).hexdigest() != BASE_SHA256:
        raise SystemExit("Base APK differs from verified 7.3.0: refusing to patch")
    args.work.mkdir(parents=True, exist_ok=False)
    source = pathlib.Path(__file__).resolve().parent
    java = args.java_home / "bin/java"
    javac = args.java_home / "bin/javac"
    classes = args.work / "helper-classes"
    dex = args.work / "helper-dex"
    classes.mkdir()
    dex.mkdir()
    subprocess.run([str(javac), "--release", "8", "-encoding", "UTF-8", "-cp", str(args.android_jar), "-d", str(classes),
                    *map(str, source.glob("stubs/**/*.java")), *map(str, source.glob("src/*.java"))], check=True)
    helpers = args.work / "helpers.jar"
    with zipfile.ZipFile(helpers, "w") as archive:
        for item in classes.glob("Beptt*.class"):
            archive.write(item, item.name)
    subprocess.run([str(java), "-cp", str(args.r8_jar), "com.android.tools.r8.D8", "--min-api", "23",
                    "--lib", str(args.android_jar), "--classpath", str(classes), "--output", str(dex), str(helpers)], check=True)
    decoded = args.work / "decoded"
    subprocess.run([args.apktool, "d", "-r", "-o", str(decoded), str(args.base)], check=True)
    article = decoded / "smali/d30.smali"
    replace_once(article, "    new-instance v8, Lqh2;", """    # Exact image URL filter: skip preview AND gallery insertion.
    invoke-static {v5, v0}, LBepttImageFilter;->shouldHide(Ljava/lang/String;Lqr5;)Z
    move-result v10
    if-nez v10, :cond_13

    new-instance v8, Lqh2;""")
    settings = decoded / "smali/tw/ystudio/beptt/presentation/setting/SettingActivity.smali"
    replace_once(settings, ".method public final onCreateOptionsMenu(Landroid/view/Menu;)Z\n    .locals 2", """.method public final onCreateOptionsMenu(Landroid/view/Menu;)Z
    .locals 2

    invoke-static {p1, p0}, LBepttImageFilter;->addSettingsMenu(Landroid/view/Menu;Landroid/app/Activity;)V""")
    rebuilt = args.work / "rebuilt.apk"
    subprocess.run([args.apktool, "b", str(decoded), "-o", str(rebuilt)], check=True)
    output = args.work / "base-filter-unsigned.apk"
    with zipfile.ZipFile(args.base) as original, zipfile.ZipFile(rebuilt) as built, zipfile.ZipFile(output, "w") as out:
        if "classes3.dex" in original.namelist():
            raise RuntimeError("Unexpected third dex")
        for entry in original.infolist():
            # Strip obsolete signatures. Every other entry is preserved byte-for-byte
            # after decompression, including manifest, resource table and classes2.
            if entry.filename.startswith("META-INF/") and entry.filename.upper().endswith((".SF", ".RSA", ".DSA", ".EC", "MANIFEST.MF")):
                continue
            data = built.read("classes.dex") if entry.filename == "classes.dex" else original.read(entry.filename)
            out.writestr(entry, data)
        out.write(dex / "classes.dex", "classes3.dex", compress_type=zipfile.ZIP_DEFLATED)
    with zipfile.ZipFile(args.base) as original, zipfile.ZipFile(output) as patched:
        changed = [name for name in original.namelist() if name in patched.namelist() and original.read(name) != patched.read(name)]
        assert changed == ["classes.dex"], changed
    print(f"Created {output}; only original classes.dex changed; helper classes3.dex added")


if __name__ == "__main__":
    main()
