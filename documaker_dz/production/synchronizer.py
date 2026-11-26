"""Synchronization & storyboard timeline builder."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from ..core.models import Project


class AudioVideoSynchronizer:
    """Builds master storyboard.json where audio duration drives scene video timing."""

    def build_storyboard(self, project: Project) -> dict[str, Any]:
        cursor = 0.0
        timeline_scenes: list[dict[str, Any]] = []

        for scene in project.scenes:
            audio_dur = scene.actual_audio_duration or scene.estimated_duration_seconds
            padding = max(0.5, min(1.5, scene.padding_seconds))
            scene_dur = audio_dur + padding
            entry = {
                "scene_id": scene.id,
                "start_sec": round(cursor, 3),
                "audio_start_sec": round(cursor, 3),
                "audio_end_sec": round(cursor + audio_dur, 3),
                "end_sec": round(cursor + scene_dur, 3),
                "audio_duration": round(audio_dur, 3),
                "scene_duration": round(scene_dur, 3),
                "padding": round(padding, 3),
                "audio_path": scene.audio_path,
                "visual_path": scene.selected_media.local_path if scene.selected_media else "",
                "visual_type": scene.selected_media.media_type if scene.selected_media else "image",
                "ken_burns": scene.ken_burns if project.ken_burns_enabled else "none",
                "transition": scene.transition,
            }
            timeline_scenes.append(entry)
            cursor += scene_dur

        project.total_duration_seconds = round(cursor, 2)
        storyboard = {
            "project_id": project.project_id,
            "title": project.title,
            "language": project.language,
            "resolution": project.resolution,
            "total_duration_seconds": project.total_duration_seconds,
            "scenes": timeline_scenes,
        }

        sb_path = Path(project.folder_path) / "storyboard.json"
        sb_path.write_text(json.dumps(storyboard, ensure_ascii=False, indent=2), encoding="utf-8")
        return storyboard
