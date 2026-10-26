import Libavutil
import Libavcodec
import Libavformat
import Libavfilter
import Libavdevice
import Libswresample
import Libswscale

// The smoke test only verifies that the XCFrameworks expose importable C modules.
// Runtime playback and end-user replacement rights require separate validation.
func ffmpegVersionSmokeTest() -> UInt32 {
    avcodec_version() ^ avutil_version() ^ avformat_version()
}
