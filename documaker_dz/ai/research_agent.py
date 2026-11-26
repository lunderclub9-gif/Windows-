"""Research Agent: collects structured facts, timeline, citations, warnings, and sensitive-topic flags."""

from __future__ import annotations

from ..core.models import Project, ResearchData
from .base import AIProvider


class ResearchAgent:
    SENSITIVE_KEYWORDS = ("politics", "religion", "war", "health", "finance", "crime")

    def run(self, ai: AIProvider, project: Project) -> ResearchData:
        lang_name = {"ar": "Arabic", "fr": "French", "en": "English"}.get(project.language, project.language)
        system_prompt = (
            "You are a rigorous documentary fact-researcher. "
            "Distinguish verified facts from speculation. Never fabricate fake URLs; "
            "provide reliable, well-known reference domains (e.g., Wikipedia, Britannica, UNESCO, academic/official portals) "
            "and explicitly flag any uncertain or disputed claims. "
            "Also classify if the topic touches sensitive areas: politics, religion, war, health, finance, crime. "
            "Return valid JSON only."
        )
        user_prompt = (
            f"Topic: {project.title}\n"
            f"Extra instructions: {project.extra_instructions or 'None'}\n"
            f"Content type: {project.content_type}\n"
            f"Output language for summary/facts/timeline/warnings: {lang_name}\n\n"
            "Return JSON object:\n"
            "{\n"
            '  "summary": "Concise factual overview in target language",\n'
            '  "key_facts": ["Fact 1", "Fact 2", ...],\n'
            '  "timeline": ["Period/Date: event", ...],\n'
            '  "entities": ["Key people, places, dates"],\n'
            '  "sources": [{"title": "Source title", "url": "https://..."}],\n'
            '  "warnings": ["Any disputed or uncertain historical/scientific claims"],\n'
            '  "sensitive_topics": ["only include from: politics, religion, war, health, finance, crime if applicable"]\n'
            "}"
        )
        data = ai.generate_json(system_prompt, user_prompt, temperature=0.2)
        research = ResearchData.from_dict(data)
        research.sensitive_topics = [
            s for s in research.sensitive_topics if s in self.SENSITIVE_KEYWORDS
        ]
        return research
