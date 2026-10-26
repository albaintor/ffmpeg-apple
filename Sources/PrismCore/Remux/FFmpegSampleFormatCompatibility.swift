import Libavutil

// FFmpeg 8.1.x keeps the "none" sample format at raw value -1.
// Some Swift/Clang framework module layouts do not re-export the C enum case.
// Preserve PrismCore's existing public behavior without changing FFmpeg binaries.
let AV_SAMPLE_FMT_NONE = AVSampleFormat(rawValue: -1)

 // Swift's Clang importer may omit FFmpeg C enum constants even though it
 // exposes the AVChannel type, including channel_layout APIs.
 // FFmpeg AV_CHAN_NONE=-1 and AV_CHAN_FRONT_CENTER=2.
let AV_CHAN_NONE = AVChannel(rawValue: -1)
let AV_CHAN_FRONT_CENTER = AVChannel(rawValue: 2)
