// swift-tools-version: 6.0
import PackageDescription

// Source-compatible fork of Wenzlik/PrismCore 3.8.0.
// The library depends on the LOCAL adapted LGPL MPVKit package, never on
// a second, remotely fetched MPVKit with the same package identity.
// The complete upstream PrismCore source and licence are retained.
let package = Package(
    name: "PrismCore",
    platforms: [.iOS(.v16), .tvOS(.v17), .macOS(.v14), .visionOS(.v1)],
    products: [.library(name: "PrismCore", targets: ["PrismCore"])],
    dependencies: [
        .package(path: "adapters/MPVKit")
    ],
    targets: [
        .binaryTarget(
            name: "TrueHDObjects",
            url: "https://github.com/Wenzlik/PrismCore/releases/download/3.8.0/TrueHDObjects.xcframework.zip",
            checksum: "0549e89d51ae8b8dcfc400002150e41f9eb0ce207ff1bbb63b53783bcf4c0d39"
        ),
        .target(
            name: "PrismCore",
            dependencies: [
                .product(name: "MPVKit", package: "MPVKit"),
                "TrueHDObjects"
            ],
            path: "Sources/PrismCore",
            swiftSettings: [.swiftLanguageMode(.v5)]
        )
    ]
)
