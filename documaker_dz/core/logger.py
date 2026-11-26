"""Rotating file logger for DocuMaker DZ."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path


def get_app_data_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    app_dir = base / "DocuMakerDZ"
    app_dir.mkdir(parents=True, exist_ok=True)
    return app_dir


def setup_logger(name: str = "documaker", project_log_dir: Path | None = None) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    log_dir = get_app_data_dir() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    app_handler = RotatingFileHandler(
        log_dir / "documaker.log",
        maxBytes=2 * 1024 * 1024,
        backupCount=4,
        encoding="utf-8",
    )
    app_handler.setFormatter(fmt)
    logger.addHandler(app_handler)

    if project_log_dir is not None:
        project_log_dir.mkdir(parents=True, exist_ok=True)
        proj_handler = RotatingFileHandler(
            project_log_dir / "project.log",
            maxBytes=1 * 1024 * 1024,
            backupCount=2,
            encoding="utf-8",
        )
        proj_handler.setFormatter(fmt)
        logger.addHandler(proj_handler)

    return logger
