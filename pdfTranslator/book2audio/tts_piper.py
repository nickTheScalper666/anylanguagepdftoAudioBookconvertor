from __future__ import annotations
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
import tempfile
import shutil
from .util import have_cmd, run_cmd

@dataclass(frozen=True)
class TtsOptions:
    voice_model: Path
    fmt: str = "m4b"
    bitrate: str = "128k"
    piper_binary: Optional[str] = None

def _piper_cmd(opts: TtsOptions) -> List[str]:
    if opts.piper_binary:
        return [opts.piper_binary]
    if have_cmd("piper"):
        return ["piper"]
    import sys
    return [sys.executable, "-m", "piper"]

def synthesize_wav(text: str, opts: TtsOptions, out_wav: Path) -> None:
    cmd = _piper_cmd(opts) + ["-m", str(opts.voice_model), "--output_file", str(out_wav)]
    run_cmd(cmd, input_text=text)

def concat_wavs(wavs: List[Path], out_wav: Path) -> None:
    if not have_cmd("ffmpeg"):
        raise RuntimeError("ffmpeg not found on PATH. Install with: brew install ffmpeg")
    with tempfile.TemporaryDirectory() as td:
        td = Path(td)
        lst = td / "list.txt"
        lst.write_text("\n".join([f"file '{w.as_posix()}'" for w in wavs]), encoding="utf-8")
        run_cmd(["ffmpeg","-y","-f","concat","-safe","0","-i",str(lst),"-c:a","pcm_s16le",str(out_wav)])

def encode_audio(in_wav: Path, out_path: Path, fmt: str, bitrate: str) -> None:
    if fmt == "wav":
        shutil.copyfile(in_wav, out_path)
        return
    if not have_cmd("ffmpeg"):
        raise RuntimeError("ffmpeg not found on PATH.")
    if fmt == "mp3":
        run_cmd(["ffmpeg","-y","-i",str(in_wav),"-b:a",bitrate,str(out_path)])
        return
    if fmt == "m4b":
        run_cmd(["ffmpeg","-y","-i",str(in_wav),"-c:a","aac","-b:a",bitrate,str(out_path)])
        return
    raise ValueError("Unsupported fmt (use mp3|m4b|wav)")
