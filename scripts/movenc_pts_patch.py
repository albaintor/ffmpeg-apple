#!/usr/bin/env python3
"""Surgical FFmpeg n8.1.3 movenc timestamp fix for fragmented MP4.

Based on the first change from FFmpeg PR #24884 (October 2026):
when check_pkt() moves a decode timestamp, preserve the composition-time
offset rather than replacing the presentation timestamp with AV_NOPTS_VALUE.
No DASH/SIDX changes are required for PrismCore's frag_custom HLS output.
The complete patched FFmpeg source must accompany any distributed binaries.
"""
from __future__ import annotations

from pathlib import Path
import re

PATCH_NAME = "movenc-preserve-pts-on-dts-correction"
PATCH_SOURCE = "https://code.ffmpeg.org/FFmpeg/FFmpeg/pulls/24884"
_MARKER = "Preserve presentation offset when correcting decode timestamp"
_OLD = re.compile(
    r"^(?P<indent>[ \t]*)pkt->dts = ref \+ 1;\r?\n(?P=indent)pkt->pts = AV_NOPTS_VALUE;",
    re.MULTILINE,
)


def apply(source_tree: Path) -> None:
    path = source_tree / "libavformat" / "movenc.c"
    code = path.read_text()
    begin = code.find("static int check_pkt(")
    if begin < 0:
        raise RuntimeError("Unexpected movenc.c: check_pkt() not found")
    # Restrict the surgical edit to the check_pkt() implementation.
    # check_pkt() ends at the next column-zero closing brace; nearby FFmpeg
    # functions need not use the static keyword.
    scope_end = code.find("\n}\n", begin + 1)
    if scope_end < 0:
        raise RuntimeError("Unexpected movenc.c: check_pkt() end not found")
    scope_end += len("\n}\n")
    fragment = code[begin:scope_end]
    if _MARKER in fragment:
        return  # idempotent for local use
    matches = list(_OLD.finditer(fragment))
    if len(matches) != 1:
        raise RuntimeError(
            f"Unexpected FFmpeg movenc.c check_pkt() shape: {len(matches)} matches"
        )
    found = matches[0]
    indent = found.group("indent")
    replacement = (
        f"{indent}/* {_MARKER}. */\n"
        f"{indent}if (pkt->dts < ref && pkt->pts != AV_NOPTS_VALUE) {{\n"
        f"{indent}    pkt->pts += ref + 1 - pkt->dts;\n"
        f"{indent}}} else {{\n"
        f"{indent}    pkt->pts = AV_NOPTS_VALUE;\n"
        f"{indent}}}\n"
        f"{indent}pkt->dts = ref + 1;"
    )
    fragment = fragment[:found.start()] + replacement + fragment[found.end():]
    path.write_text(code[:begin] + fragment + code[scope_end:])
