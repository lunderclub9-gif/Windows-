"""Edge-TTS free voice provider with Arabic/French/English voices and word-timing capture."""

from __future__ import annotations

import asyncio
from pathlib import Path

from ..core.errors import DocuMakerError
from ..core.models import WordTiming
from ..production.ffmpeg_utils import probe_duration
from .base import TTSProvider, TTSResult, VoiceInfo


class EdgeTTSProvider(TTSProvider):
    name = "edge_tts"
    supports_free_tier = True

    VOICES: list[VoiceInfo] = [
        VoiceInfo("ar-SA-HamedNeural", "حامد — فصحى رصينة (السعودية)", "ar", "male", "edge_tts"),
        VoiceInfo("ar-SA-ZariyahNeural", "زارية — فصحى هادئة (السعودية)", "ar", "female", "edge_tts"),
        VoiceInfo("ar-DZ-IsmaelNeural", "إسماعيل — عربية (الجزائر)", "ar", "male", "edge_tts"),
        VoiceInfo("ar-DZ-AminaNeural", "أمينة — عربية (الجزائر)", "ar", "female", "edge_tts"),
        VoiceInfo("ar-EG-ShakirNeural", "شاكر — وثائقي عميق (مصر)", "ar", "male", "edge_tts"),
        VoiceInfo("ar-EG-SalmaNeural", "سلمى — سرد واضح (مصر)", "ar", "female", "edge_tts"),
        VoiceInfo("fr-FR-HenriNeural", "Henri — Documentaire (FR)", "fr", "male", "edge_tts"),
        VoiceInfo("fr-FR-DeniseNeural", "Denise — Narration (FR)", "fr", "female", "edge_tts"),
        VoiceInfo("en-US-AndrewNeural", "Andrew — Documentary (EN)", "en", "male", "edge_tts"),
        VoiceInfo("en-US-AriaNeural", "Aria — Clear Narrator (EN)", "en", "female", "edge_tts"),
        VoiceInfo("es-ES-AlvaroNeural", "Alvaro (ES)", "es", "male", "edge_tts"),
        VoiceInfo("tr-TR-AhmetNeural", "Ahmet (TR)", "tr", "male", "edge_tts"),
        VoiceInfo("de-DE-ConradNeural", "Conrad (DE)", "de", "male", "edge_tts"),
    ]

    def list_voices(self, language: str | None = None) -> list[VoiceInfo]:
        if not language:
            return list(self.VOICES)
        return [v for v in self.VOICES if v.language == language] or list(self.VOICES)

    async def _synthesize_async(
        self,
        text: str,
        output_path: Path,
        voice_id: str,
        rate: str,
        pitch: str,
        volume: str,
    ) -> list[WordTiming]:
        import edge_tts  # type: ignore

        output_path.parent.mkdir(parents=True, exist_ok=True)
        communicate = edge_tts.Communicate(
            text=text,
            voice=voice_id,
            rate=rate,
            pitch=pitch,
            volume=volume,
        )
        timings: list[WordTiming] = []
        with output_path.open("wb") as audio_file:
            async for chunk in communicate.stream():
                ctype = chunk.get("type")
                if ctype == "audio":
                    audio_file.write(chunk["data"])
                elif ctype in ("WordBoundary", "SentenceBoundary"):
                    offset_sec = float(chunk.get("offset", 0)) / 10_000_000.0
                    dur_sec = float(chunk.get("duration", 0)) / 10_000_000.0
                    word_text = str(chunk.get("text", "")).strip()
                    if word_text:
                        timings.append(
                            WordTiming(
                                text=word_text,
                                start_sec=offset_sec,
                                end_sec=offset_sec + max(0.1, dur_sec),
                            )
                        )
        return timings

    def synthesize(
        self,
        text: str,
        output_path: Path,
        voice_id: str = "ar-SA-HamedNeural",
        rate: str = "+0%",
        pitch: str = "+0Hz",
        volume: str = "+0%",
    ) -> TTSResult:
        try:
            loop = asyncio.new_event_loop()
            try:
                timings = loop.run_until_complete(
                    self._synthesize_async(text, output_path, voice_id, rate, pitch, volume)
                )
            finally:
                loop.close()
        except ImportError as exc:
            raise DocuMakerError("err.tts_failed", f"edge-tts missing: {exc}", scene=0) from exc
        except Exception as exc:
            raise DocuMakerError("err.tts_failed", f"Edge-TTS failed: {exc}", scene=0) from exc

        if not output_path.exists() or output_path.stat().st_size < 256:
            raise DocuMakerError("err.tts_failed", "Edge-TTS produced empty audio", scene=0)

        duration = probe_duration(output_path)
        return TTSResult(audio_path=output_path, duration_seconds=duration, word_timings=timings)
