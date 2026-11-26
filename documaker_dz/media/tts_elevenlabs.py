"""Optional premium ElevenLabs TTS provider."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from pathlib import Path

from ..core.errors import DocuMakerError
from ..core.http_client import HttpNetworkError, request_json
from ..production.ffmpeg_utils import probe_duration
from .base import TTSProvider, TTSResult, VoiceInfo


class ElevenLabsTTSProvider(TTSProvider):
    name = "elevenlabs"
    supports_free_tier = False

    DEFAULT_VOICES = [
        VoiceInfo("21m00Tcm4TlvDq8ikWAM", "Rachel — Multilingual Documentary", "en", "female", "elevenlabs"),
        VoiceInfo("pNInz6obpgDQGcFmaJgB", "Adam — Deep Documentary", "en", "male", "elevenlabs"),
    ]

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key.strip()

    def list_voices(self, language: str | None = None) -> list[VoiceInfo]:
        return list(self.DEFAULT_VOICES)

    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice_id: str = "pNInz6obpgDQGcFmaJgB",
        rate: str = "+0%",
        pitch: str = "+0Hz",
        volume: str = "+0%",
    ) -> TTSResult:
        if not self.api_key:
            raise DocuMakerError("err.tts_failed", "Missing ElevenLabs API key", scene=0)
        url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "audio/mpeg",
        }
        payload = {"text": text, "model_id": "eleven_multilingual_v2"}
        output_path.parent.mkdir(parents=True, exist_ok=True)
        try:
            import httpx  # type: ignore

            with httpx.Client(timeout=60.0) as client:
                resp = client.post(url, headers=headers, json=payload)
            if resp.status_code >= 400:
                raise DocuMakerError("err.tts_failed", f"ElevenLabs HTTP {resp.status_code}", scene=0)
            output_path.write_bytes(resp.content)
        except ImportError:
            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            try:
                with urllib.request.urlopen(req, timeout=60.0) as resp:
                    output_path.write_bytes(resp.read())
            except urllib.error.HTTPError as exc:
                raise DocuMakerError("err.tts_failed", f"ElevenLabs HTTP {exc.code}", scene=0) from exc
            except urllib.error.URLError as exc:
                raise DocuMakerError("err.no_internet", str(exc.reason)) from exc

        dur = probe_duration(output_path)
        return TTSResult(audio_path=output_path, duration_seconds=dur, word_timings=[])

    def test_connection(self) -> tuple[bool, str]:
        if not self.api_key:
            return False, "Missing API key"
        try:
            resp = request_json(
                "GET",
                "https://api.elevenlabs.io/v1/user",
                headers={"xi-api-key": self.api_key},
                timeout=15.0,
            )
            return resp.status_code == 200, f"HTTP {resp.status_code}"
        except HttpNetworkError as exc:
            return False, str(exc)
