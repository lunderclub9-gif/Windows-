"""Desktop application entry point for DocuMaker DZ (no terminal window)."""

from __future__ import annotations

import sys
from pathlib import Path

# Support both `python -m documaker_dz.main` and PyInstaller direct script execution
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtWidgets import QApplication, QMessageBox

from documaker_dz.core.logger import setup_logger
from documaker_dz.core.project_manager import ProjectManager
from documaker_dz.core.settings_manager import SettingsManager
from documaker_dz.localization.manager import LocalizationManager
from documaker_dz.ui.main_window import MainWindow


def main() -> int:
    logger = setup_logger("documaker.app")
    app = QApplication(sys.argv)
    app.setApplicationName("DocuMaker DZ")
    app.setOrganizationName("DocuMakerDZ")

    settings = SettingsManager()
    loc = LocalizationManager(settings.config.ui_language)
    project_manager = ProjectManager(settings)

    def _excepthook(exc_type, exc_value, exc_tb) -> None:
        logger.critical("Unhandled UI exception", exc_info=(exc_type, exc_value, exc_tb))
        QMessageBox.critical(None, loc.t("app.title"), loc.t("err.generic"))

    sys.excepthook = _excepthook

    window = MainWindow(settings=settings, project_manager=project_manager, loc=loc)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
