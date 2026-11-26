"""Abstract AI Provider interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any


class AIProvider(ABC):
    name: str = "base"
    display_name: str = "Base AI"
    supports_free_tier: bool = True

    @abstractmethod
    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.5) -> str:
        raise NotImplementedError

    @abstractmethod
    def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    def test_connection(self) -> tuple[bool, str]:
        raise NotImplementedError
