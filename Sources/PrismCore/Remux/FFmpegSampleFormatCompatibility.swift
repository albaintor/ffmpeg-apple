import Libavutil

// FFmpeg 8.1.x keeps the "none" sample format at raw value -1.
// Some Swift/Clang framework module layouts do not re-export the C enum case.
// Preserve PrismCore's existing public behavior without changing FFmpeg binaries.
let AV_SAMPLE_FMT_NONE = AVSampleFormat(rawValue: -1)
