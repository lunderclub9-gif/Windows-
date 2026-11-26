"""Creative Director module: decides voice, music, visual style, and pacing without inventing facts."""

from __future__ import annotations

from ..core.models import CreativePlan, Project
from .base import AIProvider


class CreativeDirector:
    DEFAULT_VOICES = {
        "ar": {"male": "ar-SA-HamedNeural", "female": "ar-SA-ZariyahNeural"},
        "fr": {"male": "fr-FR-HenriNeural", "female": "fr-FR-DeniseNeural"},
        "en": {"male": "en-US-AndrewNeural", "female": "en-US-AriaNeural"},
        "es": {"male": "es-ES-AlvaroNeural", "female": "es-ES-ElviraNeural"},
        "tr": {"male": "tr-TR-AhmetNeural", "female": "tr-TR-EmelNeural"},
        "de": {"male": "de-DE-ConradNeural", "female": "de-DE-KatjaNeural"},
    }

    def create_plan(self, ai: AIProvider, project: Project) -> CreativePlan:
        system_prompt = (
            "You are the Creative Director of a documentary production studio. "
            "Your ONLY job is to decide presentation style (voice, music, pacing, color grade, visual style). "
            "Do NOT invent factual claims. Return a single JSON object."
        )
        user_prompt = (
            f"Topic: {project.title}\n"
            f"Language: {project.language}\n"
            f"Content type: {project.content_type}\n"
            f"Audience: {project.audience}\n"
            f"Requested tone: {project.tone}\n"
            f"Target duration seconds: {project.target_minutes * 60}\n\n"
            "Return JSON with keys:\n"
            "{\n"
            '  "language": "ar|fr|en",\n'
            '  "voice_gender": "male|female",\n'
            '  "voice_style": "deep_documentary|clear_narrator|energetic|suspenseful",\n'
            '  "voice_pace": "slow|medium|brisk",\n'
            '  "voice_emotion": "calm|dramatic|curious|inspiring|mysterious",\n'
            '  "music_style": "cinematic_oriental_ambient|calm_historical|orchestral|piano|modern_tech|dark_ambient",\n'
            '  "music_mood": "calm|mysterious|inspiring|dramatic",\n'
            '  "music_energy": "low|medium",\n'
            '  "instrumentation": ["oud", "strings", "ambient_pad"],\n'
            '  "visual_style": "historical_documentary|science_modern|travel_cinematic|mystery_dark",\n'
            '  "color_grade": "warm_earthy|cool_clean|high_contrast|natural",\n'
            '  "pacing": "slow|medium",\n'
            f'  "target_duration_seconds": {project.target_minutes * 60}\n'
            "}"
        )
        data = ai.generate_json(system_prompt, user_prompt, temperature=0.3)
        data["language"] = project.language
        data["target_duration_seconds"] = project.target_minutes * 60
        return CreativePlan.from_dict(data)

    @classmethod
    def recommend_voice_id(cls, language: str, gender: str = "male") -> str:
        lang_map = cls.DEFAULT_VOICES.get(language, cls.DEFAULT_VOICES["ar"])
        return lang_map.get(gender, lang_map["male"])
