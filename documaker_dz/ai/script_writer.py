"""Script Writer: produces an original documentary script suitable for TTS narration."""

from __future__ import annotations

from ..core.models import Project
from .base import AIProvider


class ScriptWriter:
    WORDS_PER_MINUTE = {
        "ar": 125,
        "fr": 140,
        "en": 145,
    }

    def run(self, ai: AIProvider, project: Project) -> dict[str, str]:
        wpm = self.WORDS_PER_MINUTE.get(project.language, 135)
        target_words = max(250, project.target_minutes * wpm)
        lang_instruction = (
            "Write in natural, eloquent Modern Standard Arabic (فصحى معاصرة واضحة), "
            "with clean sentence rhythm suited for TTS narration, accurate Arabic spelling of places/names, "
            "and NO awkward literal translations."
            if project.language == "ar"
            else f"Write in natural, engaging {project.language} suited for documentary voice-over."
        )

        system_prompt = (
            "You are an award-winning documentary scriptwriter. "
            "Write an ORIGINAL script grounded strictly in the provided research brief. "
            f"{lang_instruction} "
            "Structure: 1) Compelling 5-10s Hook, 2) Introduction, 3) Logical thematic sections, "
            "4) Smooth natural transitions, 5) Memorable conclusion & call-to-action. "
            "Return valid JSON only."
        )
        facts_text = "\n".join(f"- {f}" for f in project.research.key_facts[:14])
        timeline_text = "\n".join(f"- {t}" for t in project.research.timeline[:10])
        user_prompt = (
            f"Title: {project.title}\n"
            f"Target duration: {project.target_minutes} minutes (~{target_words} words)\n"
            f"Audience: {project.audience} | Tone: {project.tone} | Type: {project.content_type}\n"
            f"Extra instructions: {project.extra_instructions or 'None'}\n\n"
            f"Research summary:\n{project.research.summary}\n\n"
            f"Key facts:\n{facts_text}\n\n"
            f"Timeline:\n{timeline_text}\n\n"
            "Return JSON:\n"
            "{\n"
            '  "hook": "5-10 second opening hook",\n'
            '  "full_script_markdown": "Complete documentary narration script organized into clear sections with headings"\n'
            "}"
        )
        data = ai.generate_json(system_prompt, user_prompt, temperature=0.55)
        return {
            "hook": str(data.get("hook", "")).strip(),
            "full_script_markdown": str(data.get("full_script_markdown", "")).strip(),
        }
