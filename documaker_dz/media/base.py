"""Abstract Media Service Provider interfaces."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

from ..core.models import MediaCandidate, WordTiming


@dataclass
class VoiceInfo:
    voice_id: str
    display_name: str
    language: str
    gender: str
    provider: str


@dataclass
class TTSResult:
    audio_path: Path
    duration_seconds: float
    word_timings: list[WordTiming]


class TTSProvider(ABC):
    name: str = "base_tts"
    supports_free_tier: bool = True

    @abstractmethod
    def list_voices(self, language: str | None = None) -> list[VoiceInfo]:
        raise NotImplementedError

    @abstractmethod
    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice_id: str,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        volume: str = "+0%",
    ) -> TTSResult:
        raise NotImplementedError


class ImageProvider(ABC):
    name: str = "base_image"

    @abstractmethod
    def search_images(self, query: str, per_page: int = 5) -> list[MediaCandidate]:
        raise NotImplementedError


class VideoProvider(ABC):
    name: str = "base_video"

    @abstractmethod
    def search_videos(self, query: str, per_page: int = 5) -> list[MediaCandidate]:
        raise NotImplementedError


class MusicProvider(ABC):
    name: str = "base_music"

    @abstractmethod
    def search_music(self, query: str, mood: str = "") -> list[dict[str, str]]:
        raise NotImplementedError


class SoundEffectProvider(ABC):
    name: str = "base_sfx"

    @abstractmethod
    def search_effects(self, query: str) -> list[dict[str, str]]:
        raise NotImplementedError


class SearchProvider(ABC):
    name: str = "base_search"

    @abstractmethod
    def search(self, query: str, limit: int = 5) -> list[MediaCandidate]:
        raise NotImplementedError
