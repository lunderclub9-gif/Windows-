"""Low-memory sequential scene renderer with Ken Burns motion for 4 GB RAM Windows PCs."""

from __future__ import annotations

import threading
from pathlib import Path

from ..core.errors import DocuMakerError
from ..core.models import Project, Scene
from .ffmpeg_utils import probe_duration, run_ffmpeg


class SceneRenderer:
    """Renders each scene individually to disk so whole videos are never loaded into memory."""

    @staticmethod
    def resolution_size(resolution: str) -> tuple[int, int]:
        if resolution == "1080p":
            return 1920, 1080
        return 1280, 720

    def render_scene(
        self,
        project: Project,
        scene: Scene,
        output_mp4: Path,
        cancel_event: threading.Event | None = None,
    ) -> Path:
        if not scene.selected_media or not scene.selected_media.local_path:
            raise DocuMakerError("err.no_visuals_found", f"Missing media for scene {scene.id}", step=8, scene=scene.id)

        media_path = Path(scene.selected_media.local_path)
        if not media_path.exists():
            raise DocuMakerError("err.no_visuals_found", f"File missing: {media_path}", step=8, scene=scene.id)

        w, h = self.resolution_size(project.resolution)
        fps = 30
        dur = scene.scene_duration
        frames = max(30, int(round(dur * fps)))
        output_mp4.parent.mkdir(parents=True, exist_ok=True)

        # Use FFmpeg's built-in MPEG-4 Part 2 encoder. It is included in LGPL
        # FFmpeg builds, unlike libx264 (which requires a GPL-enabled build).
        video_codec_args = ["-c:v", "mpeg4", "-q:v", "5", "-pix_fmt", "yuv420p"]

        if scene.selected_media.media_type == "video":
            clip_dur = probe_duration(media_path)
            loop_args = ["-stream_loop", "-1"] if (clip_dur <= 0 or clip_dur < dur) else []
            vf = (
                f"scale={w}:{h}:force_original_aspect_ratio=increase,"
                f"crop={w}:{h},fps={fps},format=yuv420p"
            )
            args = [
                *loop_args,
                "-i",
                str(media_path),
                "-t",
                f"{dur:.3f}",
                "-an",
                "-vf",
                vf,
                *video_codec_args,
                str(output_mp4),
            ]
        else:
            kb = scene.ken_burns if project.ken_burns_enabled else "none"
            if kb == "zoom_out":
                z_expr = f"if(eq(on,1),1.15,max(1.0,zoom-0.15/{frames}))"
                x_expr = "iw/2-(iw/zoom/2)"
                y_expr = "ih/2-(ih/zoom/2)"
            elif kb == "pan_right":
                z_expr = "1.12"
                x_expr = f"(iw-iw/zoom)*on/{frames}"
                y_expr = "ih/2-(ih/zoom/2)"
            elif kb == "pan_left":
                z_expr = "1.12"
                x_expr = f"(iw-iw/zoom)*(1-on/{frames})"
                y_expr = "ih/2-(ih/zoom/2)"
            elif kb == "none":
                z_expr = "1.0"
                x_expr = "0"
                y_expr = "0"
            else:
                z_expr = f"min(1.15,zoom+0.15/{frames})"
                x_expr = "iw/2-(iw/zoom/2)"
                y_expr = "ih/2-(ih/zoom/2)"

            vf = (
                f"scale={w * 2}:{h * 2}:force_original_aspect_ratio=increase,"
                f"crop={w * 2}:{h * 2},"
                f"zoompan=z='{z_expr}':x='{x_expr}':y='{y_expr}':d={frames}:s={w}x{h}:fps={fps},"
                "format=yuv420p"
            )
            args = [
                "-loop",
                "1",
                "-i",
                str(media_path),
                "-t",
                f"{dur:.3f}",
                "-an",
                "-vf",
                vf,
                *video_codec_args,
                str(output_mp4),
            ]

        run_ffmpeg(args, cancel_event=cancel_event, step=8)
        return output_mp4
