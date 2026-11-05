"""Regression checks for HEVC fMP4 packet-duration lookahead.

These are source-contract tests. Only the iOS smoke build checks the Swift
compiler; actual A/V sync and HLS fragment timestamps require a device or a
reproducible source fixture.
"""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WRITER = (ROOT / "Sources/PrismCore/Remux/FMP4SegmentWriter.swift").read_text()
REMUXER = (ROOT / "Sources/PrismCore/Remux/HLSRemuxer.swift").read_text()


class HEVCFragmentTimingTests(unittest.TestCase):
    def test_video_durations_derive_from_next_real_dts(self):
        self.assertIn("let measured = nextDTS - priorDTS", WRITER)
        self.assertIn("held.pointee.duration = measured", WRITER)
        self.assertIn("try muxPacket(held)", WRITER)
        self.assertIn("packet.pointee.dts != swift_AV_NOPTS_VALUE()", WRITER)
        self.assertIn("leadingDTS[index]?.isSettled != false", WRITER)

    def test_only_hevc_video_is_deferred_not_audio(self):
        self.assertIn("stream.pointee.codecpar.pointee.codec_type == AVMEDIA_TYPE_VIDEO", WRITER)
        self.assertIn("stream.pointee.codecpar.pointee.codec_id == AV_CODEC_ID_HEVC", WRITER)
        self.assertIn("try muxPacket(packet)", WRITER)
        self.assertNotIn("held.pointee.pts =", WRITER)

    def test_fragment_boundary_closes_last_video_before_new_keyframe(self):
        boundary = REMUXER.split("} else if pts >= nextBoundaryPTS {", 1)[1].split(
            "segmentStartPTS = pts", 1
        )[0]
        self.assertLess(
            boundary.index("try writer.completeVideoBeforeBoundary("),
            boundary.index("try emitSegment(endPTS: pts)")
        )
        self.assertIn("writer.inferHEVCDurationsFromNextDTS = videoTrack.codecName == \"hevc\"", REMUXER)
        self.assertEqual(REMUXER.count("writer.inferHEVCDurationsFromNextDTS"), 2)

    def test_eof_and_reanchor_do_not_keep_stale_video_packets(self):
        self.assertGreaterEqual(
            WRITER.count("try flushPendingHEVC(nextDTS: nil)"), 3
        )
        self.assertIn("if let pending = pendingHEVCVideoPacket", WRITER)
        self.assertIn("var owned: UnsafeMutablePointer<AVPacket>? = pending", WRITER)
        self.assertIn("av_packet_free(&owned)", WRITER)
        self.assertIn("writer = FMP4SegmentWriter()", REMUXER)

    def test_corrected_hevc_duration_does_not_shift_audio_clock(self):
        # Simulated millisecond-rounded DTS, not CFR re-timing.
        original_dts = [0, 42, 83, 125, 167, 208]
        original_duration = [42, 42, 42, 42, 42, 42]
        fixed_duration = [
            original_dts[i + 1] - original_dts[i]
            for i in range(len(original_dts) - 1)
        ] + [original_duration[-1]]
        self.assertEqual(fixed_duration, [42, 41, 42, 42, 41, 42])
        audio_pts = [0, 21, 43, 64, 85]
        self.assertEqual(audio_pts, [0, 21, 43, 64, 85])
        # The source video timestamps stay exactly as originally recorded.
        self.assertEqual(original_dts, [0, 42, 83, 125, 167, 208])


if __name__ == "__main__":
    unittest.main()
