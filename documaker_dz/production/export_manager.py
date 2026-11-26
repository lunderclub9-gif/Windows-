"""Final MP4 Export Manager: concatenates scenes, muxes ducked audio, burns/attaches subtitles, cleans tmp."""

from __future__ import annotations

import shutil
import threading
from pathlib import Path

from ..ai.quality_reviewer import QualityReviewer
from ..core.errors import DocuMakerError
from ..core.models import Project
from ..core.project_manager import ProjectManager
from .ffmpeg_utils import run_ffmpeg
from .music_mixer import MusicMixer
from .scene_renderer import SceneRenderer


class ExportManager:
    def __init__(self) -> None:
        self.reviewer = QualityReviewer()
        self.scene_renderer = SceneRenderer()
        self.music_mixer = MusicMixer()

    def export_project(
        self,
        project: Project,
        progress_cb=None,
        cancel_event: threading.Event | None = None,
    ) -> Path:
        self.reviewer.review_before_export(project)

        req_mb = ProjectManager.estimate_required_mb(project.target_minutes, project.resolution)
        free_mb = shutil.disk_usage(project.folder_path).free / (1024 * 1024)
        if free_mb < req_mb * 0.5:
            raise DocuMakerError(
                "err.insufficient_space",
                f"Free {free_mb:.0f} MB < required {req_mb} MB",
                step=9,
                req=req_mb,
            )

        proj_dir = Path(project.folder_path)
        tmp_dir = proj_dir / "tmp"
        out_dir = proj_dir / "output"
        tmp_dir.mkdir(parents=True, exist_ok=True)
        out_dir.mkdir(parents=True, exist_ok=True)

        scene_clips: list[Path] = []
        total_scenes = len(project.scenes)
        for idx, scene in enumerate(project.scenes, start=1):
            if progress_cb:
                progress_cb(f"{idx}/{total_scenes}")
            clip_path = tmp_dir / f"scene_{scene.id:03d}.mp4"
            self.scene_renderer.render_scene(project, scene, clip_path, cancel_event=cancel_event)
            scene_clips.append(clip_path)

        concat_list = tmp_dir / "video_concat.txt"
        concat_list.write_text(
            "\n".join(f"file '{c.resolve().as_posix()}'" for c in scene_clips),
            encoding="utf-8",
        )
        merged_video = tmp_dir / "merged_video.mp4"
        run_ffmpeg(
            ["-f", "concat", "-safe", "0", "-i", str(concat_list), "-c", "copy", str(merged_video)],
            cancel_event=cancel_event,
            step=9,
        )

        voice_wav = tmp_dir / "narration_full.wav"
        self.music_mixer.build_narration_track(project, voice_wav, cancel_event=cancel_event)
        mixed_aac = tmp_dir / "audio_mix.aac"
        self.music_mixer.mix_final_audio(project, voice_wav, mixed_aac, cancel_event=cancel_event)

        final_mp4 = out_dir / "final_video.mp4"
        ass_path = Path(project.subtitle_ass_path) if project.subtitle_ass_path else None
        if project.burn_subtitles and ass_path and ass_path.exists():
            escaped = ass_path.resolve().as_posix().replace(":", "\\:")
            run_ffmpeg(
                [
                    "-i",
                    str(merged_video),
                    "-i",
                    str(mixed_aac),
                    "-vf",
                    f"ass='{escaped}'",
                    "-c:v",
                    "mpeg4",
                    "-q:v",
                    "5",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "copy",
                    "-shortest",
                    "-movflags",
                    "+faststart",
                    str(final_mp4),
                ],
                cancel_event=cancel_event,
                step=9,
            )
        else:
            run_ffmpeg(
                [
                    "-i",
                    str(merged_video),
                    "-i",
                    str(mixed_aac),
                    "-c:v",
                    "copy",
                    "-c:a",
                    "copy",
                    "-shortest",
                    "-movflags",
                    "+faststart",
                    str(final_mp4),
                ],
                cancel_event=cancel_event,
                step=9,
            )

        thumb_path = out_dir / "thumbnail.jpg"
        try:
            run_ffmpeg(
                ["-ss", "2", "-i", str(final_mp4), "-vframes", "1", "-q:v", "3", str(thumb_path)],
                cancel_event=cancel_event,
                step=9,
            )
            if thumb_path.exists():
                project.thumbnail_path = str(thumb_path)
        except DocuMakerError:
            pass

        shutil.rmtree(tmp_dir, ignore_errors=True)
        tmp_dir.mkdir(exist_ok=True)

        project.output_video_path = str(final_mp4)
        return final_mp4
