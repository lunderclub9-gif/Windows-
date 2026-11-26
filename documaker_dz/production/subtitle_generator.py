"""Subtitle generator (.srt and styled .ass with Arabic RTL support) driven by actual audio timing."""

from __future__ import annotations

import re
from pathlib import Path

from ..core.models import Project, Scene


def _fmt_srt_time(seconds: float) -> str:
    ms_total = max(0, int(round(seconds * 1000)))
    hours, rem = divmod(ms_total, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def _fmt_ass_time(seconds: float) -> str:
    cs_total = max(0, int(round(seconds * 100)))
    hours, rem = divmod(cs_total, 360_000)
    minutes, rem = divmod(rem, 6000)
    secs, cs = divmod(rem, 100)
    return f"{hours:d}:{minutes:02d}:{secs:02d}.{cs:02d}"


def _split_caption_chunks(text: str, max_words: int = 10) -> list[str]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!؟،,;:])\s+", text.strip()) if s.strip()]
    chunks: list[str] = []
    for sent in sentences:
        words = sent.split()
        if len(words) <= max_words:
            chunks.append(sent)
        else:
            for i in range(0, len(words), max_words):
                chunks.append(" ".join(words[i : i + max_words]))
    return chunks or [text.strip()]


class SubtitleGenerator:
    """Generates accurate SRT and ASS subtitles anchored to each scene's real narration audio."""

    def _scene_cues(self, scene: Scene, scene_start: float) -> list[tuple[float, float, str]]:
        audio_dur = max(1.0, scene.actual_audio_duration or scene.estimated_duration_seconds)
        chunks = _split_caption_chunks(scene.narration, max_words=9)
        if not chunks:
            return []
        total_chars = sum(max(1, len(c)) for c in chunks)
        cues: list[tuple[float, float, str]] = []
        t = scene_start
        for chunk in chunks:
            share = audio_dur * (max(1, len(chunk)) / total_chars)
            end = min(scene_start + audio_dur, t + share)
            if end - t >= 0.2:
                cues.append((t, end, chunk))
            t = end
        return cues

    def generate(self, project: Project) -> tuple[Path, Path]:
        sub_dir = Path(project.folder_path) / "subtitles"
        sub_dir.mkdir(parents=True, exist_ok=True)
        srt_path = sub_dir / "subtitles.srt"
        ass_path = sub_dir / "subtitles.ass"

        all_cues: list[tuple[float, float, str]] = []
        cursor = 0.0
        for scene in project.scenes:
            all_cues.extend(self._scene_cues(scene, cursor))
            cursor += scene.scene_duration

        # Write SRT
        srt_lines: list[str] = []
        for idx, (start, end, text) in enumerate(all_cues, start=1):
            srt_lines.append(f"{idx}")
            srt_lines.append(f"{_fmt_srt_time(start)} --> {_fmt_srt_time(end)}")
            srt_lines.append(text)
            srt_lines.append("")
        srt_path.write_text("\n".join(srt_lines), encoding="utf-8")

        # Write ASS with clean Arabic/Latin font styling & semi-transparent dark backdrop
        font_name = "Tahoma" if project.language == "ar" else "Arial"
        font_size = 24 if project.resolution == "720p" else 34
        ass_header = (
            "[Script Info]\n"
            "ScriptType: v4.00+\n"
            f"Title: {project.title}\n"
            f"PlayResX: {1280 if project.resolution == '720p' else 1920}\n"
            f"PlayResY: {720 if project.resolution == '720p' else 1080}\n"
            "WrapStyle: 0\n\n"
            "[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, "
            "BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, "
            "BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,&H0010141C,&H99000000,"
            "1,0,0,0,100,100,0,0,3,2,0,2,48,48,34,1\n\n"
            "[Events]\n"
            "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
        )
        ass_events: list[str] = []
        for start, end, text in all_cues:
            safe_txt = text.replace("\n", "\\N")
            if project.language == "ar":
                # Unicode Right-to-Left Embedding for proper Arabic punctuation placement in ASS
                safe_txt = f"\u202B{safe_txt}\u202C"
            ass_events.append(
                f"Dialogue: 0,{_fmt_ass_time(start)},{_fmt_ass_time(end)},Default,,0,0,0,,{safe_txt}"
            )
        ass_path.write_text(ass_header + "\n".join(ass_events) + "\n", encoding="utf-8")

        project.subtitle_srt_path = str(srt_path)
        project.subtitle_ass_path = str(ass_path)
        return srt_path, ass_path
