#!/usr/bin/env python3
"""Repackage FFmpeg xcframework archives with deterministic Clang module exports.

Changes only framework HEADERS and module.modulemap, never Mach-O binaries.
Inputs from published GitHub release have SHA-256 values verified against
the source build manifest. The output files require their own checksums.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import tempfile
import zipfile

LIBRARIES = ("Libavcodec","Libavdevice","Libavfilter","Libavformat",
             "Libavutil","Libswresample","Libswscale")
PRIMARY = {
    "Libavutil": ("avutil","samplefmt","channel_layout","frame","buffer",
                  "dict","opt","imgutils","pixdesc","pixfmt","hwcontext",
                  "mathematics","rational","time","timestamp","error",
                  "mem","common","log","intreadwrite","avstring","display",
                  "mastering_display_metadata","hdr_dynamic_metadata",
                  "dovi_meta","stereo3d","audio_fifo","fifo","bprint"),
    "Libavcodec": ("avcodec","codec","codec_id","codec_par","packet","bsf",
                   "avfft","avdct","ac3_parser","vorbis_parser","dv_profile"),
    "Libavformat": ("avformat","avio","version"),
    "Libavfilter": ("avfilter","buffersink","buffersrc","version"),
    "Libavdevice": ("avdevice","version"),
    "Libswresample": ("swresample","version"),
    "Libswscale": ("swscale","version"),
}

def sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as fp:
        for chunk in iter(lambda:fp.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()

def repair_archive(source: Path, destination: Path, component: str) -> dict:
    source_prefix=component.lower()
    umbrella=f"{component}.h"
    patched=0
    processed=set()
    with zipfile.ZipFile(source,"r") as inp,zipfile.ZipFile(destination,"w") as out:
        entries=inp.infolist()
        for entry in entries:
            file=entry.filename
            data=inp.read(file)
            if file.endswith(f"/{component}.framework/Headers/{umbrella}"):
                hdr_path=file.rsplit("/Headers/",1)[0]+"/Headers/"
                available={Path(x.filename).name for x in entries if x.filename.startswith(hdr_path)}
                requested=list(dict.fromkeys(PRIMARY[component]))
                missing=[name for name in requested if name+".h" not in available]
                if missing: # optional/OS-specific headers differ between device and sim
                    requested=[name for name in requested if name+".h" in available]
                assert source_prefix+".h" in available
                data=("#pragma once\n"+
                      "".join(f'#include "{source_prefix}/{header}.h"\n' for header in requested)).encode()
                patched+=1
            elif file.endswith(f"/{component}.framework/Modules/module.modulemap"):
                headers_root=file.rsplit("/Modules/",1)[0]+"/Headers/"
                available=sorted({Path(x.filename).name for x in entries
                                  if x.filename.startswith(headers_root)
                                  and x.filename.endswith(".h") and
                                  x.filename.count("/") == headers_root.count("/")})
                # Explicitly list all other headers as textual, so Clang never
                # infers incomplete Libavutil.samplefmt-style submodules.
                # Imported API is defined by the platform-safe umbrella.
                textual="".join(f'    textual header "{h}"\n' for h in available if h!=umbrella)
                data=(f'framework module {component} {{\n'
                      f'    umbrella header "{umbrella}"\n'
                      f'{textual}'
                      '    export *\n'
                      '}\n').encode()
                patched+=1
            out.writestr(entry,data)
            processed.add(file)
    if patched != 4:
        raise RuntimeError(f"{component}: expected 2 umbrella + 2 module maps, got {patched}")
    return {"archive":source.name,"sha256":sha256(destination),"patched_entries":patched}

def main():
    a=argparse.ArgumentParser()
    a.add_argument("--source",type=Path,default=Path("dist"))
    a.add_argument("--out",type=Path,default=Path("repacked"))
    opt=a.parse_args()
    opt.out.mkdir(parents=True,exist_ok=True)
    original=json.loads((opt.source/"build-manifest.json").read_text())
    assert set(original["ffmpeg_libraries"]) == set(LIBRARIES)
    report={}
    for component in LIBRARIES:
        item=original["ffmpeg_libraries"][component]
        archive=opt.source/item["file"]
        assert sha256(archive)==item["sha256"],component
        output=opt.out/item["file"]
        report[component]=repair_archive(archive,output,component)
        print(component,report[component]["sha256"],flush=True)
    original["ffmpeg_libraries"]={k:{"file":v["archive"],"sha256":v["sha256"]}
                                  for k,v in report.items()}
    original["packaging_note"]="Umbrella and Clang modules repaired; Mach-O binaries not modified."
    (opt.out/"build-manifest.json").write_text(json.dumps(original,indent=2)+"\n")
    print("Module packaging repaired and checksums verified.")

if __name__=="__main__":
    main()
