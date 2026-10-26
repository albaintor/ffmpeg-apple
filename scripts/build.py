#!/usr/bin/env python3
"""Build unmodified upstream FFmpeg as LGPL shared XCFrameworks for iOS.

Run on macOS with Xcode command-line tools. Does not link PrismCore or the app.
A binary is NOT legally cleared merely because this script succeeds.
"""
from __future__ import annotations
import argparse
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys
import zipfile

VERSION = "n8.1.3"
COMMIT = "1041abdc962f4cc4f394aa8de9dc5236c0c3b9e7"
UPSTREAM = "https://github.com/FFmpeg/FFmpeg.git"
LIBS = ("avutil", "swresample", "swscale", "avcodec", "avformat", "avfilter", "avdevice")
MIN_IOS = "17.0"

def cmd(*args: str, cwd: Path | None = None, capture: bool = False) -> str:
    print("+", " ".join(map(str, args)), flush=True)
    result = subprocess.run(list(map(str, args)), cwd=cwd, check=True,
                            text=True, stdout=subprocess.PIPE if capture else None)
    return (result.stdout or "").strip()

def fetch(root: Path) -> Path:
    source = root / "upstream"
    if not source.exists():
        cmd("git", "clone", "--filter=blob:none", "--branch", VERSION, "--depth", "1", UPSTREAM, source)
    actual = cmd("git", "rev-parse", "HEAD", cwd=source, capture=True)
    if actual != COMMIT:
        raise RuntimeError(f"FFmpeg source mismatch: expected {COMMIT}, found {actual}")
    if cmd("git", "status", "--porcelain", cwd=source, capture=True):
        raise RuntimeError("FFmpeg upstream working tree must not be modified")
    return source

def build_slice(source: Path, root: Path, sdk: str) -> tuple[Path, Path]:
    build = root / f"build-{sdk}"
    prefix = root / f"install-{sdk}"
    build.mkdir(parents=True, exist_ok=True)
    platform = "ios" if sdk == "iphoneos" else "ios-simulator"
    target = f"arm64-apple-{platform}{MIN_IOS}"
    sysroot = cmd("xcrun", "--sdk", sdk, "--show-sdk-path", capture=True)
    clang = cmd("xcrun", "--sdk", sdk, "--find", "clang", capture=True)
    sdkflags = f"-target {target} -isysroot {sysroot} -O2 -fPIC"
    common = [
        f"--prefix={prefix}", "--target-os=darwin", "--arch=aarch64",
        "--enable-cross-compile", f"--cc={clang}", f"--sysroot={sysroot}",
        f"--extra-cflags={sdkflags}", f"--extra-ldflags=-target {target} -isysroot {sysroot}",
        "--enable-shared", "--disable-static", "--enable-pic",
        "--disable-programs", "--disable-doc", "--disable-debug",
        "--disable-autodetect", "--disable-audiotoolbox",
        "--disable-gpl", "--disable-nonfree", "--disable-version3",
        "--enable-videotoolbox", "--install-name-dir=@rpath",
    ]
    cmd(source / "configure", *common, cwd=build)
    config = (build / "ffbuild" / "config.mak").read_text()
    if "CONFIG_GPL=yes" in config or "CONFIG_NONFREE=yes" in config or "CONFIG_VERSION3=yes" in config:
        raise RuntimeError("Forbidden GPL/nonfree/version3 FFmpeg configuration")
    jobs = min(os.cpu_count() or 4, 6)
    cmd("make", "-j", str(jobs), cwd=build)
    cmd("make", "install", cwd=build)
    if not (prefix / "include" / "libavcodec" / "avcodec.h").is_file():
        raise RuntimeError("FFmpeg headers missing after install")
    return prefix, build

def dylib(prefix: Path, lib: str) -> Path:
    files = sorted((prefix / "lib").glob(f"lib{lib}.*.dylib"))
    if not files:
        raise RuntimeError(f"Missing dynamic library lib{lib} in {prefix}")
    return files[0].resolve()

