"""Cloud AI Provider implementations (Gemini, OpenAI, Groq, OpenRouter)."""

from __future__ import annotations

import json
import re
from typing import Any

from ..core.errors import DocuMakerError
from ..core.http_client import HttpNetworkError, request_json
from .base import AIProvider


def _extract_json(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        text = text[start : end + 1]
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
        return {"data": parsed}
    except json.JSONDecodeError as exc:
        raise DocuMakerError("err.generic", f"Invalid JSON from AI provider: {exc}") from exc


def _handle_http_error(status_code: int, body: str) -> None:
    if status_code in (401, 403):
        raise DocuMakerError("err.invalid_ai_key", f"HTTP {status_code}: {body[:300]}")
    if status_code == 429:
        raise DocuMakerError("err.rate_limit", f"HTTP 429: {body[:300]}")
    if status_code >= 400:
        raise DocuMakerError("err.generic", f"HTTP {status_code}: {body[:300]}")


class GeminiProvider(AIProvider):
    name = "gemini"
    display_name = "Google Gemini"
    supports_free_tier = True

    def __init__(self, api_key: str, model: str = "gemini-2.5-flash") -> None:
        self.api_key = api_key.strip()
        self.model = model

    def _endpoint(self) -> str:
        return (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent?key={self.api_key}"
        )

    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.5) -> str:
        if not self.api_key:
            raise DocuMakerError("err.missing_ai_key", "Missing Gemini API key")
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {"temperature": temperature},
        }
        try:
            resp = request_json("POST", self._endpoint(), json_body=payload, timeout=90.0)
        except HttpNetworkError as exc:
            raise DocuMakerError("err.no_internet", str(exc)) from exc
        if resp.status_code >= 400:
            _handle_http_error(resp.status_code, resp.text)
        data = resp.json()
        try:
            return data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise DocuMakerError("err.generic", f"Unexpected Gemini response: {data}") from exc

    def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> dict[str, Any]:
        if not self.api_key:
            raise DocuMakerError("err.missing_ai_key", "Missing Gemini API key")
        payload = {
            "system_instruction": {"parts": [{"text": system_prompt}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }
        try:
            resp = request_json("POST", self._endpoint(), json_body=payload, timeout=90.0)
        except HttpNetworkError as exc:
            raise DocuMakerError("err.no_internet", str(exc)) from exc
        if resp.status_code >= 400:
            _handle_http_error(resp.status_code, resp.text)
        data = resp.json()
        try:
            raw = data["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError) as exc:
            raise DocuMakerError("err.generic", f"Unexpected Gemini JSON response: {data}") from exc
        return _extract_json(raw)

    def test_connection(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "Missing API key"
        try:
            out = self.generate_text("Reply with OK.", "Ping", temperature=0.0)
            return bool(out), "OK"
        except DocuMakerError as exc:
            return False, exc.technical_detail


class OpenAICompatibleProvider(AIProvider):
    """Base implementation for OpenAI, Groq, and OpenRouter REST APIs."""

    def __init__(
        self,
        name: str,
        display_name: str,
        base_url: str,
        api_key: str,
        model: str,
        supports_free_tier: bool = True,
        extra_headers: dict[str, str] | None = None,
    ) -> None:
        self.name = name
        self.display_name = display_name
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key.strip()
        self.model = model
        self.supports_free_tier = supports_free_tier
        self.extra_headers = extra_headers or {}

    def _chat(self, system_prompt: str, user_prompt: str, temperature: float, json_mode: bool) -> str:
        if not self.api_key:
            raise DocuMakerError("err.missing_ai_key", f"Missing {self.display_name} API key")
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            **self.extra_headers,
        }
        payload: dict[str, Any] = {
            "model": self.model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        try:
            resp = request_json("POST", f"{self.base_url}/chat/completions", headers=headers, json_body=payload, timeout=90.0)
        except HttpNetworkError as exc:
            raise DocuMakerError("err.no_internet", str(exc)) from exc
        if resp.status_code >= 400:
            _handle_http_error(resp.status_code, resp.text)
        data = resp.json()
        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError) as exc:
            raise DocuMakerError("err.generic", f"Unexpected response: {data}") from exc

    def generate_text(self, system_prompt: str, user_prompt: str, temperature: float = 0.5) -> str:
        return self._chat(system_prompt, user_prompt, temperature, json_mode=False)

    def generate_json(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> dict[str, Any]:
        raw = self._chat(system_prompt, user_prompt + "\nReturn valid JSON object only.", temperature, json_mode=True)
        return _extract_json(raw)

    def test_connection(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "Missing API key"
        try:
            out = self.generate_text("Reply with OK.", "Ping", temperature=0.0)
            return bool(out), "OK"
        except DocuMakerError as exc:
            return False, exc.technical_detail


def build_ai_provider(provider_name: str, api_key: str, model: str | None = None) -> AIProvider:
    if provider_name == "gemini":
        return GeminiProvider(api_key=api_key, model=model or "gemini-2.5-flash")
    if provider_name == "openai":
        return OpenAICompatibleProvider(
            name="openai",
            display_name="OpenAI",
            base_url="https://api.openai.com/v1",
            api_key=api_key,
            model=model or "gpt-4o-mini",
            supports_free_tier=False,
        )
    if provider_name == "groq":
        return OpenAICompatibleProvider(
            name="groq",
            display_name="Groq",
            base_url="https://api.groq.com/openai/v1",
            api_key=api_key,
            model=model or "llama-3.3-70b-versatile",
            supports_free_tier=True,
        )
    if provider_name == "openrouter":
        return OpenAICompatibleProvider(
            name="openrouter",
            display_name="OpenRouter",
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            model=model or "google/gemini-2.5-flash",
            supports_free_tier=True,
            extra_headers={"X-Title": "DocuMaker DZ"},
        )
    raise DocuMakerError("err.missing_ai_key", f"Unknown AI provider: {provider_name}")
