"""Background QThread workers keeping the PySide6 GUI completely responsive."""

from __future__ import annotations

import threading
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from ..core.errors import CancelledError, DocuMakerError
from ..core.job_queue import VideoPipelineRunner
from ..core.models import Project
from ..core.project_manager import ProjectManager
from ..core.settings_manager import SettingsManager
from ..localization.manager import LocalizationManager
from ..media.tts_edge import EdgeTTSProvider


class PipelineWorker(QThread):
    step_started = Signal(int, str)
    step_completed = Signal(int)
    detail_updated = Signal(str)
    finished_project = Signal(object)
    cancelled_signal = Signal()
    failed_signal = Signal(int, str)

    def __init__(
        self,
        settings: SettingsManager,
        project_manager: ProjectManager,
        loc: LocalizationManager,
        project: Project,
        start_step: int = 1,
        stop_after_step: int = 9,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.project_manager = project_manager
        self.loc = loc
        self.project = project
        self.start_step = start_step
        self.stop_after_step = stop_after_step
        self.cancel_event = threading.Event()

    def request_cancel(self) -> None:
        self.cancel_event.set()

    def run(self) -> None:
        runner = VideoPipelineRunner(self.settings, self.project_manager, self.loc)
        try:
            proj = runner.run(
                project=self.project,
                start_step=self.start_step,
                stop_after_step=self.stop_after_step,
                cancel_event=self.cancel_event,
                on_step_started=lambda s, label: self.step_started.emit(s, label),
                on_step_completed=lambda s: self.step_completed.emit(s),
                on_detail=lambda msg: self.detail_updated.emit(msg),
            )
            self.finished_project.emit(proj)
        except CancelledError:
            self.cancelled_signal.emit()
        except DocuMakerError as exc:
            self.failed_signal.emit(exc.step or 1, exc.user_message(self.loc))
        except Exception:
            self.failed_signal.emit(1, self.loc.t("err.generic"))


class ProviderTestWorker(QThread):
    result_signal = Signal(str, bool, str)

    def __init__(self, provider_name: str, test_fn) -> None:
        super().__init__()
        self.provider_name = provider_name
        self.test_fn = test_fn

    def run(self) -> None:
        try:
            ok, msg = self.test_fn()
            self.result_signal.emit(self.provider_name, ok, msg)
        except Exception as exc:
            self.result_signal.emit(self.provider_name, False, str(exc))


class VoicePreviewWorker(QThread):
    finished_signal = Signal(str)
    error_signal = Signal(str)

    def __init__(
        self,
        text: str,
        output_path: Path,
        voice_id: str,
        rate: str,
        pitch: str,
        volume: str,
        loc: LocalizationManager,
    ) -> None:
        super().__init__()
        self.text = text
        self.output_path = output_path
        self.voice_id = voice_id
        self.rate = rate
        self.pitch = pitch
        self.volume = volume
        self.loc = loc

    def run(self) -> None:
        try:
            tts = EdgeTTSProvider()
            res = tts.synthesize(
                text=self.text,
                output_path=self.output_path,
                voice_id=self.voice_id,
                rate=self.rate,
                pitch=self.pitch,
                volume=self.volume,
            )
            self.finished_signal.emit(str(res.audio_path))
        except DocuMakerError as exc:
            self.error_signal.emit(exc.user_message(self.loc))
        except Exception:
            self.error_signal.emit(self.loc.t("err.generic"))
