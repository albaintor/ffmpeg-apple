#!/usr/bin/env python3
"""Upgrade PrismCore's MPVKit FFmpeg adapter from a verified release.

Refuse a release without zlib + bzip2 on both platforms, matching SHA-256
archives, seven complete dynamic XCFrameworks, or original device/simulator
dSYMs. Archive UUID matching is verified separately in the iOS application.
"""
from __future__ import annotations
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

LIBRARIES = ("Libavcodec", "Libavdevice", "Libavfilter", "Libavformat",
             "Libavutil", "Libswresample", "Libswscale")
PUBLISHER = "https://github.com/albaintor/ffmpeg-apple/releases/download"
TAG_PATTERN = re.compile(r"build-v\d+\.\d+\.\d+-r\d+\Z")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda: fp.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def require_symbols(archive: Path, lib: str) -> None:
    with zipfile.ZipFile(archive) as z:
        paths = z.namelist()
    for platform in ("ios-arm64", "ios-arm64-simulator"):
        binaries = [p for p in paths if
                    f"{platform}/{lib}.framework/" in p and p.endswith("/" + lib)]
        syms = [p for p in paths if
                f"{platform}/dSYMs/{lib}.framework.dSYM/" in p
                and p.endswith("/DWARF/" + lib)]
        if not binaries or not syms:
            raise ValueError(f"{lib}: missing {platform} executable or original dSYM")


def validate(dist: Path) -> dict:
    manifest = json.loads((dist / "build-manifest.json").read_text())
    if set(manifest.get("ffmpeg_libraries", {})) != set(LIBRARIES):
        raise ValueError("Release must contain exactly seven FFmpeg libraries")
    # n8.1.3 does not have the movenc PTS fix upstream. Never downgrade to
    # an unpatched n8.1.3 binary even if its SHA-256 and dSYMs are valid.
    if manifest.get("tag") == "n8.1.3" and not any(
        item.get("name") == "movenc-preserve-pts-on-dts-correction"
        for item in manifest.get("source_modifications", [])
    ):
        raise ValueError("FFmpeg n8.1.3 release lacks the required movenc PTS fix")
    for name, entry in [*manifest["ffmpeg_libraries"].items(),
                        ("source", manifest.get("source_archive", {}))]:
        filename = entry.get("file", "")
        if Path(filename).name != filename or not filename:
            raise ValueError(f"{name}: invalid filename")
        path = dist / filename
        expected = entry.get("sha256", "")
        if not re.fullmatch(r"[a-fA-F0-9]{64}", expected):
            raise ValueError(f"{name}: invalid SHA-256")
        if not path.is_file() or sha256(path) != expected.lower():
            raise ValueError(f"{name}: missing or SHA-256-mismatched archive")
        if name != "source":
            require_symbols(path, name)
        elif manifest.get("tag") == "n8.1.3":
            with zipfile.ZipFile(path) as archive:
                entries = [p for p in archive.namelist()
                           if p.endswith("/libavformat/movenc.c")]
                if len(entries) != 1 or (
                    b"Preserve presentation offset when correcting decode timestamp"
                    not in archive.read(entries[0])
                ):
                    raise ValueError("Matching FFmpeg source is missing the movenc patch")
    for platform in ("iphoneos", "iphonesimulator"):
        config = (dist / f"config-{platform}.mak").read_text()
        for feature in ("ZLIB", "BZLIB"):
            if not re.search(rf"^CONFIG_{feature}=yes$", config, re.MULTILINE):
                raise ValueError(f"{platform}: required CONFIG_{feature}=yes missing")
        for feature in ("GPL", "NONFREE", "VERSION3"):
            if re.search(rf"^CONFIG_{feature}=yes$", config, re.MULTILINE):
                raise ValueError(f"{platform}: forbidden CONFIG_{feature}=yes")
    return manifest


def update_package(contents: str, release: str, manifest: dict) -> str:
    if not TAG_PATTERN.fullmatch(release):
        raise ValueError("Invalid release tag")
    for name in LIBRARIES:
        entry = manifest["ffmpeg_libraries"][name]
        pattern = re.compile(
            rf'(\.binaryTarget\(\s*name:\s*"{re.escape(name)}"\s*,\s*url:\s*")'
            rf'[^"]+("\s*,\s*checksum:\s*")[0-9a-f]{{64}}("\s*\))',
            re.MULTILINE,
        )
        url = f"{PUBLISHER}/{release}/{entry['file']}"
        contents, count = pattern.subn(
            lambda m: m.group(1) + url + m.group(2)
            + entry["sha256"].lower() + m.group(3), contents
        )
        if count != 1:
            raise ValueError(f"{name}: expected one binaryTarget, found {count}")
    contents = re.sub(
        r"from albaintor/ffmpeg-apple v\d+\.\d+\.\d+-r\d+",
        f"from albaintor/ffmpeg-apple {release}", contents, count=1,
    )
    return contents


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", required=True)
    parser.add_argument("--dist", required=True, type=Path)
    parser.add_argument("--package", required=True, type=Path)
    args = parser.parse_args()
    try:
        manifest = validate(args.dist)
        old = args.package.read_text()
        new = update_package(old, args.release, manifest)
        if new != old:
            args.package.write_text(new)
        print(f"Verified {args.release}: seven SHA-256s, source, device/simulator dSYMs, zlib+bzip2")
        print("MPVKit adapter:", "updated" if new != old else "already current")
    except (ValueError, KeyError, OSError, zipfile.BadZipFile,
            json.JSONDecodeError) as exc:
        print(f"FFmpeg upgrade refused: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
