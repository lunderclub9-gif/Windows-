"""Scene Planner: converts a documentary script into structured, timed scenes with English stock keywords."""

from __future__ import annotations

from ..core.models import Project, Scene
from .base import AIProvider


class ScenePlanner:
    def run(self, ai: AIProvider, project: Project) -> list[Scene]:
        target_seconds = project.target_minutes * 60
        expected_scenes = max(6, min(28, round(target_seconds / 15)))
        source_urls = [s.get("url", "") for s in project.research.sources if s.get("url")]

        system_prompt = (
            "You are a documentary storyboard & scene planner. "
            "Break the full script into cohesive scenes where each scene has narration (in the script's language), "
            "an English visual_prompt, and 2-4 concise English search_keywords optimized for Pexels stock video/photo search "
            "(even if the narration is Arabic or French, search_keywords MUST be in clear English!). "
            "Ensure total estimated_duration_seconds approximates the target duration. "
            "Return valid JSON only."
        )
        user_prompt = (
            f"Title: {project.title}\n"
            f"Language: {project.language}\n"
            f"Target total duration: {target_seconds} seconds (~{expected_scenes} scenes)\n"
            f"Visual style: {project.creative_plan.visual_style}\n"
            f"Available sources: {source_urls[:5]}\n\n"
            f"Full script:\n{project.full_script_markdown}\n\n"
            "Return JSON:\n"
            "{\n"
            '  "scenes": [\n'
            "    {\n"
            '      "id": 1,\n'
            '      "title": "Short scene title",\n'
            '      "narration": "Exact narration spoken in this scene (keep full script intact across scenes)",\n'
            '      "visual_prompt": "Detailed cinematic English visual description",\n'
            '      "search_keywords": ["keyword one", "keyword two"],\n'
            '      "visual_type": "stock_video_or_image",\n'
            '      "estimated_duration_seconds": 14,\n'
            '      "music_mood": "calm_historical",\n'
            '      "transition": "slow_fade",\n'
            '      "ken_burns": "zoom_in",\n'
            '      "text_overlay": "",\n'
            '      "sources": ["https://..."]\n'
            "    }\n"
            "  ]\n"
            "}"
        )
        data = ai.generate_json(system_prompt, user_prompt, temperature=0.3)
        raw_scenes = data.get("scenes", [])
        scenes: list[Scene] = []
        kb_cycle = ["zoom_in", "pan_right", "zoom_out", "pan_left"]
        for idx, item in enumerate(raw_scenes, start=1):
            if not isinstance(item, dict):
                continue
            narration = str(item.get("narration", "")).strip()
            if not narration:
                continue
            item["id"] = idx
            if not item.get("ken_burns"):
                item["ken_burns"] = kb_cycle[(idx - 1) % len(kb_cycle)]
            if not item.get("sources") and source_urls:
                item["sources"] = source_urls[:2]
            scenes.append(Scene.from_dict(item))
        return scenes

    def regenerate_single_scene(self, ai: AIProvider, project: Project, scene: Scene, instruction: str = "") -> Scene:
        system_prompt = (
            "You are a documentary editor refining a single scene's narration and English stock search keywords. "
            "Preserve factual accuracy and keep the narration natural for TTS. Return valid JSON only."
        )
        user_prompt = (
            f"Documentary: {project.title} ({project.language})\n"
            f"Current narration: {scene.narration}\n"
            f"Current visual prompt: {scene.visual_prompt}\n"
            f"User instruction: {instruction or 'Improve clarity, rhythm, and visual description.'}\n\n"
            "Return JSON with keys: narration, visual_prompt, search_keywords (list of English keywords)."
        )
        data = ai.generate_json(system_prompt, user_prompt, temperature=0.4)
        scene.narration = str(data.get("narration", scene.narration)).strip()
        scene.visual_prompt = str(data.get("visual_prompt", scene.visual_prompt)).strip()
        kws = data.get("search_keywords")
        if isinstance(kws, list) and kws:
            scene.search_keywords = [str(k) for k in kws]
        return scene
