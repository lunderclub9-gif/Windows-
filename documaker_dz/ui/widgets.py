"""Reusable PySide6 UI cards and widgets for DocuMaker DZ."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ..core.models import Project, Scene
from ..localization.manager import LocalizationManager


class StepProgressRow(QFrame):
    """Displays one of the 9 documentary generation steps with clear Arabic status."""

    def __init__(self, step_num: int, label_text: str) -> None:
        super().__init__()
        self.step_num = step_num
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 5, 8, 5)
        self.badge = QLabel("○")
        self.badge.setFixedWidth(24)
        self.badge.setAlignment(Qt.AlignCenter)
        self.label = QLabel(label_text)
        self.detail = QLabel("")
        self.detail.setStyleSheet("color: #94A3B8; font-size: 11px;")
        layout.addWidget(self.badge)
        layout.addWidget(self.label, 1)
        layout.addWidget(self.detail)
        self.set_state("pending")

    def set_state(self, state: str, detail: str = "") -> None:
        self.detail.setText(detail)
        if state == "done":
            self.badge.setText("✓")
            self.badge.setStyleSheet("color: #34D399; font-weight: bold;")
            self.label.setStyleSheet("color: #A7F3D0;")
        elif state == "running":
            self.badge.setText("◉")
            self.badge.setStyleSheet("color: #FBBF24; font-weight: bold;")
            self.label.setStyleSheet("color: #FDE68A; font-weight: bold;")
        elif state == "failed":
            self.badge.setText("✕")
            self.badge.setStyleSheet("color: #F87171; font-weight: bold;")
            self.label.setStyleSheet("color: #FCA5A5; font-weight: bold;")
        else:
            self.badge.setText("○")
            self.badge.setStyleSheet("color: #64748B;")
            self.label.setStyleSheet("color: #94A3B8;")


class ProviderSettingsCard(QFrame):
    """API provider configuration card with status badge, masked key input, test & disconnect buttons."""

    test_requested = Signal(str, str)
    disconnect_requested = Signal(str)

    def __init__(
        self,
        provider_id: str,
        display_name: str,
        is_free_tier: bool,
        current_key: str,
        loc: LocalizationManager,
    ) -> None:
        super().__init__()
        self.setObjectName("Card")
        self.provider_id = provider_id
        self.loc = loc

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 12)
        root.setSpacing(8)

        top = QHBoxLayout()
        title_lbl = QLabel(display_name)
        title_lbl.setStyleSheet("font-size: 15px; font-weight: 700; color: #F8FAFC;")
        tier_lbl = QLabel(loc.t("settings.free_tier") if is_free_tier else loc.t("settings.paid_tier"))
        tier_lbl.setStyleSheet(
            "font-size: 11px; color: #34D399; background-color: #064E3B; padding: 3px 8px; border-radius: 6px;"
            if is_free_tier
            else "font-size: 11px; color: #FBBF24; background-color: #451A03; padding: 3px 8px; border-radius: 6px;"
        )
        self.status_lbl = QLabel()
        top.addWidget(title_lbl)
        top.addWidget(tier_lbl)
        top.addStretch()
        top.addWidget(self.status_lbl)
        root.addLayout(top)

        key_row = QHBoxLayout()
        key_row.addWidget(QLabel(loc.t("settings.api_key_label")))
        self.key_input = QLineEdit(current_key)
        self.key_input.setEchoMode(QLineEdit.Password)
        self.key_input.setPlaceholderText("sk-... / AIza...")
        key_row.addWidget(self.key_input, 1)

        self.btn_test = QPushButton(loc.t("settings.btn_test"))
        self.btn_test.setObjectName("SecondaryBtn")
        self.btn_test.clicked.connect(lambda: self.test_requested.emit(self.provider_id, self.key_input.text()))
        key_row.addWidget(self.btn_test)

        self.btn_disconnect = QPushButton(loc.t("settings.btn_disconnect"))
        self.btn_disconnect.setObjectName("DangerBtn")
        self.btn_disconnect.clicked.connect(self._on_disconnect)
        key_row.addWidget(self.btn_disconnect)
        root.addLayout(key_row)

        self.refresh_status(bool(current_key))

    def _on_disconnect(self) -> None:
        self.key_input.clear()
        self.refresh_status(False)
        self.disconnect_requested.emit(self.provider_id)

    def refresh_status(self, connected: bool) -> None:
        if connected:
            self.status_lbl.setText(self.loc.t("settings.status.connected"))
            self.status_lbl.setStyleSheet("color: #34D399; font-weight: 700;")
        else:
            self.status_lbl.setText(self.loc.t("settings.status.disconnected"))
            self.status_lbl.setStyleSheet("color: #94A3B8;")


class ProjectCard(QFrame):
    """Card displayed inside Project Library with actions."""

    open_folder = Signal(str)
    edit_script = Signal(str)
    resume_project = Signal(str)
    delete_project = Signal(str)

    def __init__(self, project: Project, loc: LocalizationManager) -> None:
        super().__init__()
        self.setObjectName("Card")
        self.project_id = project.project_id
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        header = QHBoxLayout()
        title = QLabel(project.title)
        title.setStyleSheet("font-size: 15px; font-weight: 700;")
        status_key = f"library.status.{project.status}"
        status_lbl = QLabel(loc.t(status_key))
        color = {
            "completed": "#34D399",
            "failed": "#F87171",
            "in_progress": "#FBBF24",
        }.get(project.status, "#94A3B8")
        status_lbl.setStyleSheet(f"color: {color}; font-weight: 700;")
        header.addWidget(title, 1)
        header.addWidget(status_lbl)
        layout.addLayout(header)

        dur_text = loc.format_duration_mmss(project.total_duration_seconds or project.target_minutes * 60)
        meta = QLabel(f"{project.created_at}  |  {project.language.upper()}  |  {dur_text}  |  {project.resolution}")
        meta.setStyleSheet("color: #94A3B8; font-size: 12px;")
        layout.addWidget(meta)

        btns = QHBoxLayout()
        b_open = QPushButton(loc.t("library.btn.open_folder"))
        b_open.setObjectName("SecondaryBtn")
        b_open.clicked.connect(lambda: self.open_folder.emit(project.folder_path))

        b_edit = QPushButton(loc.t("library.btn.edit_script"))
        b_edit.setObjectName("SecondaryBtn")
        b_edit.clicked.connect(lambda: self.edit_script.emit(project.project_id))

        b_res = QPushButton(loc.t("library.btn.regenerate"))
        b_res.setObjectName("PrimaryBtn")
        b_res.clicked.connect(lambda: self.resume_project.emit(project.project_id))

        b_del = QPushButton(loc.t("library.btn.delete"))
        b_del.setObjectName("DangerBtn")
        b_del.clicked.connect(lambda: self.delete_project.emit(project.project_id))

        btns.addWidget(b_open)
        btns.addWidget(b_edit)
        btns.addWidget(b_res)
        btns.addStretch()
        btns.addWidget(b_del)
        layout.addLayout(btns)


class SceneEditorWidget(QFrame):
    """Editable scene block in Script Editor."""

    regenerate_requested = Signal(int)

    def __init__(self, scene: Scene, loc: LocalizationManager) -> None:
        super().__init__()
        self.setObjectName("Card")
        self.scene = scene

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        head = QHBoxLayout()
        dur = round(scene.actual_audio_duration or scene.estimated_duration_seconds)
        lbl = QLabel(loc.t("script.scene_label", num=scene.id, sec=dur))
        lbl.setStyleSheet("font-weight: 700; color: #34D399;")
        btn_regen = QPushButton(loc.t("script.btn_regen_scene"))
        btn_regen.setObjectName("SecondaryBtn")
        btn_regen.clicked.connect(lambda: self.regenerate_requested.emit(scene.id))
        head.addWidget(lbl, 1)
        head.addWidget(btn_regen)
        layout.addLayout(head)

        layout.addWidget(QLabel(loc.t("script.narration_label")))
        self.narration_edit = QPlainTextEdit(scene.narration)
        self.narration_edit.setMinimumHeight(76)
        layout.addWidget(self.narration_edit)

        layout.addWidget(QLabel(loc.t("script.visual_prompt_label")))
        self.prompt_edit = QLineEdit(scene.visual_prompt)
        layout.addWidget(self.prompt_edit)

    def apply_changes(self) -> None:
        self.scene.narration = self.narration_edit.toPlainText().strip()
        self.scene.visual_prompt = self.prompt_edit.text().strip()
