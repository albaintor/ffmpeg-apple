#!/usr/bin/env python3
"""Regression checks for the exact n8.1.3 movenc check_pkt workaround."""
from __future__ import annotations
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from movenc_pts_patch import apply

SAMPLE = """
static int check_pkt(void)
{
    if (pkt->dts < ref) {
        pkt->dts = ref + 1;
        pkt->pts = AV_NOPTS_VALUE;
    }
    return 0;
}
static int another_function(void)
{
    return 0;
}
"""


class MovencPTSPatchTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        target = self.root / "libavformat"
        target.mkdir()
        self.mov = target / "movenc.c"

    def test_preserves_composition_offset_only_in_check_pkt(self) -> None:
        self.mov.write_text(SAMPLE)
        apply(self.root)
        result = self.mov.read_text()
        self.assertIn("pkt->pts += ref + 1 - pkt->dts;", result)
        self.assertIn("if (pkt->dts < ref && pkt->pts != AV_NOPTS_VALUE)", result)
        self.assertIn("pkt->dts = ref + 1;", result)
        self.assertEqual(result.count("pkt->pts += ref + 1 - pkt->dts;"), 1)

    def test_idempotent(self) -> None:
        self.mov.write_text(SAMPLE)
        apply(self.root)
        first = self.mov.read_bytes()
        apply(self.root)
        self.assertEqual(self.mov.read_bytes(), first)

    def test_refuses_unknown_upstream_source(self) -> None:
        self.mov.write_text(SAMPLE.replace("pkt->dts = ref + 1;", "pkt->dts = ref;"))
        with self.assertRaises(RuntimeError):
            apply(self.root)

    def test_does_not_modify_other_functions(self) -> None:
        text = SAMPLE + "\nstatic int other(void) {\n    pkt->dts = ref + 1;\n    pkt->pts = AV_NOPTS_VALUE;\n}\n"
        self.mov.write_text(text)
        apply(self.root)
        result = self.mov.read_text()
        self.assertEqual(result.count("pkt->pts = AV_NOPTS_VALUE;"), 2)
        self.assertIn("static int other(void) {\n    pkt->dts = ref + 1;", result)


if __name__ == "__main__":
    unittest.main()
