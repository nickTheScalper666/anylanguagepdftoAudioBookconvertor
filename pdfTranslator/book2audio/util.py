from __future__ import annotations
import shutil, subprocess
from typing import List, Optional

def have_cmd(name: str) -> bool:
    return shutil.which(name) is not None

def run_cmd(cmd: List[str], *, input_text: Optional[str] = None) -> None:
    try:
        subprocess.run(
            cmd,
            input=(input_text.encode("utf-8") if input_text is not None else None),
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as e:
        stderr = (e.stderr or b"").decode("utf-8", errors="replace")
        raise RuntimeError(f"Command failed: {' '.join(cmd)}\n\n{stderr}") from e
