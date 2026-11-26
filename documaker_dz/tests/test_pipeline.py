"""End-to-end automated tests for DocuMaker DZ core, security, sync, subtitles, and FFmpeg pipeline."""

from __future__ import annotations

import shutil
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from documaker_dz.ai.base import AIProvider
from documaker_dz.ai.quality_reviewer import QualityReviewer
from documaker_dz.core.errors import CancelledError, DocuMakerError
from documaker_dz.core.job_queue import VideoPipelineRunner
from documaker_dz.core.models import MediaCandidate, ProjectStatus, Scene
from documaker_dz.core.project_manager import ProjectManager
from documaker_dz.core.security import SecretVault
from documaker_dz.core.settings_manager import SettingsManager
from documaker_dz.localization.manager import LocalizationManager
from documaker_dz.media.base import TTSResult
from documaker_dz.production.export_manager import ExportManager
from documaker_dz.production.ffmpeg_utils import probe_duration, run_ffmpeg
from documaker_dz.production.subtitle_generator import SubtitleGenerator
from documaker_dz.production.synchronizer import AudioVideoSynchronizer


class StubAIProvider(AIProvider):
    name = "gemini"
    display_name = "Stub Gemini"
    supports_free_tier = True

    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.5) -> str:
        return "OK"

    def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.3):
        if "Creative Director" in system_prompt:
            return {
                "language": "ar",
                "voice_gender": "male",
                "voice_style": "deep_documentary",
                "voice_pace": "slow",
                "voice_emotion": "calm",
                "music_style": "calm_historical",
                "music_mood": "calm",
                "music_energy": "low",
                "instrumentation": ["oud", "strings"],
                "visual_style": "historical_documentary",
                "color_grade": "warm_earthy",
                "pacing": "slow",
                "target_duration_seconds": 180,
            }
        if "fact-researcher" in system_prompt:
            return {
                "summary": "بجاية مدينة تاريخية عريقة على ساحل البحر المتوسط.",
                "key_facts": ["تأسست في العهد الحمادي سنة 1067م."],
                "timeline": ["1067م: بناء الناصرية (بجاية)"],
                "entities": ["بجاية", "الناصر بن علناس"],
                "sources": [{"title": "UNESCO World Heritage", "url": "https://whc.unesco.org"}],
                "warnings": [],
                "sensitive_topics": [],
            }
        if "scriptwriter" in system_prompt:
            return {
                "hook": "على ضفاف المتوسط، تقف مدينة بجاية شاهدة على قرون من العلم.",
                "full_script_markdown": "### المقدمة\nعلى ضفاف المتوسط، تقف مدينة بجاية شاهدة على قرون من العلم.",
            }
        return {
            "scenes": [
                {
                    "id": 1,
                    "title": "مقدمة",
                    "narration": "على ضفاف المتوسط، تقف مدينة بجاية شاهدة على قرون من العلم.",
                    "visual_prompt": "Mediterranean coast historical city",
                    "search_keywords": ["mediterranean coast", "ancient city"],
                    "estimated_duration_seconds": 3,
                    "music_mood": "calm",
                    "transition": "slow_fade",
                }
            ]
        }

    def test_connection(self) -> tuple[bool, str]:
        return True, "OK"


class DocuMakerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp_root = Path(tempfile.mkdtemp(prefix="documaker_test_"))
        self.settings = SettingsManager(app_dir=self.tmp_root / "appdata")
        self.pm = ProjectManager(self.settings)

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp_root, ignore_errors=True)

    def test_localization_arabic_default_rtl(self) -> None:
        loc = LocalizationManager("ar")
        self.assertTrue(loc.is_rtl)
        self.assertIn("إنشاء", loc.t("home.btn_create"))
        loc.set_language("fr")
        self.assertFalse(loc.is_rtl)
        loc.set_language("en")
        self.assertEqual(loc.t("home.btn_create"), "Create Video")

    def test_secret_vault_encryption(self) -> None:
        vault = SecretVault(self.tmp_root / "api_keys.enc")
        vault.save_keys({"gemini": "AIzaSecretTestKey123", "pexels": "PexelsSecret456"})
        raw_file = (self.tmp_root / "api_keys.enc").read_text(encoding="utf-8")
        self.assertNotIn("AIzaSecretTestKey123", raw_file)
        self.assertNotIn("PexelsSecret456", raw_file)
        loaded = vault.load_keys()
        self.assertEqual(loaded["gemini"], "AIzaSecretTestKey123")
        self.assertEqual(loaded["pexels"], "PexelsSecret456")

    def test_project_crud_and_ffmpeg_export_with_burned_subtitles(self) -> None:
        proj = self.pm.create_project(
            title="تاريخ مدينة بجاية",
            language="ar",
            target_minutes=3,
            resolution="720p",
        )
        self.assertTrue(Path(proj.folder_path).exists())
        self.assertIsNotNone(self.pm.load_project(proj.project_id))

        vis_img = Path(proj.folder_path) / "visuals" / "scene_001.png"
        aud_wav = Path(proj.folder_path) / "audio" / "scene_001.wav"
        run_ffmpeg(["-f", "lavfi", "-i", "color=c=0x1e293b:s=1280x720:d=1", "-frames:v", "1", str(vis_img)])
        run_ffmpeg(["-f", "lavfi", "-i", "sine=frequency=440:duration=2.0", "-ar", "44100", "-ac", "2", str(aud_wav)])

        dur = probe_duration(aud_wav)
        self.assertGreater(dur, 1.8)

        scene = Scene(
            id=1,
            title="مقدمة بجاية",
            narration="تقع مدينة بجاية على ساحل البحر المتوسط في الجزائر.",
            visual_prompt="Aerial view of Bejaia coast",
            search_keywords=["mediterranean coast", "ancient city"],
            actual_audio_duration=dur,
            padding_seconds=0.8,
            ken_burns="zoom_in",
            audio_path=str(aud_wav),
            selected_media=MediaCandidate(
                provider="pexels",
                media_type="image",
                media_id="test1",
                url="https://pexels.com",
                download_url="https://pexels.com",
                license_name="Pexels License",
                attribution="Test Photographer",
                local_path=str(vis_img),
            ),
        )
        proj.scenes = [scene]
        proj.burn_subtitles = True

        AudioVideoSynchronizer().build_storyboard(proj)
        srt_path, ass_path = SubtitleGenerator().generate(proj)
        self.assertTrue(srt_path.exists())
        self.assertTrue(ass_path.exists())
        self.assertIn("تقع مدينة بجاية", srt_path.read_text(encoding="utf-8"))

        out_mp4 = ExportManager().export_project(proj)
        self.assertTrue(out_mp4.exists())
        self.assertGreater(out_mp4.stat().st_size, 5000)
        self.assertGreater(probe_duration(out_mp4), 2.3)

    def test_resumable_pipeline_runner_and_cancellation(self) -> None:
        self.settings.set_api_key("gemini", "stub-key")
        self.settings.set_api_key("pexels", "stub-pexels")
        loc = LocalizationManager("ar")
        proj = self.pm.create_project(title="تاريخ مدينة بجاية", language="ar", target_minutes=3)
        runner = VideoPipelineRunner(self.settings, self.pm, loc)

        def fake_tts(text, output_path: Path, **kwargs):
            run_ffmpeg(["-f", "lavfi", "-i", "sine=frequency=520:duration=1.5", "-ar", "44100", "-ac", "2", str(output_path)])
            return TTSResult(audio_path=output_path, duration_seconds=1.5, word_timings=[])

        def fake_pexels_dl(self_p, candidate: MediaCandidate, dest_dir: Path, filename_prefix: str):
            p = dest_dir / f"{filename_prefix}.png"
            run_ffmpeg(["-f", "lavfi", "-i", "color=c=0x0f172a:s=1280x720:d=1", "-frames:v", "1", str(p)])
            candidate.local_path = str(p)
            candidate.media_type = "image"
            return p

        fake_cand = MediaCandidate(
            provider="pexels",
            media_type="image",
            media_id="99",
            url="https://pexels.com/99",
            download_url="https://pexels.com/99.jpg",
            license_name="Pexels License",
            attribution="Pexels",
        )

        with (
            patch("documaker_dz.core.job_queue.build_ai_provider", return_value=StubAIProvider()),
            patch("documaker_dz.media.tts_edge.EdgeTTSProvider.synthesize", side_effect=fake_tts),
            patch("documaker_dz.media.pexels_provider.PexelsMediaProvider.search_videos", return_value=[]),
            patch("documaker_dz.media.pexels_provider.PexelsMediaProvider.search_images", return_value=[fake_cand]),
            patch("documaker_dz.media.pexels_provider.PexelsMediaProvider.download_candidate", autospec=True, side_effect=fake_pexels_dl),
        ):
            # Phase A: Run steps 1..3 for script review
            proj = runner.run(proj, start_step=1, stop_after_step=3)
            self.assertEqual(proj.completed_step, 3)
            self.assertEqual(len(proj.scenes), 1)

            # Phase B: Resume from step 4..9
            proj = runner.run(proj, start_step=4, stop_after_step=9)
            self.assertEqual(proj.completed_step, 9)
            self.assertEqual(proj.status, ProjectStatus.COMPLETED.value)
            self.assertTrue(Path(proj.output_video_path).exists())

            # Verify cancellation raises CancelledError cleanly
            ev = threading.Event()
            ev.set()
            with self.assertRaises(CancelledError):
                runner.run(proj, start_step=1, stop_after_step=9, cancel_event=ev)

    def test_unknown_license_blocked(self) -> None:
        proj = self.pm.create_project(title="Test License Guard", language="en")
        proj.scenes = [
            Scene(
                id=1,
                narration="Test",
                selected_media=MediaCandidate(
                    provider="unknown",
                    media_type="image",
                    media_id="x",
                    url="",
                    download_url="",
                    license_name="unknown",
                    local_path="/tmp/fake.jpg",
                ),
            )
        ]
        with self.assertRaises(DocuMakerError) as ctx:
            QualityReviewer().review_before_export(proj)
        self.assertEqual(ctx.exception.loc_key, "err.unknown_license")


if __name__ == "__main__":
    unittest.main()
