"""Settings manager for AppConfig and encrypted API keys."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from .logger import get_app_data_dir
from .models import AppConfig
from .security import SecretVault


class SettingsManager:
    PROVIDER_KEYS = (
        "gemini",
        "openai",
        "groq",
        "openrouter",
        "pexels",
        "pixabay",
        "elevenlabs",
    )

    def __init__(self, app_dir: Path | None = None) -> None:
        self.app_dir = app_dir or get_app_data_dir()
        self.config_path = self.app_dir / "config.json"
        self.cache_dir = self.app_dir / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.vault = SecretVault(self.app_dir / "api_keys.enc")
        self.config = self._load_config()
        self._api_keys = self.vault.load_keys()

    def _default_projects_dir(self) -> Path:
        p = self.app_dir / "projects"
        p.mkdir(parents=True, exist_ok=True)
        return p

    def _load_config(self) -> AppConfig:
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                cfg = AppConfig.from_dict(data)
                if cfg.gemini_model.strip() == "gemini-2.5-pro":
                    cfg.gemini_model = "gemini-3.1-pro-preview"
                    self.save_config(cfg)
                if not cfg.projects_dir:
                    cfg.projects_dir = str(self._default_projects_dir())
                return cfg
            except Exception:
                pass
        cfg = AppConfig(projects_dir=str(self._default_projects_dir()))
        self.save_config(cfg)
        return cfg

    def save_config(self, config: AppConfig | None = None) -> None:
        if config is not None:
            self.config = config
        self.app_dir.mkdir(parents=True, exist_ok=True)
        from dataclasses import asdict

        self.config_path.write_text(
            json.dumps(asdict(self.config), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def get_api_key(self, provider: str) -> str:
        return self._api_keys.get(provider, "")

    def set_api_key(self, provider: str, value: str) -> None:
        cleaned = value.strip()
        if cleaned:
            self._api_keys[provider] = cleaned
        else:
            self._api_keys.pop(provider, None)
        self.vault.save_keys(self._api_keys)

    def is_connected(self, provider: str) -> bool:
        if provider in ("edge_tts", "wikimedia", "local"):
            return True
        return bool(self.get_api_key(provider))

    def get_projects_dir(self) -> Path:
        p = Path(self.config.projects_dir) if self.config.projects_dir else self._default_projects_dir()
        p.mkdir(parents=True, exist_ok=True)
        return p

    def clear_cache(self) -> float:
        total_bytes = 0
        if self.cache_dir.exists():
            for item in self.cache_dir.rglob("*"):
                if item.is_file():
                    total_bytes += item.stat().st_size
            shutil.rmtree(self.cache_dir, ignore_errors=True)
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        return total_bytes / (1024 * 1024)
