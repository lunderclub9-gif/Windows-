"""Core domain models for DocuMaker DZ."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ProjectStatus(str, Enum):
    DRAFT = "draft"
    IN_PROGRESS = "in_progress"
    FAILED = "failed"
    COMPLETED = "completed"


class PipelineStep(int, Enum):
    RESEARCH = 1
    SCRIPT = 2
    SCENES = 3
    VOICE = 4
    VISUALS = 5
    MUSIC = 6
    SUBTITLES = 7
    ASSEMBLY = 8
    EXPORT = 9


@dataclass
class MediaCandidate:
    provider: str
    media_type: str  # "image" | "video"
    media_id: str
    url: str
    download_url: str
    thumbnail_url: str = ""
    width: int = 0
    height: int = 0
    duration: float = 0.0
    license_name: str = "Pexels License"
    attribution: str = ""
    source_page: str = ""
    local_path: str = ""
    score: float = 0.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MediaCandidate":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class WordTiming:
    text: str
    start_sec: float
    end_sec: float

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "WordTiming":
        return cls(
            text=str(data.get("text", "")),
            start_sec=float(data.get("start_sec", 0.0)),
            end_sec=float(data.get("end_sec", 0.0)),
        )


@dataclass
class Scene:
    id: int
    title: str = ""
    narration: str = ""
    visual_prompt: str = ""
    search_keywords: list[str] = field(default_factory=list)
    visual_type: str = "stock_video_or_image"
    estimated_duration_seconds: float = 12.0
    actual_audio_duration: float = 0.0
    padding_seconds: float = 0.8
    music_mood: str = "calm_historical"
    transition: str = "slow_fade"
    ken_burns: str = "zoom_in"  # zoom_in | zoom_out | pan_left | pan_right | none
    text_overlay: str = ""
    sources: list[str] = field(default_factory=list)
    audio_path: str = ""
    word_timings: list[WordTiming] = field(default_factory=list)
    candidates: list[MediaCandidate] = field(default_factory=list)
    selected_media: MediaCandidate | None = None

    @property
    def scene_duration(self) -> float:
        base = self.actual_audio_duration if self.actual_audio_duration > 0 else self.estimated_duration_seconds
        return max(3.0, base + self.padding_seconds)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "narration": self.narration,
            "visual_prompt": self.visual_prompt,
            "search_keywords": self.search_keywords,
            "visual_type": self.visual_type,
            "estimated_duration_seconds": self.estimated_duration_seconds,
            "actual_audio_duration": self.actual_audio_duration,
            "padding_seconds": self.padding_seconds,
            "music_mood": self.music_mood,
            "transition": self.transition,
            "ken_burns": self.ken_burns,
            "text_overlay": self.text_overlay,
            "sources": self.sources,
            "audio_path": self.audio_path,
            "word_timings": [asdict(w) for w in self.word_timings],
            "candidates": [asdict(c) for c in self.candidates],
            "selected_media": asdict(self.selected_media) if self.selected_media else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Scene":
        timings = [WordTiming.from_dict(w) for w in data.get("word_timings", [])]
        cands = [MediaCandidate.from_dict(c) for c in data.get("candidates", [])]
        sel_raw = data.get("selected_media")
        sel = MediaCandidate.from_dict(sel_raw) if isinstance(sel_raw, dict) else None
        return cls(
            id=int(data.get("id", 1)),
            title=str(data.get("title", "")),
            narration=str(data.get("narration", "")),
            visual_prompt=str(data.get("visual_prompt", "")),
            search_keywords=list(data.get("search_keywords", [])),
            visual_type=str(data.get("visual_type", "stock_video_or_image")),
            estimated_duration_seconds=float(data.get("estimated_duration_seconds", 12.0)),
            actual_audio_duration=float(data.get("actual_audio_duration", 0.0)),
            padding_seconds=float(data.get("padding_seconds", 0.8)),
            music_mood=str(data.get("music_mood", "calm_historical")),
            transition=str(data.get("transition", "slow_fade")),
            ken_burns=str(data.get("ken_burns", "zoom_in")),
            text_overlay=str(data.get("text_overlay", "")),
            sources=list(data.get("sources", [])),
            audio_path=str(data.get("audio_path", "")),
            word_timings=timings,
            candidates=cands,
            selected_media=sel,
        )


@dataclass
class ResearchData:
    summary: str = ""
    key_facts: list[str] = field(default_factory=list)
    timeline: list[str] = field(default_factory=list)
    entities: list[str] = field(default_factory=list)
    sources: list[dict[str, str]] = field(default_factory=list)  # [{title, url}]
    warnings: list[str] = field(default_factory=list)
    sensitive_topics: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ResearchData":
        return cls(
            summary=str(data.get("summary", "")),
            key_facts=list(data.get("key_facts", [])),
            timeline=list(data.get("timeline", [])),
            entities=list(data.get("entities", [])),
            sources=list(data.get("sources", [])),
            warnings=list(data.get("warnings", [])),
            sensitive_topics=list(data.get("sensitive_topics", [])),
        )


@dataclass
class CreativePlan:
    language: str = "ar"
    voice_gender: str = "male"
    voice_style: str = "deep_documentary"
    voice_pace: str = "slow"
    voice_emotion: str = "calm"
    music_style: str = "cinematic_oriental_ambient"
    music_mood: str = "calm"
    music_energy: str = "low"
    instrumentation: list[str] = field(default_factory=lambda: ["oud", "strings", "ambient_pad"])
    visual_style: str = "historical_documentary"
    color_grade: str = "warm_earthy"
    pacing: str = "slow"
    target_duration_seconds: int = 180

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CreativePlan":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class MusicConfig:
    mode: str = "auto"  # auto | manual
    provider: str = "pixabay"  # pixabay | local | synthetic_ambient
    track_title: str = ""
    track_path: str = ""
    license_name: str = "Pixabay Content License"
    attribution: str = ""
    volume: float = 0.22
    ducking_enabled: bool = True
    fade_in_seconds: float = 2.0
    fade_out_seconds: float = 3.0

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MusicConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class VoiceConfig:
    mode: str = "auto"  # auto | manual
    provider: str = "edge_tts"  # edge_tts | elevenlabs
    voice_id: str = "ar-SA-HamedNeural"
    rate: str = "+0%"
    pitch: str = "+0Hz"
    volume: str = "+0%"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "VoiceConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Project:
    project_id: str
    title: str
    folder_path: str
    language: str = "ar"
    target_minutes: int = 3
    extra_instructions: str = ""
    content_type: str = "documentary"
    audience: str = "general"
    tone: str = "calm"
    visual_mode: str = "stock"
    resolution: str = "720p"
    burn_subtitles: bool = True
    ken_burns_enabled: bool = True
    ai_disclosure: bool = False
    status: str = ProjectStatus.DRAFT.value
    completed_step: int = 0
    failed_step: int | None = None
    last_error: str = ""
    script_approved: bool = False
    created_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    total_duration_seconds: float = 0.0
    thumbnail_path: str = ""
    output_video_path: str = ""
    subtitle_srt_path: str = ""
    subtitle_ass_path: str = ""
    hook: str = ""
    full_script_markdown: str = ""
    creative_plan: CreativePlan = field(default_factory=CreativePlan)
    research: ResearchData = field(default_factory=ResearchData)
    voice_config: VoiceConfig = field(default_factory=VoiceConfig)
    music_config: MusicConfig = field(default_factory=MusicConfig)
    scenes: list[Scene] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_id": self.project_id,
            "title": self.title,
            "folder_path": self.folder_path,
            "language": self.language,
            "target_minutes": self.target_minutes,
            "extra_instructions": self.extra_instructions,
            "content_type": self.content_type,
            "audience": self.audience,
            "tone": self.tone,
            "visual_mode": self.visual_mode,
            "resolution": self.resolution,
            "burn_subtitles": self.burn_subtitles,
            "ken_burns_enabled": self.ken_burns_enabled,
            "ai_disclosure": self.ai_disclosure,
            "status": self.status,
            "completed_step": self.completed_step,
            "failed_step": self.failed_step,
            "last_error": self.last_error,
            "script_approved": self.script_approved,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "total_duration_seconds": self.total_duration_seconds,
            "thumbnail_path": self.thumbnail_path,
            "output_video_path": self.output_video_path,
            "subtitle_srt_path": self.subtitle_srt_path,
            "subtitle_ass_path": self.subtitle_ass_path,
            "hook": self.hook,
            "full_script_markdown": self.full_script_markdown,
            "creative_plan": asdict(self.creative_plan),
            "research": asdict(self.research),
            "voice_config": asdict(self.voice_config),
            "music_config": asdict(self.music_config),
            "scenes": [s.to_dict() for s in self.scenes],
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Project":
        return cls(
            project_id=str(data["project_id"]),
            title=str(data["title"]),
            folder_path=str(data["folder_path"]),
            language=str(data.get("language", "ar")),
            target_minutes=int(data.get("target_minutes", 3)),
            extra_instructions=str(data.get("extra_instructions", "")),
            content_type=str(data.get("content_type", "documentary")),
            audience=str(data.get("audience", "general")),
            tone=str(data.get("tone", "calm")),
            visual_mode=str(data.get("visual_mode", "stock")),
            resolution=str(data.get("resolution", "720p")),
            burn_subtitles=bool(data.get("burn_subtitles", True)),
            ken_burns_enabled=bool(data.get("ken_burns_enabled", True)),
            ai_disclosure=bool(data.get("ai_disclosure", False)),
            status=str(data.get("status", ProjectStatus.DRAFT.value)),
            completed_step=int(data.get("completed_step", 0)),
            failed_step=data.get("failed_step"),
            last_error=str(data.get("last_error", "")),
            script_approved=bool(data.get("script_approved", False)),
            created_at=str(data.get("created_at", "")),
            updated_at=str(data.get("updated_at", "")),
            total_duration_seconds=float(data.get("total_duration_seconds", 0.0)),
            thumbnail_path=str(data.get("thumbnail_path", "")),
            output_video_path=str(data.get("output_video_path", "")),
            subtitle_srt_path=str(data.get("subtitle_srt_path", "")),
            subtitle_ass_path=str(data.get("subtitle_ass_path", "")),
            hook=str(data.get("hook", "")),
            full_script_markdown=str(data.get("full_script_markdown", "")),
            creative_plan=CreativePlan.from_dict(data.get("creative_plan", {})),
            research=ResearchData.from_dict(data.get("research", {})),
            voice_config=VoiceConfig.from_dict(data.get("voice_config", {})),
            music_config=MusicConfig.from_dict(data.get("music_config", {})),
            scenes=[Scene.from_dict(s) for s in data.get("scenes", [])],
        )


@dataclass
class AppConfig:
    ui_language: str = "ar"
    projects_dir: str = ""
    active_ai_provider: str = "gemini"  # gemini | openai | groq | openrouter
    active_tts_provider: str = "edge_tts"  # edge_tts | elevenlabs
    active_media_provider: str = "pexels"
    active_music_provider: str = "pixabay"
    default_resolution: str = "720p"
    burn_subtitles: bool = True
    ken_burns_enabled: bool = True
    ai_disclosure_default: bool = False
    gemini_model: str = "gemini-2.5-flash"
    openai_model: str = "gpt-4o-mini"
    groq_model: str = "llama-3.3-70b-versatile"
    openrouter_model: str = "google/gemini-2.5-flash"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AppConfig":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
