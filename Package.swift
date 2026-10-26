// swift-tools-version: 6.0
// GENERATED from matching FFmpeg release artifacts; do not hand-edit checksums.
import PackageDescription

let package = Package(
    name: "FFmpegApple",
    platforms: [.iOS(.v17)],
    products: [
        .library(name: "FFmpegApple", targets: [
            "Libavutil", "Libswresample", "Libswscale", "Libavcodec", "Libavformat", "Libavfilter", "Libavdevice"
        ])
    ],
    targets: [
        .binaryTarget(name: "Libavutil", url: "https://github.com/albaintor/ffmpeg-apple/releases/download/build-v8.1.3-r1/Libavutil.xcframework.zip", checksum: "bcdfcdef4e8b64909dd773e5267d91d4f54deef84e1c330e44b866bd282588f4"),
        .binaryTarget(name: "Libswresample", url: "https://github.com/albaintor/ffmpeg-apple/releases/download/build-v8.1.3-r1/Libswresample.xcframework.zip", checksum: "04e1c3167f6cd82069d6d274aae398d783f7d2fc02522f5db969deda26b7c64a"),
        .binaryTarget(name: "Libswscale", url: "https://github.com/albaintor/ffmpeg-apple/releases/download/build-v8.1.3-r1/Libswscale.xcframework.zip", checksum: "710fee5a044f9b0d4b0814576dbcbbb52026d0c73d014878c5c4f1769c5d1917"),
        .binaryTarget(name: "Libavcodec", url: "https://github.com/albaintor/ffmpeg-apple/releases/download/build-v8.1.3-r1/Libavcodec.xcframework.zip", checksum: "aa27c89afb2da29041cc8c9e47320bf2d87c0cac258272be3bb8bde49f27ee83"),
        .binaryTarget(name: "Libavformat", url: "https://github.com/albaintor/ffmpeg-apple/releases/download/build-v8.1.3-r1/Libavformat.xcframework.zip", checksum: "bcb5eb925099d417983100d0b881a824c354f63c4b23f54decafa7fd497b4150"),
        .binaryTarget(name: "Libavfilter", url: "https://github.com/albaintor/ffmpeg-apple/releases/download/build-v8.1.3-r1/Libavfilter.xcframework.zip", checksum: "fa832b870759ec34c5091995a75eddc19641f2d416558a78c16def0000e6d7b5"),
        .binaryTarget(name: "Libavdevice", url: "https://github.com/albaintor/ffmpeg-apple/releases/download/build-v8.1.3-r1/Libavdevice.xcframework.zip", checksum: "46dd0f3b4d97477e29e2e378f8f10d3b20cbb1d284907604a861137e9813a7b1")
    ]
)
