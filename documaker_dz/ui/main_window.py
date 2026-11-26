"""Main PySide6 desktop window for DocuMaker DZ (Arabic-first RTL)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSlider,
    QSpinBox,
    QStackedWidget,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from ..ai.providers import build_ai_provider
from ..ai.scene_planner import ScenePlanner
from ..core.errors import DocuMakerError
from ..core.models import MediaCandidate, Project
from ..core.project_manager import ProjectManager
from ..core.settings_manager import SettingsManager
from ..localization.manager import LocalizationManager, get_resource_path
from ..media.pexels_provider import PexelsMediaProvider
from ..media.pixabay_provider import PixabayProvider
from ..media.tts_edge import EdgeTTSProvider
from ..media.tts_elevenlabs import ElevenLabsTTSProvider
from .theme import APP_QSS
from .widgets import ProjectCard, ProviderSettingsCard, SceneEditorWidget, StepProgressRow
from .workers import PipelineWorker, ProviderTestWorker, VoicePreviewWorker


def _open_folder_silently(folder_path: str) -> None:
    path = Path(folder_path)
    if not path.exists():
        return
    if sys.platform == "win32":
        os.startfile(str(path))  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.Popen(["open", str(path)])
    else:
        subprocess.Popen(["xdg-open", str(path)])


class MainWindow(QMainWindow):
    def __init__(
        self,
        settings: SettingsManager,
        project_manager: ProjectManager,
        loc: LocalizationManager,
    ) -> None:
        super().__init__()
        self.settings = settings
        self.project_manager = project_manager
        self.loc = loc

        self.current_project: Project | None = None
        self.worker: PipelineWorker | None = None
        self.test_worker: ProviderTestWorker | None = None
        self.preview_worker: VoicePreviewWorker | None = None
        self.step_rows: dict[int, StepProgressRow] = {}
        self.provider_cards: dict[str, ProviderSettingsCard] = {}
        self.ai_model_combos: dict[str, QComboBox] = {}
        self.scene_editors: list[SceneEditorWidget] = []
        self.nav_buttons: list[QPushButton] = []

        self._apply_window_chrome()
        self._build_ui()
        self._refresh_storage_banner()
        self._refresh_library()

    def _apply_window_chrome(self) -> None:
        self.setWindowTitle(self.loc.t("app.title"))
        self.resize(1200, 780)
        self.setMinimumSize(980, 660)
        icon_ico = get_resource_path("assets/icon.ico")
        icon_png = get_resource_path("assets/icon.png")
        if icon_ico.exists():
            self.setWindowIcon(QIcon(str(icon_ico)))
        elif icon_png.exists():
            self.setWindowIcon(QIcon(str(icon_png)))
        self.setLayoutDirection(Qt.RightToLeft if self.loc.is_rtl else Qt.LeftToRight)
        self.setStyleSheet(APP_QSS)

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QHBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Sidebar
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(235)
        sb_layout = QVBoxLayout(sidebar)
        sb_layout.setContentsMargins(14, 18, 14, 18)
        sb_layout.setSpacing(6)

        brand_title = QLabel("DocuMaker DZ")
        brand_title.setObjectName("BrandTitle")
        brand_sub = QLabel(self.loc.t("app.subtitle"))
        brand_sub.setObjectName("BrandSub")
        brand_sub.setWordWrap(True)
        sb_layout.addWidget(brand_title)
        sb_layout.addWidget(brand_sub)
        sb_layout.addSpacing(14)

        nav_keys = [
            "nav.home",
            "nav.library",
            "nav.script",
            "nav.voice",
            "nav.music",
            "nav.visuals",
            "nav.settings",
        ]
        self.nav_buttons.clear()
        for idx, key in enumerate(nav_keys):
            btn = QPushButton(self.loc.t(key))
            btn.setObjectName("NavBtn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda _=False, i=idx: self._switch_page(i))
            sb_layout.addWidget(btn)
            self.nav_buttons.append(btn)

        sb_layout.addStretch()
        root.addWidget(sidebar)

        # Main stacked pages
        self.stack = QStackedWidget()
        root.addWidget(self.stack, 1)

        self.stack.addWidget(self._build_home_page())
        self.stack.addWidget(self._build_library_page())
        self.stack.addWidget(self._build_script_page())
        self.stack.addWidget(self._build_voice_page())
        self.stack.addWidget(self._build_music_page())
        self.stack.addWidget(self._build_visuals_page())
        self.stack.addWidget(self._build_settings_page())

        self._switch_page(0)

    def _switch_page(self, index: int) -> None:
        self.stack.setCurrentIndex(index)
        for i, btn in enumerate(self.nav_buttons):
            btn.setProperty("active", "true" if i == index else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)
        if index == 1:
            self._refresh_library()
        elif index == 2:
            self._refresh_script_editor()
        elif index == 3:
            self._refresh_voice_studio()
        elif index == 4:
            self._refresh_music_studio()
        elif index == 5:
            self._refresh_visual_studio()

    # ---------------- 1. HOME / CREATE VIDEO ----------------
    def _build_home_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 20, 24, 24)
        layout.setSpacing(14)

        title = QLabel(self.loc.t("home.header"))
        title.setObjectName("PageTitle")
        sub = QLabel(self.loc.t("home.subheader"))
        sub.setObjectName("PageSub")
        sub.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(sub)

        # Form Card
        form_card = QFrame()
        form_card.setObjectName("Card")
        fl = QVBoxLayout(form_card)
        fl.setContentsMargins(18, 16, 18, 16)
        fl.setSpacing(12)

        fl.addWidget(QLabel(self.loc.t("home.topic_label")))
        self.topic_input = QLineEdit()
        self.topic_input.setPlaceholderText(self.loc.t("home.topic_placeholder"))
        fl.addWidget(self.topic_input)

        fl.addWidget(QLabel(self.loc.t("home.instructions_label")))
        self.instructions_input = QPlainTextEdit()
        self.instructions_input.setPlaceholderText(self.loc.t("home.instructions_placeholder"))
        self.instructions_input.setMaximumHeight(68)
        fl.addWidget(self.instructions_input)

        grid = QGridLayout()
        grid.setSpacing(10)

        # Language
        grid.addWidget(QLabel(self.loc.t("home.language_label")), 0, 0)
        self.lang_combo = QComboBox()
        for code in ("ar", "fr", "en", "es", "tr", "de"):
            self.lang_combo.addItem(self.loc.t(f"lang.{code}"), code)
        grid.addWidget(self.lang_combo, 1, 0)

        # Duration
        grid.addWidget(QLabel(self.loc.t("home.duration_label")), 0, 1)
        dur_row = QHBoxLayout()
        self.duration_combo = QComboBox()
        for m in (3, 5, 8, 10):
            self.duration_combo.addItem(f"{m}", m)
        self.duration_combo.addItem(self.loc.t("home.custom_minutes"), -1)
        self.custom_minutes_spin = QSpinBox()
        self.custom_minutes_spin.setRange(1, 30)
        self.custom_minutes_spin.setValue(4)
        self.custom_minutes_spin.setVisible(False)
        self.duration_combo.currentIndexChanged.connect(self._on_duration_changed)
        dur_row.addWidget(self.duration_combo, 1)
        dur_row.addWidget(self.custom_minutes_spin)
        grid.addLayout(dur_row, 1, 1)

        # Content Type
        grid.addWidget(QLabel(self.loc.t("home.content_type_label")), 0, 2)
        self.type_combo = QComboBox()
        for key in ("documentary", "history", "biography", "science", "travel", "motivation", "mystery", "news"):
            self.type_combo.addItem(self.loc.t(f"type.{key}"), key)
        grid.addWidget(self.type_combo, 1, 2)

        # Audience
        grid.addWidget(QLabel(self.loc.t("home.audience_label")), 2, 0)
        self.audience_combo = QComboBox()
        for key in ("general", "children", "youth", "experts"):
            self.audience_combo.addItem(self.loc.t(f"audience.{key}"), key)
        grid.addWidget(self.audience_combo, 3, 0)

        # Tone
        grid.addWidget(QLabel(self.loc.t("home.tone_label")), 2, 1)
        self.tone_combo = QComboBox()
        for key in ("calm", "dramatic", "educational", "mysterious", "inspiring"):
            self.tone_combo.addItem(self.loc.t(f"tone.{key}"), key)
        grid.addWidget(self.tone_combo, 3, 1)

        # Resolution
        grid.addWidget(QLabel(self.loc.t("home.resolution_label")), 2, 2)
        self.res_combo = QComboBox()
        self.res_combo.addItem(self.loc.t("home.resolution_720p"), "720p")
        self.res_combo.addItem(self.loc.t("home.resolution_1080p"), "1080p")
        self.res_combo.currentIndexChanged.connect(self._refresh_storage_banner)
        grid.addWidget(self.res_combo, 3, 2)

        # Modes
        grid.addWidget(QLabel(self.loc.t("home.voice_mode_label")), 4, 0)
        self.voice_mode_combo = QComboBox()
        self.voice_mode_combo.addItem(self.loc.t("mode.auto"), "auto")
        self.voice_mode_combo.addItem(self.loc.t("mode.manual"), "manual")
        grid.addWidget(self.voice_mode_combo, 5, 0)

        grid.addWidget(QLabel(self.loc.t("home.music_mode_label")), 4, 1)
        self.music_mode_combo = QComboBox()
        self.music_mode_combo.addItem(self.loc.t("mode.auto"), "auto")
        self.music_mode_combo.addItem(self.loc.t("mode.manual"), "manual")
        grid.addWidget(self.music_mode_combo, 5, 1)

        grid.addWidget(QLabel(self.loc.t("home.visual_mode_label")), 4, 2)
        self.visual_mode_combo = QComboBox()
        self.visual_mode_combo.addItem(self.loc.t("visual.stock"), "stock")
        self.visual_mode_combo.addItem(self.loc.t("visual.mixed"), "mixed")
        self.visual_mode_combo.addItem(self.loc.t("visual.ai"), "ai")
        grid.addWidget(self.visual_mode_combo, 5, 2)

        fl.addLayout(grid)

        self.res_warning_lbl = QLabel(self.loc.t("home.resolution_1080p_warning"))
        self.res_warning_lbl.setStyleSheet("color: #FBBF24; font-size: 12px;")
        self.res_warning_lbl.setVisible(False)
        fl.addWidget(self.res_warning_lbl)

        self.storage_lbl = QLabel()
        self.storage_lbl.setStyleSheet("color: #94A3B8; font-size: 12px;")
        fl.addWidget(self.storage_lbl)

        btn_row = QHBoxLayout()
        self.btn_create = QPushButton(self.loc.t("home.btn_create"))
        self.btn_create.setObjectName("PrimaryBtn")
        self.btn_create.setCursor(Qt.PointingHandCursor)
        self.btn_create.clicked.connect(lambda: self._start_new_job(stop_after_step=9))

        self.btn_plan_only = QPushButton(self.loc.t("home.btn_generate_plan"))
        self.btn_plan_only.setObjectName("SecondaryBtn")
        self.btn_plan_only.clicked.connect(lambda: self._start_new_job(stop_after_step=3))

        self.btn_cancel = QPushButton(self.loc.t("home.btn_cancel"))
        self.btn_cancel.setObjectName("DangerBtn")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel_job)

        self.btn_retry = QPushButton(self.loc.t("home.btn_retry"))
        self.btn_retry.setObjectName("SecondaryBtn")
        self.btn_retry.setVisible(False)
        self.btn_retry.clicked.connect(self._retry_failed_job)

        self.btn_open_out = QPushButton(self.loc.t("home.btn_open_output"))
        self.btn_open_out.setObjectName("SecondaryBtn")
        self.btn_open_out.setVisible(False)
        self.btn_open_out.clicked.connect(self._open_current_output)

        btn_row.addWidget(self.btn_create)
        btn_row.addWidget(self.btn_plan_only)
        btn_row.addWidget(self.btn_cancel)
        btn_row.addWidget(self.btn_retry)
        btn_row.addWidget(self.btn_open_out)
        btn_row.addStretch()
        fl.addLayout(btn_row)
        layout.addWidget(form_card)

        # Progress Card
        prog_card = QFrame()
        prog_card.setObjectName("Card")
        pl = QVBoxLayout(prog_card)
        pl.setContentsMargins(18, 16, 18, 16)
        pl.setSpacing(8)

        pl.addWidget(QLabel(self.loc.t("home.progress_title")))
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 9)
        self.progress_bar.setValue(0)
        pl.addWidget(self.progress_bar)

        self.status_banner = QLabel(self.loc.t("home.status_idle"))
        self.status_banner.setStyleSheet("color: #CBD5E1; font-weight: 600;")
        self.status_banner.setWordWrap(True)
        pl.addWidget(self.status_banner)

        self.step_rows.clear()
        for step_num in range(1, 10):
            row = StepProgressRow(step_num, self.loc.t(f"step.{step_num}"))
            self.step_rows[step_num] = row
            pl.addWidget(row)

        layout.addWidget(prog_card)
        layout.addStretch()
        scroll.setWidget(container)
        return scroll

    def _selected_minutes(self) -> int:
        val = self.duration_combo.currentData()
        if val == -1:
            return self.custom_minutes_spin.value()
        return int(val)

    def _on_duration_changed(self) -> None:
        is_custom = self.duration_combo.currentData() == -1
        self.custom_minutes_spin.setVisible(is_custom)
        self._refresh_storage_banner()

    def _refresh_storage_banner(self) -> None:
        res = str(self.res_combo.currentData() or "720p")
        self.res_warning_lbl.setVisible(res == "1080p")
        req_mb = ProjectManager.estimate_required_mb(self._selected_minutes(), res)
        free_gb = self.project_manager.get_free_space_gb()
        self.storage_lbl.setText(self.loc.t("home.storage_estimate", mb=req_mb, free_gb=free_gb))

    def _start_new_job(self, stop_after_step: int = 9) -> None:
        topic = self.topic_input.text().strip()
        if not topic:
            QMessageBox.warning(self, self.loc.t("app.title"), self.loc.t("err.missing_topic"))
            return
        proj = self.project_manager.create_project(
            title=topic,
            language=str(self.lang_combo.currentData()),
            target_minutes=self._selected_minutes(),
            extra_instructions=self.instructions_input.toPlainText(),
            content_type=str(self.type_combo.currentData()),
            audience=str(self.audience_combo.currentData()),
            tone=str(self.tone_combo.currentData()),
            visual_mode=str(self.visual_mode_combo.currentData()),
            resolution=str(self.res_combo.currentData()),
        )
        proj.voice_config.mode = str(self.voice_mode_combo.currentData())
        proj.music_config.mode = str(self.music_mode_combo.currentData())
        self.project_manager.save_project(proj)
        self.current_project = proj
        self._run_pipeline(proj, start_step=1, stop_after_step=stop_after_step)

    def _run_pipeline(self, project: Project, start_step: int, stop_after_step: int) -> None:
        if self.worker and self.worker.isRunning():
            return
        for s_num, row in self.step_rows.items():
            if s_num < start_step:
                row.set_state("done")
            else:
                row.set_state("pending")
        self.progress_bar.setValue(max(0, start_step - 1))
        self.btn_create.setEnabled(False)
        self.btn_plan_only.setEnabled(False)
        self.btn_cancel.setEnabled(True)
        self.btn_retry.setVisible(False)
        self.btn_open_out.setVisible(False)

        self.worker = PipelineWorker(
            self.settings,
            self.project_manager,
            self.loc,
            project,
            start_step=start_step,
            stop_after_step=stop_after_step,
        )
        self.worker.step_started.connect(self._on_step_started)
        self.worker.step_completed.connect(self._on_step_completed)
        self.worker.detail_updated.connect(self._on_detail_updated)
        self.worker.finished_project.connect(self._on_pipeline_finished)
        self.worker.cancelled_signal.connect(self._on_pipeline_cancelled)
        self.worker.failed_signal.connect(self._on_pipeline_failed)
        self.worker.start()

    def _on_step_started(self, step: int, label: str) -> None:
        if step in self.step_rows:
            self.step_rows[step].set_state("running")
        self.status_banner.setText(self.loc.t("home.status_running", step=label))
        self.status_banner.setStyleSheet("color: #FDE68A; font-weight: 600;")

    def _on_step_completed(self, step: int) -> None:
        if step in self.step_rows:
            self.step_rows[step].set_state("done")
        self.progress_bar.setValue(step)

    def _on_detail_updated(self, msg: str) -> None:
        cur = self.progress_bar.value() + 1
        if cur in self.step_rows:
            self.step_rows[cur].detail.setText(msg)

    def _on_pipeline_finished(self, project: Project) -> None:
        self.current_project = project
        self.btn_create.setEnabled(True)
        self.btn_plan_only.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_open_out.setVisible(True)
        if project.completed_step >= 9:
            self.status_banner.setText(self.loc.t("home.status_completed"))
            self.status_banner.setStyleSheet("color: #34D399; font-weight: 700;")
        else:
            self.status_banner.setText(self.loc.t("script.header"))
            self.status_banner.setStyleSheet("color: #34D399; font-weight: 700;")
            self._switch_page(2)

    def _on_pipeline_cancelled(self) -> None:
        self.btn_create.setEnabled(True)
        self.btn_plan_only.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_retry.setVisible(True)
        self.status_banner.setText(self.loc.t("home.status_cancelled"))
        self.status_banner.setStyleSheet("color: #FBBF24; font-weight: 600;")

    def _on_pipeline_failed(self, step: int, message: str) -> None:
        if step in self.step_rows:
            self.step_rows[step].set_state("failed")
        self.btn_create.setEnabled(True)
        self.btn_plan_only.setEnabled(True)
        self.btn_cancel.setEnabled(False)
        self.btn_retry.setVisible(True)
        self.status_banner.setText(f"{self.loc.t('home.status_failed', step=self.loc.t(f'step.{step}'))}\n{message}")
        self.status_banner.setStyleSheet("color: #FCA5A5; font-weight: 600;")
        QMessageBox.warning(self, self.loc.t("app.title"), message)

    def _cancel_job(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.request_cancel()

    def _retry_failed_job(self) -> None:
        if not self.current_project:
            return
        start_step = self.current_project.failed_step or (self.current_project.completed_step + 1)
        start_step = max(1, min(9, start_step))
        self._run_pipeline(self.current_project, start_step=start_step, stop_after_step=9)

    def _open_current_output(self) -> None:
        if self.current_project:
            _open_folder_silently(self.current_project.folder_path)

    # ---------------- 2. PROJECT LIBRARY ----------------
    def _build_library_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel(self.loc.t("library.header"))
        title.setObjectName("PageTitle")
        btn_ref = QPushButton(self.loc.t("library.refresh"))
        btn_ref.setObjectName("SecondaryBtn")
        btn_ref.clicked.connect(self._refresh_library)
        top.addWidget(title, 1)
        top.addWidget(btn_ref)
        layout.addLayout(top)

        self.library_scroll = QScrollArea()
        self.library_scroll.setWidgetResizable(True)
        self.library_container = QWidget()
        self.library_list_layout = QVBoxLayout(self.library_container)
        self.library_list_layout.setSpacing(10)
        self.library_scroll.setWidget(self.library_container)
        layout.addWidget(self.library_scroll, 1)
        return page

    def _refresh_library(self) -> None:
        while self.library_list_layout.count():
            item = self.library_list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        projects = self.project_manager.list_projects()
        if not projects:
            empty = QLabel(self.loc.t("library.empty"))
            empty.setStyleSheet("color: #94A3B8; padding: 20px;")
            self.library_list_layout.addWidget(empty)
        else:
            for p in projects:
                card = ProjectCard(p, self.loc)
                card.open_folder.connect(_open_folder_silently)
                card.edit_script.connect(self._open_project_in_script_editor)
                card.resume_project.connect(self._resume_project_from_library)
                card.delete_project.connect(self._delete_project_from_library)
                self.library_list_layout.addWidget(card)
        self.library_list_layout.addStretch()

    def _open_project_in_script_editor(self, project_id: str) -> None:
        proj = self.project_manager.load_project(project_id)
        if proj:
            self.current_project = proj
            self._switch_page(2)

    def _resume_project_from_library(self, project_id: str) -> None:
        proj = self.project_manager.load_project(project_id)
        if not proj:
            return
        self.current_project = proj
        start_step = proj.failed_step or (proj.completed_step + 1)
        if start_step > 9:
            start_step = 8
        self._switch_page(0)
        self._run_pipeline(proj, start_step=start_step, stop_after_step=9)

    def _delete_project_from_library(self, project_id: str) -> None:
        proj = self.project_manager.load_project(project_id)
        if not proj:
            return
        ans = QMessageBox.question(
            self,
            self.loc.t("app.title"),
            self.loc.t("library.confirm_delete", title=proj.title),
        )
        if ans == QMessageBox.Yes:
            self.project_manager.delete_project(project_id)
            if self.current_project and self.current_project.project_id == project_id:
                self.current_project = None
            self._refresh_library()

    # ---------------- 3. SCRIPT EDITOR ----------------
    def _build_script_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        top = QHBoxLayout()
        title = QLabel(self.loc.t("script.header"))
        title.setObjectName("PageTitle")
        self.btn_save_script = QPushButton(self.loc.t("script.btn_save"))
        self.btn_save_script.setObjectName("SecondaryBtn")
        self.btn_save_script.clicked.connect(self._save_script_edits)

        self.btn_approve_render = QPushButton(self.loc.t("script.btn_approve_render"))
        self.btn_approve_render.setObjectName("PrimaryBtn")
        self.btn_approve_render.clicked.connect(self._approve_and_render)

        top.addWidget(title, 1)
        top.addWidget(self.btn_save_script)
        top.addWidget(self.btn_approve_render)
        layout.addLayout(top)

        self.script_warn_banner = QFrame()
        self.script_warn_banner.setObjectName("WarnBanner")
        wb_lay = QVBoxLayout(self.script_warn_banner)
        self.script_warn_lbl = QLabel()
        self.script_warn_lbl.setWordWrap(True)
        wb_lay.addWidget(self.script_warn_lbl)
        self.script_warn_banner.setVisible(False)
        layout.addWidget(self.script_warn_banner)

        self.script_scroll = QScrollArea()
        self.script_scroll.setWidgetResizable(True)
        self.script_container = QWidget()
        self.script_lay = QVBoxLayout(self.script_container)
        self.script_lay.setSpacing(10)
        self.script_scroll.setWidget(self.script_container)
        layout.addWidget(self.script_scroll, 1)
        return page

    def _refresh_script_editor(self) -> None:
        while self.script_lay.count():
            item = self.script_lay.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.scene_editors.clear()

        if not self.current_project:
            self.script_warn_banner.setVisible(False)
            self.script_lay.addWidget(QLabel(self.loc.t("script.no_project")))
            self.script_lay.addStretch()
            return

        proj = self.current_project
        if proj.research.sensitive_topics:
            self.script_warn_lbl.setText(
                self.loc.t("script.sensitive_warning", topics=", ".join(proj.research.sensitive_topics))
            )
            self.script_warn_banner.setVisible(True)
        else:
            self.script_warn_banner.setVisible(False)

        # Sources & warnings card
        if proj.research.sources or proj.research.warnings:
            src_card = QFrame()
            src_card.setObjectName("Card")
            sl = QVBoxLayout(src_card)
            sl.setContentsMargins(12, 10, 12, 10)
            if proj.research.sources:
                sl.addWidget(QLabel(self.loc.t("script.sources_title")))
                for src in proj.research.sources:
                    lbl = QLabel(f"• {src.get('title', 'Source')}: {src.get('url', '')}")
                    lbl.setTextInteractionFlags(Qt.TextSelectableByMouse)
                    lbl.setStyleSheet("color: #93C5FD; font-size: 12px;")
                    lbl.setWordWrap(True)
                    sl.addWidget(lbl)
            if proj.research.warnings:
                sl.addWidget(QLabel(self.loc.t("script.disputed_title")))
                for w in proj.research.warnings:
                    wl = QLabel(f"⚠ {w}")
                    wl.setStyleSheet("color: #FBBF24; font-size: 12px;")
                    wl.setWordWrap(True)
                    sl.addWidget(wl)
            self.script_lay.addWidget(src_card)

        for scene in proj.scenes:
            editor = SceneEditorWidget(scene, self.loc)
            editor.regenerate_requested.connect(self._regen_single_scene)
            self.scene_editors.append(editor)
            self.script_lay.addWidget(editor)
        self.script_lay.addStretch()

    def _save_script_edits(self) -> None:
        if not self.current_project:
            return
        for ed in self.scene_editors:
            ed.apply_changes()
        self.current_project.full_script_markdown = "\n\n".join(
            f"### {s.title or f'Scene {s.id}'}\n{s.narration}" for s in self.current_project.scenes
        )
        self.project_manager.save_project(self.current_project)
        QMessageBox.information(self, self.loc.t("app.title"), self.loc.t("script.saved_ok"))

    def _regen_single_scene(self, scene_id: int) -> None:
        if not self.current_project:
            return
        api_key = self.settings.get_api_key(self.settings.config.active_ai_provider)
        if not api_key:
            QMessageBox.warning(self, self.loc.t("app.title"), self.loc.t("err.missing_ai_key"))
            return
        try:
            ai = build_ai_provider(self.settings.config.active_ai_provider, api_key)
            for s in self.current_project.scenes:
                if s.id == scene_id:
                    ScenePlanner().regenerate_single_scene(ai, self.current_project, s)
                    break
            self.project_manager.save_project(self.current_project)
            self._refresh_script_editor()
        except DocuMakerError as exc:
            QMessageBox.warning(self, self.loc.t("app.title"), exc.user_message(self.loc))

    def _approve_and_render(self) -> None:
        if not self.current_project:
            return
        for ed in self.scene_editors:
            ed.apply_changes()
        self.current_project.script_approved = True
        self.project_manager.save_project(self.current_project)
        self._switch_page(0)
        self._run_pipeline(self.current_project, start_step=4, stop_after_step=9)

    # ---------------- 4. VOICE STUDIO ----------------
    def _build_voice_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel(self.loc.t("voice.header"))
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        card = QFrame()
        card.setObjectName("Card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(10)

        cl.addWidget(QLabel(self.loc.t("voice.voice_label")))
        self.voice_combo = QComboBox()
        for v in EdgeTTSProvider().list_voices():
            self.voice_combo.addItem(f"{v.display_name} ({v.language})", v.voice_id)
        cl.addWidget(self.voice_combo)

        cl.addWidget(QLabel(self.loc.t("voice.speed_label")))
        self.rate_slider = QSlider(Qt.Horizontal)
        self.rate_slider.setRange(-35, 35)
        self.rate_slider.setValue(0)
        cl.addWidget(self.rate_slider)

        cl.addWidget(QLabel(self.loc.t("voice.pitch_label")))
        self.pitch_slider = QSlider(Qt.Horizontal)
        self.pitch_slider.setRange(-20, 20)
        self.pitch_slider.setValue(0)
        cl.addWidget(self.pitch_slider)

        self.preview_text = QLineEdit(self.loc.t("voice.sample_text"))
        cl.addWidget(self.preview_text)

        row = QHBoxLayout()
        b_prev = QPushButton(self.loc.t("voice.btn_preview"))
        b_prev.setObjectName("SecondaryBtn")
        b_prev.clicked.connect(self._preview_voice)

        b_apply = QPushButton(self.loc.t("voice.btn_regen_all"))
        b_apply.setObjectName("PrimaryBtn")
        b_apply.clicked.connect(self._apply_voice_and_regen)
        row.addWidget(b_prev)
        row.addWidget(b_apply)
        row.addStretch()
        cl.addLayout(row)

        layout.addWidget(card)
        layout.addStretch()
        return page

    def _refresh_voice_studio(self) -> None:
        if not self.current_project:
            return
        idx = self.voice_combo.findData(self.current_project.voice_config.voice_id)
        if idx >= 0:
            self.voice_combo.setCurrentIndex(idx)

    def _preview_voice(self) -> None:
        rate_val = self.rate_slider.value()
        pitch_val = self.pitch_slider.value()
        rate_str = f"{rate_val:+d}%"
        pitch_str = f"{pitch_val:+d}Hz"
        out = self.settings.cache_dir / "voice_preview.mp3"
        self.preview_worker = VoicePreviewWorker(
            text=self.preview_text.text().strip() or self.loc.t("voice.sample_text"),
            output_path=out,
            voice_id=str(self.voice_combo.currentData()),
            rate=rate_str,
            pitch=pitch_str,
            volume="+0%",
            loc=self.loc,
        )
        self.preview_worker.finished_signal.connect(self._on_voice_preview_ready)
        self.preview_worker.error_signal.connect(
            lambda err: QMessageBox.warning(self, self.loc.t("app.title"), err)
        )
        self.preview_worker.start()

    def _on_voice_preview_ready(self, audio_file: str) -> None:
        try:
            from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer

            self._player = QMediaPlayer(self)
            self._audio_out = QAudioOutput(self)
            self._player.setAudioOutput(self._audio_out)
            self._player.setSource(QUrl.fromLocalFile(audio_file))
            self._audio_out.setVolume(0.9)
            self._player.play()
        except Exception:
            QMessageBox.information(self, self.loc.t("app.title"), self.loc.t("voice.preview_ready"))

    def _apply_voice_and_regen(self) -> None:
        if not self.current_project:
            QMessageBox.warning(self, self.loc.t("app.title"), self.loc.t("script.no_project"))
            return
        self.current_project.voice_config.mode = "manual"
        self.current_project.voice_config.voice_id = str(self.voice_combo.currentData())
        self.current_project.voice_config.rate = f"{self.rate_slider.value():+d}%"
        self.current_project.voice_config.pitch = f"{self.pitch_slider.value():+d}Hz"
        self.project_manager.save_project(self.current_project)
        self._switch_page(0)
        self._run_pipeline(self.current_project, start_step=4, stop_after_step=9)

    # ---------------- 5. MUSIC & SOUND STUDIO ----------------
    def _build_music_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        title = QLabel(self.loc.t("music.header"))
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        card = QFrame()
        card.setObjectName("Card")
        cl = QVBoxLayout(card)
        cl.setContentsMargins(16, 14, 16, 14)
        cl.setSpacing(10)

        self.music_selected_lbl = QLabel(self.loc.t("music.none_selected"))
        cl.addWidget(self.music_selected_lbl)

        btn_upload = QPushButton(self.loc.t("music.btn_upload"))
        btn_upload.setObjectName("SecondaryBtn")
        btn_upload.clicked.connect(self._upload_music_file)
        cl.addWidget(btn_upload)

        cl.addWidget(QLabel(self.loc.t("music.volume_label")))
        self.music_vol_slider = QSlider(Qt.Horizontal)
        self.music_vol_slider.setRange(5, 60)
        self.music_vol_slider.setValue(22)
        self.music_vol_slider.valueChanged.connect(self._save_music_settings)
        cl.addWidget(self.music_vol_slider)

        self.ducking_check = QCheckBox(self.loc.t("music.ducking_check"))
        self.ducking_check.setChecked(True)
        self.ducking_check.toggled.connect(self._save_music_settings)
        cl.addWidget(self.ducking_check)

        self.fade_check = QCheckBox(self.loc.t("music.fade_check"))
        self.fade_check.setChecked(True)
        self.fade_check.toggled.connect(self._save_music_settings)
        cl.addWidget(self.fade_check)

        layout.addWidget(card)
        layout.addStretch()
        return page

    def _refresh_music_studio(self) -> None:
        if not self.current_project:
            self.music_selected_lbl.setText(self.loc.t("music.none_selected"))
            return
        mc = self.current_project.music_config
        self.music_vol_slider.setValue(int(mc.volume * 100))
        self.ducking_check.setChecked(mc.ducking_enabled)
        if mc.track_title:
            self.music_selected_lbl.setText(self.loc.t("music.selected_track", name=mc.track_title))
        else:
            self.music_selected_lbl.setText(self.loc.t("music.none_selected"))

    def _upload_music_file(self) -> None:
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.loc.t("music.btn_upload"),
            "",
            "Audio Files (*.mp3 *.wav *.aac *.m4a *.ogg)",
        )
        if not file_path or not self.current_project:
            return
        dest = Path(self.current_project.folder_path) / "music" / Path(file_path).name
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file_path, dest)
        self.current_project.music_config.mode = "manual"
        self.current_project.music_config.provider = "local"
        self.current_project.music_config.track_path = str(dest)
        self.current_project.music_config.track_title = dest.name
        self.current_project.music_config.license_name = "User Uploaded Audio"
        self.project_manager.save_project(self.current_project)
        self._refresh_music_studio()

    def _save_music_settings(self) -> None:
        if not self.current_project:
            return
        self.current_project.music_config.volume = self.music_vol_slider.value() / 100.0
        self.current_project.music_config.ducking_enabled = self.ducking_check.isChecked()
        if not self.fade_check.isChecked():
            self.current_project.music_config.fade_in_seconds = 0.0
            self.current_project.music_config.fade_out_seconds = 0.0
        else:
            self.current_project.music_config.fade_in_seconds = 2.0
            self.current_project.music_config.fade_out_seconds = 3.0
        self.project_manager.save_project(self.current_project)

    # ---------------- 6. VISUAL STUDIO ----------------
    def _build_visuals_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(10)

        title = QLabel(self.loc.t("visuals.header"))
        title.setObjectName("PageTitle")
        layout.addWidget(title)

        opts = QHBoxLayout()
        self.kb_check = QCheckBox(self.loc.t("visuals.ken_burns"))
        self.kb_check.setChecked(True)
        self.kb_check.toggled.connect(self._save_visual_toggles)
        self.sub_burn_check = QCheckBox(self.loc.t("visuals.subtitles_burn"))
        self.sub_burn_check.setChecked(True)
        self.sub_burn_check.toggled.connect(self._save_visual_toggles)
        opts.addWidget(self.kb_check)
        opts.addWidget(self.sub_burn_check)
        opts.addStretch()
        layout.addLayout(opts)

        self.visual_scene_list = QListWidget()
        self.visual_scene_list.currentRowChanged.connect(self._on_visual_scene_selected)
        layout.addWidget(self.visual_scene_list, 1)

        replace_row = QHBoxLayout()
        self.vis_search_input = QLineEdit()
        self.vis_search_input.setPlaceholderText(self.loc.t("visuals.search_placeholder"))
        b_search = QPushButton(self.loc.t("visuals.btn_search"))
        b_search.setObjectName("SecondaryBtn")
        b_search.clicked.connect(self._replace_scene_from_pexels)
        b_local = QPushButton(self.loc.t("visuals.btn_upload_scene"))
        b_local.setObjectName("SecondaryBtn")
        b_local.clicked.connect(self._replace_scene_from_local)
        replace_row.addWidget(self.vis_search_input, 1)
        replace_row.addWidget(b_search)
        replace_row.addWidget(b_local)
        layout.addLayout(replace_row)

        self.vis_license_lbl = QLabel()
        self.vis_license_lbl.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(self.vis_license_lbl)
        return page

    def _refresh_visual_studio(self) -> None:
        self.visual_scene_list.clear()
        if not self.current_project:
            return
        self.kb_check.setChecked(self.current_project.ken_burns_enabled)
        self.sub_burn_check.setChecked(self.current_project.burn_subtitles)
        for s in self.current_project.scenes:
            media_desc = s.selected_media.attribution if s.selected_media else "No media yet"
            item = QListWidgetItem(f"{s.id}. {s.title or s.narration[:40]} — [{media_desc}]")
            self.visual_scene_list.addItem(item)

    def _on_visual_scene_selected(self, row: int) -> None:
        if not self.current_project or row < 0 or row >= len(self.current_project.scenes):
            return
        s = self.current_project.scenes[row]
        lic = s.selected_media.license_name if s.selected_media else "-"
        self.vis_license_lbl.setText(self.loc.t("visuals.license_label", license=lic))

    def _save_visual_toggles(self) -> None:
        if not self.current_project:
            return
        self.current_project.ken_burns_enabled = self.kb_check.isChecked()
        self.current_project.burn_subtitles = self.sub_burn_check.isChecked()
        self.project_manager.save_project(self.current_project)

    def _replace_scene_from_pexels(self) -> None:
        row = self.visual_scene_list.currentRow()
        if not self.current_project or row < 0:
            return
        query = self.vis_search_input.text().strip()
        if not query:
            return
        pexels_key = self.settings.get_api_key("pexels")
        pixabay_key = self.settings.get_api_key("pixabay")
        if not pexels_key and not pixabay_key:
            QMessageBox.warning(self, self.loc.t("app.title"), "Connect Pexels or Pixabay in Settings first.")
            return
        try:
            pexels = PexelsMediaProvider(pexels_key, cache_dir=self.settings.cache_dir) if pexels_key else None
            pixabay = PixabayProvider(pixabay_key) if pixabay_key else None
            items = []
            for provider in (pexels, pixabay):
                if not provider:
                    continue
                try:
                    items.extend(provider.search_videos(query, per_page=2))
                    items.extend(provider.search_images(query, per_page=2))
                except DocuMakerError:
                    continue
            if not items:
                QMessageBox.information(self, self.loc.t("app.title"), self.loc.t("err.no_visuals_found", scene=row + 1))
                return
            items.sort(key=lambda item: item.score, reverse=True)
            scene = self.current_project.scenes[row]
            chosen = items[0]
            dest = Path(self.current_project.folder_path) / "visuals"
            if chosen.provider == "pexels" and pexels:
                pexels.download_candidate(chosen, dest, f"scene_{scene.id:03d}_custom")
            elif chosen.provider == "pixabay" and pixabay:
                pixabay.download_candidate(chosen, dest, f"scene_{scene.id:03d}_custom")
            scene.selected_media = chosen
            self.project_manager.save_project(self.current_project)
            self._refresh_visual_studio()
        except DocuMakerError as exc:
            QMessageBox.warning(self, self.loc.t("app.title"), exc.user_message(self.loc))

    def _replace_scene_from_local(self) -> None:
        row = self.visual_scene_list.currentRow()
        if not self.current_project or row < 0:
            return
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            self.loc.t("visuals.btn_upload_scene"),
            "",
            "Media (*.jpg *.jpeg *.png *.mp4 *.mov)",
        )
        if not file_path:
            return
        src = Path(file_path)
        dest = Path(self.current_project.folder_path) / "visuals" / f"scene_{row + 1:03d}_local{src.suffix}"
        shutil.copy2(src, dest)
        is_vid = src.suffix.lower() in (".mp4", ".mov")
        self.current_project.scenes[row].selected_media = MediaCandidate(
            provider="local",
            media_type="video" if is_vid else "image",
            media_id=src.name,
            url="",
            download_url="",
            license_name="User Supplied Media",
            attribution="Local File",
            local_path=str(dest),
        )
        self.project_manager.save_project(self.current_project)
        self._refresh_visual_studio()

    # ---------------- 7. SETTINGS / API CONNECTIONS ----------------
    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        top = QHBoxLayout()
        title = QLabel(self.loc.t("settings.header"))
        title.setObjectName("PageTitle")
        b_save = QPushButton(self.loc.t("settings.btn_save"))
        b_save.setObjectName("PrimaryBtn")
        b_save.clicked.connect(self._save_all_settings)
        top.addWidget(title, 1)
        top.addWidget(b_save)
        layout.addLayout(top)

        tabs = QTabWidget()

        # Tab 1: AI Provider
        ai_tab = QWidget()
        ai_lay = QVBoxLayout(ai_tab)
        ai_lay.addWidget(QLabel(self.loc.t("settings.tab.ai")))
        self.active_ai_combo = QComboBox()
        for pid, label in (
            ("gemini", "Google Gemini (Recommended Free Tier)"),
            ("groq", "Groq Llama 3.3 (Fast Free Tier)"),
            ("openrouter", "OpenRouter"),
            ("openai", "OpenAI"),
        ):
            self.active_ai_combo.addItem(label, pid)
        ai_idx = self.active_ai_combo.findData(self.settings.config.active_ai_provider)
        if ai_idx >= 0:
            self.active_ai_combo.setCurrentIndex(ai_idx)
        ai_lay.addWidget(self.active_ai_combo)

        model_options = {
            "gemini": ("gemini_model", ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash", "gemini-2.0-flash-lite"]),
            "groq": ("groq_model", ["llama-3.3-70b-versatile", "openai/gpt-oss-20b", "llama-4-scout-17b-16e-instruct", "qwen/qwen3-32b"]),
            "openrouter": ("openrouter_model", ["google/gemini-2.5-flash", "openai/gpt-4o-mini", "meta-llama/llama-3.3-70b-instruct:free", "deepseek/deepseek-chat-v3-0324:free"]),
            "openai": ("openai_model", ["gpt-4o-mini", "gpt-4o", "gpt-4.1-mini", "gpt-4.1", "o4-mini"]),
        }
        for pid, name, free in (
            ("gemini", "Google Gemini", True),
            ("groq", "Groq", True),
            ("openrouter", "OpenRouter", True),
            ("openai", "OpenAI", False),
        ):
            card = ProviderSettingsCard(pid, name, free, self.settings.get_api_key(pid), self.loc)
            card.test_requested.connect(self._test_provider)
            card.disconnect_requested.connect(self._disconnect_provider)
            self.provider_cards[pid] = card
            ai_lay.addWidget(card)
            attr, suggestions = model_options[pid]
            model_label = QLabel(f"{name} model / version (editable)")
            model_combo = QComboBox()
            model_combo.setEditable(True)
            model_combo.addItems(suggestions)
            model_combo.setCurrentText(str(getattr(self.settings.config, attr)))
            model_combo.setToolTip("Choose a suggested model or enter any model ID supported by this provider.")
            self.ai_model_combos[pid] = model_combo
            ai_lay.addWidget(model_label)
            ai_lay.addWidget(model_combo)
        ai_lay.addStretch()
        tabs.addTab(ai_tab, self.loc.t("settings.tab.ai"))

        # Tab 2: Voices
        v_tab = QWidget()
        v_lay = QVBoxLayout(v_tab)
        edge_lbl = QLabel(f"Edge-TTS: {self.loc.t('settings.status.connected')} ({self.loc.t('settings.free_tier')})")
        edge_lbl.setStyleSheet("color: #34D399; font-weight: 700; padding: 8px;")
        v_lay.addWidget(edge_lbl)
        el_card = ProviderSettingsCard("elevenlabs", "ElevenLabs (Optional Premium)", False, self.settings.get_api_key("elevenlabs"), self.loc)
        el_card.test_requested.connect(self._test_provider)
        el_card.disconnect_requested.connect(self._disconnect_provider)
        self.provider_cards["elevenlabs"] = el_card
        v_lay.addWidget(el_card)
        v_lay.addStretch()
        tabs.addTab(v_tab, self.loc.t("settings.tab.voices"))

        # Tab 3: Music
        m_tab = QWidget()
        m_lay = QVBoxLayout(m_tab)
        px_card = ProviderSettingsCard("pixabay", "Pixabay Music & Media", True, self.settings.get_api_key("pixabay"), self.loc)
        px_card.test_requested.connect(self._test_provider)
        px_card.disconnect_requested.connect(self._disconnect_provider)
        self.provider_cards["pixabay"] = px_card
        m_lay.addWidget(px_card)
        m_lay.addStretch()
        tabs.addTab(m_tab, self.loc.t("settings.tab.music"))

        # Tab 4: Images / Video
        im_tab = QWidget()
        im_lay = QVBoxLayout(im_tab)
        pex_card = ProviderSettingsCard("pexels", "Pexels Photos & Videos (Optional)", True, self.settings.get_api_key("pexels"), self.loc)
        pex_card.test_requested.connect(self._test_provider)
        pex_card.disconnect_requested.connect(self._disconnect_provider)
        self.provider_cards["pexels"] = pex_card
        im_lay.addWidget(pex_card)
        wiki_lbl = QLabel(f"Wikimedia Commons: {self.loc.t('settings.status.connected')} ({self.loc.t('settings.free_tier')})")
        wiki_lbl.setStyleSheet("color: #34D399; font-weight: 700; padding: 8px;")
        im_lay.addWidget(wiki_lbl)
        im_lay.addStretch()
        tabs.addTab(im_tab, self.loc.t("settings.tab.media"))

        # Tab 5: Languages
        l_tab = QWidget()
        l_lay = QVBoxLayout(l_tab)
        l_lay.addWidget(QLabel(self.loc.t("settings.ui_lang_label")))
        self.ui_lang_combo = QComboBox()
        self.ui_lang_combo.addItem("العربية (RTL)", "ar")
        self.ui_lang_combo.addItem("Français", "fr")
        self.ui_lang_combo.addItem("English", "en")
        l_idx = self.ui_lang_combo.findData(self.settings.config.ui_language)
        if l_idx >= 0:
            self.ui_lang_combo.setCurrentIndex(l_idx)
        l_lay.addWidget(self.ui_lang_combo)
        l_lay.addStretch()
        tabs.addTab(l_tab, self.loc.t("settings.tab.languages"))

        # Tab 6: Output
        o_tab = QWidget()
        o_lay = QVBoxLayout(o_tab)
        o_lay.addWidget(QLabel(self.loc.t("settings.projects_dir_label")))
        dir_row = QHBoxLayout()
        self.projects_dir_edit = QLineEdit(str(self.settings.get_projects_dir()))
        b_browse = QPushButton(self.loc.t("settings.btn_browse"))
        b_browse.setObjectName("SecondaryBtn")
        b_browse.clicked.connect(self._browse_projects_dir)
        dir_row.addWidget(self.projects_dir_edit, 1)
        dir_row.addWidget(b_browse)
        o_lay.addLayout(dir_row)
        self.ai_disclosure_check = QCheckBox(self.loc.t("settings.ai_disclosure"))
        self.ai_disclosure_check.setChecked(self.settings.config.ai_disclosure_default)
        o_lay.addWidget(self.ai_disclosure_check)
        o_lay.addStretch()
        tabs.addTab(o_tab, self.loc.t("settings.tab.output"))

        # Tab 7: Account / Storage
        a_tab = QWidget()
        a_lay = QVBoxLayout(a_tab)
        b_cache = QPushButton(self.loc.t("settings.clear_cache"))
        b_cache.setObjectName("SecondaryBtn")
        b_cache.clicked.connect(self._clear_cache)
        a_lay.addWidget(b_cache)
        a_lay.addStretch()
        tabs.addTab(a_tab, self.loc.t("settings.tab.account"))

        layout.addWidget(tabs, 1)
        return page

    def _browse_projects_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, self.loc.t("settings.projects_dir_label"))
        if folder:
            self.projects_dir_edit.setText(folder)

    def _clear_cache(self) -> None:
        freed_mb = self.settings.clear_cache()
        QMessageBox.information(self, self.loc.t("app.title"), self.loc.t("settings.cache_cleared", mb=freed_mb))

    def _disconnect_provider(self, provider_id: str) -> None:
        self.settings.set_api_key(provider_id, "")

    def _test_provider(self, provider_id: str, raw_key: str) -> None:
        key = raw_key.strip()
        self.settings.set_api_key(provider_id, key)
        if provider_id in self.provider_cards:
            self.provider_cards[provider_id].refresh_status(bool(key))

        def run_test() -> tuple[bool, str]:
            if provider_id in ("gemini", "openai", "groq", "openrouter"):
                model = self.ai_model_combos[provider_id].currentText().strip() if provider_id in self.ai_model_combos else None
                return build_ai_provider(provider_id, key, model=model).test_connection()
            if provider_id == "pexels":
                return PexelsMediaProvider(key).test_connection()
            if provider_id == "pixabay":
                return PixabayProvider(key).test_connection()
            if provider_id == "elevenlabs":
                return ElevenLabsTTSProvider(key).test_connection()
            return False, "Unknown provider"

        self.test_worker = ProviderTestWorker(provider_id, run_test)
        self.test_worker.result_signal.connect(self._on_provider_test_result)
        self.test_worker.start()

    def _on_provider_test_result(self, provider_id: str, ok: bool, reason: str) -> None:
        if ok:
            QMessageBox.information(self, self.loc.t("app.title"), self.loc.t("settings.test_ok"))
        else:
            QMessageBox.warning(self, self.loc.t("app.title"), self.loc.t("settings.test_fail", reason=reason))

    def _save_all_settings(self) -> None:
        for pid, card in self.provider_cards.items():
            key = card.key_input.text().strip()
            self.settings.set_api_key(pid, key)
            card.refresh_status(bool(key))

        new_lang = str(self.ui_lang_combo.currentData())
        lang_changed = new_lang != self.settings.config.ui_language
        self.settings.config.ui_language = new_lang
        self.settings.config.active_ai_provider = str(self.active_ai_combo.currentData())
        model_attrs = {"gemini": "gemini_model", "openai": "openai_model", "groq": "groq_model", "openrouter": "openrouter_model"}
        for pid, attr in model_attrs.items():
            value = self.ai_model_combos[pid].currentText().strip()
            if value:
                setattr(self.settings.config, attr, value)
        self.settings.config.projects_dir = self.projects_dir_edit.text().strip()
        self.settings.config.ai_disclosure_default = self.ai_disclosure_check.isChecked()
        self.settings.save_config()

        if lang_changed:
            self.loc.set_language(new_lang)
            self._apply_window_chrome()
            self._build_ui()
        QMessageBox.information(self, self.loc.t("app.title"), self.loc.t("settings.saved"))
