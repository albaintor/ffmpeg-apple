# FFmpeg Apple — iOS LGPL dynamic builds

Build **unmodified upstream FFmpeg** as seven dynamic iOS/iPadOS **XCFrameworks** (ARM64 device + ARM64 simulator), with release artifacts and corresponding source/configuration metadata. This repository contains **no Home Media Catalog Swift code**.

## Source and licences

- Upstream: [FFmpeg](https://github.com/FFmpeg/FFmpeg)
- Pinned release: **n8.1.3**; pinned commit `1041abdc962f4cc4f394aa8de9dc5236c0c3b9e7` (21 September 2026).
- Intended build licence: **LGPL-2.1-or-later**; `--disable-gpl`, `--disable-nonfree`, `--disable-version3`, `--disable-autodetect`, `--disable-audiotoolbox`; native VideoToolbox supported.
- Files: `Libavutil`, `Libavcodec`, `Libavformat`, `Libavfilter`, `Libavdevice`, `Libswscale`, `Libswresample`. These should be real dynamically linked Mach-O libraries, **not static archives inside .framework folders**.

The build uses FFmpeg's official **unmodified source**; the cross-compilation, framework packaging and module maps are local scripts. The full original source archive and build config are included with each release. See [FFmpeg licensing](https://ffmpeg.org/legal.html). A full dependency and release-binary audit is still required.

## Build

Open **Actions → FFmpeg iOS LGPL dynamic XCFrameworks** to view the current build status. The workflow runs on GitHub's macOS runner after changes to build scripts; it can also be dispatched manually.

To compile locally on a Mac with Xcode:

```bash
python3 scripts/build.py --out dist --work .build-ffmpeg
python3 scripts/make_swiftpm.py --manifest dist/build-manifest.json \
  --tag build-v8.1.3-r1 --output dist/Package.swift
swift package dump-package --package-path dist
```

This creates seven `.xcframework.zip` assets, `build-manifest.json` with SHA256 digests, the original FFmpeg source archive and FFmpeg configure artifacts. The Swift import smoke test (`Tests/FFmpegSmoke.swift`) runs in CI. Debug/simulator builds **do not substitute** for an inspected signed App Store release.

The GitHub Actions workflow has a manual `publish` option. Once all checks pass, dispatch it with **publish=true** and suffix `r1`: it publishes the immutable binary release `build-v8.1.3-r1` with source/configuration files, and a separate semantic SwiftPM tag **`v8.1.3-r1`** with checksum-pinned URLs. If that release already exists, publishing fails rather than replacing binaries.

## Swift Package Manager

After a *successful published release*, add `https://github.com/albaintor/ffmpeg-apple` to an Apple-platform project and select the exact version `8.1.3-r1` (product `FFmpegApple`). All seven binary frameworks are then provided through SwiftPM. **Do not add the package while an unmodified upstream MPVKit already statically embeds FFmpeg**.

The package version tag contains the generated `Package.swift`. The source-build `main` branch intentionally does not carry a manifest pointing at non-existent release ZIPs. Keep the published binary and corresponding source matched.

## Integration with Home Media Catalog

The iOS application is maintained **privately** at [home-media-catalog-ios](https://github.com/albaintor/home-media-catalog-ios), development branch `ffmpeg_lib`. The existing player uses **PrismCore 3.8.0** and **Wenzlik/MPVKit 1.0.1**, whose transitively shipped FFmpeg frameworks are currently **static**. These transitive libraries must be replaced or adjusted **before** adding FFmpegApple to the app. Adding a second FFmpeg does not confer compliance and risks collisions.

Preserve existing local MKV/offline streaming, Dolby Vision/HDR, codecs, audio/subtitles, PiP and VideoToolbox/Metal MEMC by testing the complete package graph and regression media suite. See [migration plan](https://github.com/albaintor/home-media-catalog-ios/blob/ffmpeg_lib/docs/FFMPEG_APPLE_MIGRATION.md) (private access required).

## Legal caveat

**Dynamic linking alone does not certify App Store compliance with LGPL.** LGPL obligations include notices, library source/build provenance, and meaningful library modification/replacement rights. Apple code-signing and distribution restrictions need specialist legal analysis. PrismCore's App Store exception explicitly **does not extend to FFmpeg or MPVKit**. Codec/patent rights and other upstream licences are separate.

Technical build scripts and binaries are public; your proprietary Swift application source need not be published solely because it uses LGPL libraries, provided all applicable terms are satisfied.
