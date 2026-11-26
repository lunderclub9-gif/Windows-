"""Silent FFmpeg/FFprobe discovery and subprocess execution (no console window on Windows)."""

from __future__ import annotations

import shutil
import subprocess
import sys
import threading
from pathlib import Path

from ..core.errors import CancelledError, DocuMakerError
from ..localization.manager import get_resource_path


def _subprocess_flags() -> int:
    if sys.platform == "win32":
        return 0x08000000  # subprocess.CREATE_NO_WINDOW
    return 0


def find_binary(name: str) -> str:
    exe_name = f"{name}.exe" if sys.platform == "win32" else name
    candidates = [
        get_resource_path(f"bin/{exe_name}"),
        Path.cwd() / "bin" / exe_name,
        Path(sys.executable).resolve().parent / "bin" / exe_name,
    ]
    for cand in candidates:
        if cand.exists() and cand.is_file():
            return str(cand)
    found = shutil.which(exe_name) or shutil.which(name)
    if found:
        return found
    raise DocuMakerError("err.ffmpeg_missing", f"Binary not found: {exe_name}")


def run_ffmpeg(
    args: list[str],
    cancel_event: threading.Event | None = None,
    step: int | None = None,
) -> None:
    ffmpeg_bin = find_binary("ffmpeg")
    cmd = [ffmpeg_bin, "-y", "-hide_banner", "-loglevel", "error", *args]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        creationflags=_subprocess_flags(),
    )
    try:
        while True:
            if cancel_event is not None and cancel_event.is_set():
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
                raise CancelledError(step=step)
            ret = proc.poll()
            if ret is not None:
                break
            threading.Event().wait(0.15)

        if proc.returncode != 0:
            err_out = (proc.stderr.read() if proc.stderr else b"").decode("utf-8", errors="replace")
            raise DocuMakerError("err.ffmpeg_failed", f"FFmpeg exited {proc.returncode}: {err_out}", step=step)
    finally:
        if proc.stdout:
            proc.stdout.close()
        if proc.stderr:
            proc.stderr.close()


def probe_duration(media_path: Path) -> float:
    ffprobe_bin = find_binary("ffprobe")
    cmd = [
        ffprobe_bin,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=noprint_wrappers=1:nokey=1",
        str(media_path),
    ]
    res = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        creationflags=_subprocess_flags(),
        check=False,
    )
    try:
        return max(0.0, float(res.stdout.strip()))
    except ValueError:
        return 0.0
