"""Per-scene audio loudness normalization via FFmpeg."""

from __future__ import annotations

import threading
from pathlib import Path

from .ffmpeg_utils import probe_duration, run_ffmpeg


class AudioNormalizer:
    """Normalizes narration clips to consistent -16 LUFS, 44.1 kHz stereo WAV."""

    def normalize(
        self,
        input_path: Path,
        output_wav_path: Path,
        cancel_event: threading.Event | None = None,
    ) -> float:
        output_wav_path.parent.mkdir(parents=True, exist_ok=True)
        run_ffmpeg(
            [
                "-i",
                str(input_path),
                "-af",
                "loudnorm=I=-16:TP=-1.5:LRA=11",
                "-ar",
                "44100",
                "-ac",
                "2",
                "-c:a",
                "pcm_s16le",
                str(output_wav_path),
            ],
            cancel_event=cancel_event,
            step=4,
        )
        return probe_duration(output_wav_path)