def framework(prefix: Path, root: Path, sdk: str, lib: str) -> Path:
    name = "Lib" + lib
    dest = root / "frameworks" / sdk / (name + ".framework")
    if dest.exists():
        shutil.rmtree(dest)
    (dest / "Modules").mkdir(parents=True)
    shutil.copy2(dylib(prefix, lib), dest / name)
    # Headers from all built FFmpeg modules are required for cross-module C includes.
    shutil.copytree(prefix / "include", dest / "Headers")
    (dest / "Headers" / (name + ".h")).write_text(
        f"#pragma once\n#include \"lib{lib}/{lib}.h\"\n"
        if lib not in ("swresample", "swscale") else
        f"#pragma once\n#include \"lib{lib}/{lib}.h\"\n"
    )
    (dest / "Modules" / "module.modulemap").write_text(
        f"framework module {name} {{\n"
        f"    umbrella header \"{name}.h\"\n"
        f"    export *\n"
        f"    module * {{ export * }}\n"
        f"}}\n"
    )
    with (dest / "Info.plist").open("wb") as fp:
        plistlib.dump({
            "CFBundleDevelopmentRegion": "en",
            "CFBundleExecutable": name,
            "CFBundleIdentifier": f"fr.albaintor.ffmpeg.{name.lower()}",
            "CFBundleInfoDictionaryVersion": "6.0",
            "CFBundleName": name,
            "CFBundlePackageType": "FMWK",
            "CFBundleShortVersionString": VERSION.removeprefix("n"),
            "CFBundleVersion": "1",
            "MinimumOSVersion": MIN_IOS,
        }, fp)
    binary = dest / name
    cmd("install_name_tool", "-id", f"@rpath/{name}.framework/{name}", binary)
    linked = cmd("otool", "-L", binary, capture=True).splitlines()[1:]
    for line in linked:
        old = line.strip().split(" (", 1)[0]
        match = re.search(r"/?lib(avcodec|avdevice|avfilter|avformat|avutil|swresample|swscale)(?:\.[0-9]+)*\.dylib$", old)
        if match:
            replacement = "Lib" + match.group(1)
            cmd("install_name_tool", "-change", old,
                f"@rpath/{replacement}.framework/{replacement}", binary)
    final = cmd("otool", "-L", binary, capture=True)
    if re.search(r"lib(?:avcodec|avdevice|avfilter|avformat|avutil|swresample|swscale)\.[0-9]+\.dylib", final):
        raise RuntimeError(f"Unrewritten FFmpeg dependency in {name}: {final}")
    info = cmd("file", binary, capture=True)
    if "dynamically linked shared library" not in info and "dynamically linked" not in info:
        raise RuntimeError(f"{name} is not a dylib: {info}")
    (dest / "LICENSE-FFMPEG.txt").write_text(
        "FFmpeg: LGPL-2.1-or-later build without --enable-gpl/--enable-nonfree/--enable-version3.\n"
        "See the release's matching original source archive, COPYING.LGPLv2.1 and build configuration.\n"
        "https://ffmpeg.org/legal.html\n"
    )
    return dest

def zip_xcframework(source: Path, dest: Path) -> None:
    with zipfile.ZipFile(dest, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file():
                archive.write(path, (Path(source.name) / path.relative_to(source)).as_posix())

def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()

def main() -> None:
    if sys.platform != "darwin":
        raise SystemExit("macOS with Xcode required")
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("dist"))
    parser.add_argument("--work", type=Path, default=Path(".build-ffmpeg"))
    args = parser.parse_args()
    work = args.work.resolve()
    out = args.out.resolve()
    work.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)
    source = fetch(work)
    installed = {}
    for sdk in ("iphoneos", "iphonesimulator"):
        installed[sdk], build = build_slice(source, work, sdk)
        shutil.copy2(build / "ffbuild" / "config.mak", out / f"config-{sdk}.mak")
        shutil.copy2(build / "config.h", out / f"config-{sdk}.h")
    artifacts = {}
    for lib in LIBS:
        device = framework(installed["iphoneos"], work, "iphoneos", lib)
        simulator = framework(installed["iphonesimulator"], work, "iphonesimulator", lib)
        name = "Lib" + lib
        target = out / (name + ".xcframework")
        if target.exists():
            shutil.rmtree(target)
        cmd("xcodebuild", "-create-xcframework", "-framework", device,
            "-framework", simulator, "-output", target)
        archive = out / (name + ".xcframework.zip")
        zip_xcframework(target, archive)
        artifacts[name] = {"file": archive.name, "sha256": sha256(archive)}
    # Archive the source tree exactly as built, excluding .git and build outputs.
    source_archive = out / f"FFmpeg-{VERSION}-source.zip"
    zip_xcframework(source, source_archive)
    report = {
        "source": UPSTREAM, "tag": VERSION, "git_sha": COMMIT, "minimum_ios": MIN_IOS,
        "platforms": ["ios-arm64", "ios-simulator-arm64"],
        "license_intent": "LGPL-2.1-or-later (verify final config; external licensing review required)",
        "ffmpeg_libraries": artifacts,
        "source_archive": {"file": source_archive.name, "sha256": sha256(source_archive)},
        "note": "Does not prove full iOS application's licence compliance or parity with MPVKit.",
    }
    (out / "build-manifest.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
