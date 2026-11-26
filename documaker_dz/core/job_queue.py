"""Resumable 9-step documentary pipeline runner with cancellation and per-step persistence."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import Callable

from ..ai.creative_director import CreativeDirector
from ..ai.providers import build_ai_provider
from ..ai.research_agent import ResearchAgent
from ..ai.scene_planner import ScenePlanner
from ..ai.script_writer import ScriptWriter
from ..localization.manager import LocalizationManager
from ..media.pexels_provider import PexelsMediaProvider
from ..media.pixabay_provider import PixabayProvider, WikimediaSearchProvider
from ..media.tts_edge import EdgeTTSProvider
from ..media.tts_elevenlabs import ElevenLabsTTSProvider
from ..production.audio_normalizer import AudioNormalizer
from ..production.export_manager import ExportManager
from ..production.subtitle_generator import SubtitleGenerator
from ..production.synchronizer import AudioVideoSynchronizer
from .errors import CancelledError, DocuMakerError
from .logger import setup_logger
from .models import PipelineStep, Project, ProjectStatus
from .project_manager import ProjectManager
from .settings_manager import SettingsManager


class VideoPipelineRunner:
    """Executes steps 1..9 sequentially on a worker thread, preserving completed steps."""

    def __init__(
        self,
        settings: SettingsManager,
        project_manager: ProjectManager,
        loc: LocalizationManager,
    ) -> None:
        self.settings = settings
        self.project_manager = project_manager
        self.loc = loc

    def _check_cancel(self, cancel_event: threading.Event, step: int) -> None:
        if cancel_event.is_set():
            raise CancelledError(step=step)

    def _get_ai(self):
        provider_name = self.settings.config.active_ai_provider
        api_key = self.settings.get_api_key(provider_name)
        if not api_key:
            raise DocuMakerError("err.missing_ai_key", f"No API key for {provider_name}")
        model_map = {
            "gemini": self.settings.config.gemini_model,
            "openai": self.settings.config.openai_model,
            "groq": self.settings.config.groq_model,
            "openrouter": self.settings.config.openrouter_model,
        }
        return build_ai_provider(provider_name, api_key, model=model_map.get(provider_name))

    def _get_tts(self):
        if self.settings.config.active_tts_provider == "elevenlabs":
            key = self.settings.get_api_key("elevenlabs")
            if key:
                return ElevenLabsTTSProvider(key)
        return EdgeTTSProvider()

    def run(
        self,
        project: Project,
        start_step: int = 1,
        stop_after_step: int = 9,
        cancel_event: threading.Event | None = None,
        on_step_started: Callable[[int, str], None] | None = None,
        on_step_completed: Callable[[int], None] | None = None,
        on_detail: Callable[[str], None] | None = None,
    ) -> Project:
        cancel = cancel_event or threading.Event()
        logger: logging.Logger = setup_logger(
            f"documaker.proj.{project.project_id}",
            Path(project.folder_path) / "logs",
        )

        project.status = ProjectStatus.IN_PROGRESS.value
        project.failed_step = None
        project.last_error = ""
        self.project_manager.save_project(project)

        normalizer = AudioNormalizer()
        synchronizer = AudioVideoSynchronizer()
        sub_gen = SubtitleGenerator()
        exporter = ExportManager()

        current_step = start_step
        try:
            # Step 1: Research + Creative Plan
            if start_step <= PipelineStep.RESEARCH.value <= stop_after_step:
                current_step = PipelineStep.RESEARCH.value
                self._check_cancel(cancel, current_step)
                if on_step_started:
                    on_step_started(current_step, self.loc.t("step.1"))
                ai = self._get_ai()
                project.creative_plan = CreativeDirector().create_plan(ai, project)
                if project.voice_config.mode == "auto":
                    project.voice_config.voice_id = CreativeDirector.recommend_voice_id(
                        project.language, project.creative_plan.voice_gender
                    )
                project.research = ResearchAgent().run(ai, project)
                project.completed_step = max(project.completed_step, current_step)
                self.project_manager.save_project(project)
                if on_step_completed:
                    on_step_completed(current_step)

            # Step 2: Script Writing
            if start_step <= PipelineStep.SCRIPT.value <= stop_after_step:
                current_step = PipelineStep.SCRIPT.value
                self._check_cancel(cancel, current_step)
                if on_step_started:
                    on_step_started(current_step, self.loc.t("step.2"))
                ai = self._get_ai()
                script_res = ScriptWriter().run(ai, project)
                project.hook = script_res["hook"]
                project.full_script_markdown = script_res["full_script_markdown"]
                project.completed_step = max(project.completed_step, current_step)
                self.project_manager.save_project(project)
                if on_step_completed:
                    on_step_completed(current_step)

            # Step 3: Scene Planning
            if start_step <= PipelineStep.SCENES.value <= stop_after_step:
                current_step = PipelineStep.SCENES.value
                self._check_cancel(cancel, current_step)
                if on_step_started:
                    on_step_started(current_step, self.loc.t("step.3"))
                ai = self._get_ai()
                project.scenes = ScenePlanner().run(ai, project)
                project.completed_step = max(project.completed_step, current_step)
                self.project_manager.save_project(project)
                if on_step_completed:
                    on_step_completed(current_step)

            # Step 4: Per-scene Voice-Over Generation & Normalization
            if start_step <= PipelineStep.VOICE.value <= stop_after_step:
                current_step = PipelineStep.VOICE.value
                self._check_cancel(cancel, current_step)
                if on_step_started:
                    on_step_started(current_step, self.loc.t("step.4"))
                tts = self._get_tts()
                audio_dir = Path(project.folder_path) / "audio"
                for idx, scene in enumerate(project.scenes, start=1):
                    self._check_cancel(cancel, current_step)
                    if on_detail:
                        on_detail(f"TTS {idx}/{len(project.scenes)}")
                    raw_mp3 = audio_dir / f"scene_{scene.id:03d}_raw.mp3"
                    norm_wav = audio_dir / f"scene_{scene.id:03d}.wav"
                    try:
                        tts_res = tts.synthesize(
                            text=scene.narration,
                            output_path=raw_mp3,
                            voice_id=project.voice_config.voice_id,
                            rate=project.voice_config.rate,
                            pitch=project.voice_config.pitch,
                            volume=project.voice_config.volume,
                        )
                    except DocuMakerError as exc:
                        raise DocuMakerError(exc.loc_key, exc.technical_detail, step=current_step, scene=scene.id) from exc
                    dur = normalizer.normalize(raw_mp3, norm_wav, cancel_event=cancel)
                    scene.audio_path = str(norm_wav)
                    scene.actual_audio_duration = dur or tts_res.duration_seconds
                    scene.word_timings = tts_res.word_timings
                project.completed_step = max(project.completed_step, current_step)
                self.project_manager.save_project(project)
                if on_step_completed:
                    on_step_completed(current_step)

            # Step 5: Sequential Visual Asset Selection (Pexels + Pixabay/Wikimedia fallback)
            if start_step <= PipelineStep.VISUALS.value <= stop_after_step:
                current_step = PipelineStep.VISUALS.value
                self._check_cancel(cancel, current_step)
                if on_step_started:
                    on_step_started(current_step, self.loc.t("step.5"))
                pexels_key = self.settings.get_api_key("pexels")
                if not pexels_key:
                    raise DocuMakerError("err.missing_pexels_key", "Missing Pexels key", step=current_step)
                pexels = PexelsMediaProvider(pexels_key, cache_dir=self.settings.cache_dir)
                pixabay = PixabayProvider(self.settings.get_api_key("pixabay"))
                wiki = WikimediaSearchProvider()
                visuals_dir = Path(project.folder_path) / "visuals"

                for idx, scene in enumerate(project.scenes, start=1):
                    self._check_cancel(cancel, current_step)
                    if scene.selected_media and scene.selected_media.local_path and Path(scene.selected_media.local_path).exists():
                        continue
                    if on_detail:
                        on_detail(f"Visual {idx}/{len(project.scenes)}")
                    query = " ".join(scene.search_keywords[:3]) or scene.visual_prompt[:60] or project.title
                    candidates = []
                    # Fetch both videos and images sequentially to minimize RAM
                    candidates.extend(pexels.search_videos(query, per_page=2))
                    candidates.extend(pexels.search_images(query, per_page=3))
                    if not candidates and pixabay.api_key:
                        candidates.extend(pixabay.search_images(query, per_page=3))
                    if not candidates:
                        candidates.extend(wiki.search(query, limit=3))
                    if not candidates:
                        # Broader fallback query
                        candidates.extend(pexels.search_images("cinematic documentary landscape", per_page=2))
                    if not candidates:
                        raise DocuMakerError(
                            "err.no_visuals_found",
                            f"No stock media found for query '{query}'",
                            step=current_step,
                            scene=scene.id,
                        )
                    candidates.sort(key=lambda c: c.score, reverse=True)
                    scene.candidates = candidates[:4]
                    chosen = scene.candidates[0]
                    if chosen.provider == "pexels":
                        pexels.download_candidate(chosen, visuals_dir, f"scene_{scene.id:03d}")
                    elif chosen.provider == "wikimedia":
                        WikimediaSearchProvider.download_to(chosen, visuals_dir / f"scene_{scene.id:03d}.jpg")
                    else:
                        pexels.download_candidate(chosen, visuals_dir, f"scene_{scene.id:03d}")
                    scene.selected_media = chosen
                project.completed_step = max(project.completed_step, current_step)
                self.project_manager.save_project(project)
                if on_step_completed:
                    on_step_completed(current_step)

            # Step 6: Music Selection
            if start_step <= PipelineStep.MUSIC.value <= stop_after_step:
                current_step = PipelineStep.MUSIC.value
                self._check_cancel(cancel, current_step)
                if on_step_started:
                    on_step_started(current_step, self.loc.t("step.6"))
                if project.music_config.mode == "auto" and not project.music_config.track_path:
                    pixabay = PixabayProvider(self.settings.get_api_key("pixabay"))
                    tracks = pixabay.search_music("", mood=project.creative_plan.music_mood)
                    if tracks:
                        project.music_config.track_title = tracks[0]["title"]
                        project.music_config.license_name = tracks[0]["license"]
                project.completed_step = max(project.completed_step, current_step)
                self.project_manager.save_project(project)
                if on_step_completed:
                    on_step_completed(current_step)

            # Step 7: Subtitles Generation
            if start_step <= PipelineStep.SUBTITLES.value <= stop_after_step:
                current_step = PipelineStep.SUBTITLES.value
                self._check_cancel(cancel, current_step)
                if on_step_started:
                    on_step_started(current_step, self.loc.t("step.7"))
                synchronizer.build_storyboard(project)
                sub_gen.generate(project)
                project.completed_step = max(project.completed_step, current_step)
                self.project_manager.save_project(project)
                if on_step_completed:
                    on_step_completed(current_step)

            # Step 8 & 9: Assembly & Final MP4 Export
            if start_step <= PipelineStep.ASSEMBLY.value <= stop_after_step:
                current_step = PipelineStep.ASSEMBLY.value
                self._check_cancel(cancel, current_step)
                if on_step_started:
                    on_step_started(current_step, self.loc.t("step.8"))
                synchronizer.build_storyboard(project)
                project.completed_step = max(project.completed_step, current_step)
                self.project_manager.save_project(project)
                if on_step_completed:
                    on_step_completed(current_step)

            if start_step <= PipelineStep.EXPORT.value <= stop_after_step:
                current_step = PipelineStep.EXPORT.value
                self._check_cancel(cancel, current_step)
                if on_step_started:
                    on_step_started(current_step, self.loc.t("step.9"))
                exporter.export_project(project, progress_cb=on_detail, cancel_event=cancel)
                project.completed_step = max(project.completed_step, current_step)
                project.status = ProjectStatus.COMPLETED.value
                self.project_manager.save_project(project)
                if on_step_completed:
                    on_step_completed(current_step)
            elif stop_after_step < 9:
                project.status = ProjectStatus.DRAFT.value
                self.project_manager.save_project(project)

            return project

        except CancelledError:
            project.status = ProjectStatus.DRAFT.value
            project.failed_step = current_step
            project.last_error = self.loc.t("err.cancelled")
            self.project_manager.save_project(project)
            raise
        except DocuMakerError as exc:
            logger.exception("Pipeline error at step %s: %s", current_step, exc.technical_detail)
            project.status = ProjectStatus.FAILED.value
            project.failed_step = exc.step or current_step
            project.last_error = exc.user_message(self.loc)
            self.project_manager.save_project(project)
            raise DocuMakerError(
                exc.loc_key,
                exc.technical_detail,
                step=project.failed_step,
                **exc.format_args,
            ) from exc
        except Exception as exc:
            logger.exception("Unexpected pipeline failure at step %s", current_step)
            project.status = ProjectStatus.FAILED.value
            project.failed_step = current_step
            project.last_error = self.loc.t("err.generic")
            self.project_manager.save_project(project)
            raise DocuMakerError("err.generic", str(exc), step=current_step) from exc
