"""Self-contained project folder & SQLite project library manager."""

from __future__ import annotations

import json
import re
import shutil
import sqlite3
import uuid
from datetime import datetime
from pathlib import Path

from .models import Project
from .settings_manager import SettingsManager


def slugify_title(title: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", title, flags=re.UNICODE).strip()
    cleaned = re.sub(r"[-\s]+", "-", cleaned)
    return cleaned[:48] or "documentary"


class ProjectManager:
    SUBFOLDERS = (
        "research",
        "script",
        "audio",
        "visuals",
        "music",
        "subtitles",
        "output",
        "logs",
        "tmp",
    )

    def __init__(self, settings: SettingsManager) -> None:
        self.settings = settings
        self.db_path = self.settings.app_dir / "projects.db"
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS projects (
                    project_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    folder_path TEXT NOT NULL,
                    language TEXT NOT NULL,
                    status TEXT NOT NULL,
                    total_duration_seconds REAL DEFAULT 0,
                    thumbnail_path TEXT DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.commit()

    def create_project(
        self,
        title: str,
        language: str = "ar",
        target_minutes: int = 3,
        extra_instructions: str = "",
        content_type: str = "documentary",
        audience: str = "general",
        tone: str = "calm",
        visual_mode: str = "stock",
        resolution: str = "720p",
    ) -> Project:
        project_id = uuid.uuid4().hex[:10]
        date_prefix = datetime.now().strftime("%Y-%m-%d")
        slug = slugify_title(title)
        base_dir = self.settings.get_projects_dir()
        folder = base_dir / f"{date_prefix}_{slug}_{project_id[:4]}"
        folder.mkdir(parents=True, exist_ok=True)
        for sub in self.SUBFOLDERS:
            (folder / sub).mkdir(exist_ok=True)

        proj = Project(
            project_id=project_id,
            title=title.strip(),
            folder_path=str(folder),
            language=language,
            target_minutes=target_minutes,
            extra_instructions=extra_instructions.strip(),
            content_type=content_type,
            audience=audience,
            tone=tone,
            visual_mode=visual_mode,
            resolution=resolution,
            burn_subtitles=self.settings.config.burn_subtitles,
            ken_burns_enabled=self.settings.config.ken_burns_enabled,
            ai_disclosure=self.settings.config.ai_disclosure_default,
        )
        self.save_project(proj)
        return proj

    def save_project(self, project: Project) -> None:
        project.updated_at = datetime.now().isoformat(timespec="seconds")
        folder = Path(project.folder_path)
        folder.mkdir(parents=True, exist_ok=True)
        for sub in self.SUBFOLDERS:
            (folder / sub).mkdir(exist_ok=True)

        (folder / "project.json").write_text(
            json.dumps(project.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        # Also write human-readable script & research artifacts for the user's folder
        if project.full_script_markdown:
            (folder / "script" / "script.md").write_text(project.full_script_markdown, encoding="utf-8")
        if project.research.summary or project.research.sources:
            (folder / "research" / "research.json").write_text(
                json.dumps(project.to_dict()["research"], ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            sources_lines = [
                f"- {s.get('title', 'Source')}: {s.get('url', '')}"
                for s in project.research.sources
            ]
            (folder / "research" / "sources.txt").write_text("\n".join(sources_lines), encoding="utf-8")

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO projects (
                    project_id, title, folder_path, language, status,
                    total_duration_seconds, thumbnail_path, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(project_id) DO UPDATE SET
                    title=excluded.title,
                    folder_path=excluded.folder_path,
                    language=excluded.language,
                    status=excluded.status,
                    total_duration_seconds=excluded.total_duration_seconds,
                    thumbnail_path=excluded.thumbnail_path,
                    updated_at=excluded.updated_at
                """,
                (
                    project.project_id,
                    project.title,
                    project.folder_path,
                    project.language,
                    project.status,
                    project.total_duration_seconds,
                    project.thumbnail_path,
                    project.created_at,
                    project.updated_at,
                ),
            )
            conn.commit()

    def load_project(self, project_id: str) -> Project | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT folder_path FROM projects WHERE project_id = ?", (project_id,)
            ).fetchone()
        if not row:
            return None
        json_path = Path(row[0]) / "project.json"
        if not json_path.exists():
            return None
        data = json.loads(json_path.read_text(encoding="utf-8"))
        return Project.from_dict(data)

    def list_projects(self) -> list[Project]:
        with sqlite3.connect(self.db_path) as conn:
            rows = conn.execute(
                "SELECT folder_path FROM projects ORDER BY updated_at DESC"
            ).fetchall()
        results: list[Project] = []
        for (folder_path,) in rows:
            json_path = Path(folder_path) / "project.json"
            if json_path.exists():
                try:
                    results.append(Project.from_dict(json.loads(json_path.read_text(encoding="utf-8"))))
                except Exception:
                    continue
        return results

    def delete_project(self, project_id: str) -> None:
        proj = self.load_project(project_id)
        if proj:
            shutil.rmtree(proj.folder_path, ignore_errors=True)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM projects WHERE project_id = ?", (project_id,))
            conn.commit()

    @staticmethod
    def estimate_required_mb(target_minutes: int, resolution: str) -> int:
        # Lightweight estimate: ~25 MB/min for 720p working assets + export; ~55 MB/min for 1080p
        per_min = 55 if resolution == "1080p" else 25
        return max(80, target_minutes * per_min)

    def get_free_space_gb(self) -> float:
        usage = shutil.disk_usage(self.settings.get_projects_dir())
        return usage.free / (1024 ** 3)
