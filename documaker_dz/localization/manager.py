"""Localization manager supporting Arabic (default RTL), French, and English."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


def get_resource_path(relative_path: str) -> Path:
    """Resolve resource path both in source tree and PyInstaller onefile bundle."""
    base = getattr(sys, "_MEIPASS", None)
    if base:
        return Path(base) / relative_path
    return Path(__file__).resolve().parent.parent / relative_path


class LocalizationManager:
    SUPPORTED_LANGUAGES = ("ar", "fr", "en")

    def __init__(self, language: str = "ar") -> None:
        self._translations: dict[str, dict[str, Any]] = {}
        self._language = "ar"
        self._load_all()
        self.set_language(language)

    def _load_all(self) -> None:
        loc_dir = get_resource_path("localization")
        for lang in self.SUPPORTED_LANGUAGES:
            path = loc_dir / f"{lang}.json"
            if path.exists():
                with path.open("r", encoding="utf-8") as fh:
                    self._translations[lang] = json.load(fh)
            else:
                self._translations[lang] = {}

    @property
    def language(self) -> str:
        return self._language

    @property
    def is_rtl(self) -> bool:
        return bool(self._translations.get(self._language, {}).get("app.rtl", self._language == "ar"))

    def set_language(self, language: str) -> None:
        if language in self.SUPPORTED_LANGUAGES:
            self._language = language
        else:
            self._language = "ar"

    def t(self, key: str, **kwargs: Any) -> str:
        lang_map = self._translations.get(self._language, {})
        text = lang_map.get(key)
        if text is None:
            text = self._translations.get("ar", {}).get(key, key)
        if not isinstance(text, str):
            return str(text)
        if kwargs:
            try:
                return text.format(**kwargs)
            except Exception:
                return text
        return text

    @staticmethod
    def format_duration_mmss(seconds: float) -> str:
        total = max(0, int(round(seconds)))
        mins, secs = divmod(total, 60)
        return f"{mins:02d}:{secs:02d}"
