#!/usr/bin/env python3
"""Emit a SwiftPM manifest from verified GitHub Release build-manifest.json."""
import argparse
import json
from pathlib import Path
import re

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("dist/build-manifest.json"))
    parser.add_argument("--tag", required=True, help="Existing immutable GitHub Release tag")
    parser.add_argument("--output", type=Path, default=Path("dist/Package.swift"))
    args = parser.parse_args()
    if not re.fullmatch(r"[a-zA-Z0-9][a-zA-Z0-9._-]{0,99}", args.tag):
        raise SystemExit("Invalid release tag")
    metadata = json.loads(args.manifest.read_text())
    libs = metadata["ffmpeg_libraries"]
    expected = ["Libavutil", "Libswresample", "Libswscale", "Libavcodec",
                "Libavformat", "Libavfilter", "Libavdevice"]
    if sorted(libs) != sorted(expected):
        raise SystemExit("Incomplete FFmpeg component set")
    items = []
    for name in expected:
        info = libs[name]
        checksum = info["sha256"]
        if not re.fullmatch(r"[a-f0-9]{64}", checksum):
            raise SystemExit(f"Invalid checksum for {name}")
        url = f"https://github.com/albaintor/ffmpeg-apple/releases/download/{args.tag}/{info['file']}"
        items.append(f'        .binaryTarget(name: "{name}", url: "{url}", checksum: "{checksum}")')
    manifest = (
        "// swift-tools-version: 6.0\n"
        "// GENERATED from matching FFmpeg release artifacts; do not hand-edit checksums.\n"
        "import PackageDescription\n\n"
        "let package = Package(\n"
        '    name: "FFmpegApple",\n'
        '    platforms: [.iOS(.v17)],\n'
        "    products: [\n"
        '        .library(name: "FFmpegApple", targets: [\n'
        + "            " + ", ".join(f'"{name}"' for name in expected) + "\n"
        "        ])\n"
        "    ],\n"
        "    targets: [\n"
        + ",\n".join(items) + "\n"
        "    ]\n"
        ")\n"
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(manifest)
    print(f"Generated {args.output} referencing {args.tag}")

if __name__ == "__main__":
    main()
