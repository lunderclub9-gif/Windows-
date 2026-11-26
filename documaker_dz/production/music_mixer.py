"""Music mixer with looping, fade-in/out, ambient fallback synthesis, and narration ducking."""

from __future__ import annotations

import threading
from pathlib import Path

from ..core.models import Project
from .ffmpeg_utils import run_ffmpeg


class MusicMixer:
    """Combines per-scene narration clips into a synchronized voice track and mixes background music."""

    def build_narration_track(
        self,
        project: Project,
        output_voice_wav: Path,
        cancel_event: threading.Event | None = None,
    ) -> Path:
        tmp_dir = Path(project.folder_path) / "tmp"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        padded_clips: list[Path] = []

        for scene in project.scenes:
            padded_wav = tmp_dir / f"voice_padded_{scene.id:03d}.wav"
            pad_sec = max(0.5, min(1.5, scene.padding_seconds))
            if scene.audio_path and Path(scene.audio_path).exists():
                run_ffmpeg(
                    [
                        "-i",
                        scene.audio_path,
                        "-af",
                        f"apad=pad_dur={pad_sec:.3f}",
                        "-ar",
                        "44100",
                        "-ac",
                        "2",
                        "-c:a",
                        "pcm_s16le",
                        str(padded_wav),
                    ],
                    cancel_event=cancel_event,
                    step=8,
                )
            else:
                dur = scene.scene_duration
                run_ffmpeg(
                    [
                        "-f",
                        "lavfi",
                        "-i",
                        "anullsrc=r=44100:cl=stereo",
                        "-t",
                        f"{dur:.3f}",
                        "-c:a",
                        "pcm_s16le",
                        str(padded_wav),
                    ],
                    cancel_event=cancel_event,
                    step=8,
                )
            padded_clips.append(padded_wav)

        concat_txt = tmp_dir / "voice_concat.txt"
        concat_txt.write_text(
            "\n".join(f"file '{p.resolve().as_posix()}'" for p in padded_clips),
            encoding="utf-8",
        )
        run_ffmpeg(
            [
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(concat_txt),
                "-c:a",
                "pcm_s16le",
                str(output_voice_wav),
            ],
            cancel_event=cancel_event,
            step=8,
        )
        return output_voice_wav

    def generate_ambient_pad(
        self,
        output_wav: Path,
        duration_seconds: float,
        mood: str = "calm",
        cancel_event: threading.Event | None = None,
    ) -> Path:
        """Generates a gentle, royalty-free warm ambient documentary pad when no external track is provided."""
        output_wav.parent.mkdir(parents=True, exist_ok=True)
        # Warm soft harmonic chord frequencies (A2=110, E3=164.81, B3=246.94) filtered gently
        expr = "0.08*sin(2*PI*110*t)+0.06*sin(2*PI*164.81*t)+0.04*sin(2*PI*220*t)"
        if mood == "mysterious":
            expr = "0.08*sin(2*PI*98*t)+0.06*sin(2*PI*146.83*t)+0.04*sin(2*PI*174.61*t)"
        run_ffmpeg(
            [
                "-f",
                "lavfi",
                "-i",
                f"aevalsrc={expr}:s=44100:d={max(5.0, duration_seconds):.2f}",
                "-af",
                "lowpass=f=480,aecho=0.8:0.88:60:0.4",
                "-ac",
                "2",
                "-c:a",
                "pcm_s16le",
                str(output_wav),
            ],
            cancel_event=cancel_event,
            step=6,
        )
        return output_wav

    def mix_final_audio(
        self,
        project: Project,
        voice_wav: Path,
        output_mix_aac: Path,
        cancel_event: threading.Event | None = None,
    ) -> Path:
        total_dur = max(3.0, project.total_duration_seconds)
        music_cfg = project.music_config
        music_path = Path(music_cfg.track_path) if music_cfg.track_path else None

        if not music_path or not music_path.exists():
            fallback_music = Path(project.folder_path) / "music" / "ambient_pad.wav"
            self.generate_ambient_pad(
                fallback_music,
                duration_seconds=total_dur,
                mood=project.creative_plan.music_mood,
                cancel_event=cancel_event,
            )
            music_path = fallback_music
            music_cfg.track_path = str(fallback_music)
            if not music_cfg.track_title:
                music_cfg.track_title = "Built-in Documentary Ambient Pad"
                music_cfg.license_name = "CC0 / Local Synthesis"

        fade_in = max(0.5, music_cfg.fade_in_seconds)
        fade_out = max(0.5, music_cfg.fade_out_seconds)
        fade_out_start = max(0.0, total_dur - fade_out)
        vol = max(0.02, min(1.0, music_cfg.volume))

        fmt = "aformat=sample_fmts=fltp:sample_rates=44100:channel_layouts=stereo"
        music_chain = (
            f"[1:a]aloop=loop=-1:size=2e+09,atrim=0:{total_dur:.3f},"
            f"asetpts=PTS-STARTPTS,{fmt},volume={vol:.3f},"
            f"afade=t=in:st=0:d={fade_in:.2f},"
            f"afade=t=out:st={fade_out_start:.2f}:d={fade_out:.2f}[bg]"
        )

        if music_cfg.ducking_enabled:
            filter_complex = (
                f"{music_chain};"
                f"[0:a]{fmt},asplit=2[voice_main][voice_sc];"
                "[bg][voice_sc]sidechaincompress=threshold=0.02:ratio=6:attack=120:release=600[ducked_bg];"
                "[voice_main][ducked_bg]amix=inputs=2:duration=first:dropout_transition=2[outa]"
            )
        else:
            filter_complex = (
                f"{music_chain};"
                f"[0:a]{fmt}[voice_main];"
                "[voice_main][bg]amix=inputs=2:duration=first:dropout_transition=2[outa]"
            )

        output_mix_aac.parent.mkdir(parents=True, exist_ok=True)
        run_ffmpeg(
            [
                "-i",
                str(voice_wav),
                "-i",
                str(music_path),
                "-filter_complex",
                filter_complex,
                "-map",
                "[outa]",
                "-c:a",
                "aac",
                "-b:a",
                "192k",
                str(output_mix_aac),
            ],
            cancel_event=cancel_event,
            step=8,
        )
        return output_mix_aac
