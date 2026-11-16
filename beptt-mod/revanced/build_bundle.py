#!/usr/bin/env python3
"""Build a JVM + Android ReVanced .rvp bundle with local, explicit tools."""
import argparse
import os
from pathlib import Path
import subprocess
import zipfile


def run(*command, env):
    subprocess.run(list(map(str, command)), env=env, check=True)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--cli", type=Path, required=True)
    p.add_argument("--kotlinc", type=Path, required=True)
    p.add_argument("--android-jar", type=Path, required=True)
    p.add_argument("--r8", type=Path, required=True)
    p.add_argument("--java-home", type=Path, required=True)
    p.add_argument("--work", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    a.work.mkdir(parents=True, exist_ok=False)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, JAVA_HOME=str(a.java_home.resolve()))
    root = Path(__file__).resolve().parent
    java = a.java_home / "bin/java"
    javac = a.java_home / "bin/javac"
    helpers = a.work / "helpers"
    helpers.mkdir()
    run(javac, "--release", "8", "-encoding", "UTF-8", "-cp", a.android_jar, "-d", helpers,
        root / "src/BepttImageFilter.java", root.parent / "patch/src/BepttUrlRules.java", env=env)
    helper_jar = a.work / "helpers.jar"
    with zipfile.ZipFile(helper_jar, "w") as z:
        for f in helpers.glob("*.class"): z.write(f, f.name)
    extension = a.work / "extension"
    extension.mkdir()
    run(java, "-cp", a.r8, "com.android.tools.r8.D8", "--min-api", "23", "--lib", a.android_jar,
        "--output", extension, helper_jar, env=env)
    patch_jar = a.work / "patches.jar"
    # ReVanced 22's published classes carry Kotlin experimental metadata.
    run(a.kotlinc, "-jvm-target", "17", "-Xcontext-parameters", "-Xskip-prerelease-check", "-classpath", a.cli, "-d", patch_jar,
        root / "src/BepttPatch.kt", env=env)
    android = a.work / "android-patches"
    android.mkdir()
    run(java, "-cp", a.r8, "com.android.tools.r8.D8", "--min-api", "26", "--lib", a.android_jar,
        "--classpath", a.cli, "--output", android, patch_jar, env=env)
    manifest = "\r\n".join([
        "Manifest-Version: 1.0", "Name: BePTT Image URL Patches", "Version: 1.0.0",
        "Description: Exact image URL blacklist with persistent settings",
        "Author: 29988122", "Source: https://github.com/29988122/29988122",
        "License: GPL-3.0-only", "", "",
    ])
    with zipfile.ZipFile(a.out, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("META-INF/MANIFEST.MF", manifest)
        with zipfile.ZipFile(patch_jar) as compiled:
            for entry in compiled.infolist():
                if entry.filename.upper() != "META-INF/MANIFEST.MF": z.writestr(entry.filename, compiled.read(entry.filename))
        z.write(android / "classes.dex", "classes.dex")
        z.write(extension / "classes.dex", "extensions/beptt.rve")
    print("Built ReVanced bundle:", a.out)


if __name__ == "__main__":
    main()
