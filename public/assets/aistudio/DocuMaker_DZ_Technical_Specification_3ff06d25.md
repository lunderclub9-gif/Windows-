# DocuMaker DZ — Technical Specification for an AI Developer

## 1. Project Overview

Build a **desktop application for Windows** called **DocuMaker DZ** (working name; the developer may propose a better product name).

The application lets a non-technical user create faceless documentary-style YouTube videos from a single topic/title.

The user should be able to:

- Open the app by double-clicking an `.exe` file.
- See a clean, modern, Arabic-first graphical interface.
- Enter a video topic, such as “The history of Béjaïa”.
- Choose language, duration, video type, voice style, and quality level.
- Connect free or paid APIs from inside the app.
- Press one button: **Create Video**.
- Watch progress updates in Arabic.
- Receive a finished MP4 video, script, audio, subtitles, and source list.
- Never need to open Command Prompt, Terminal, PowerShell, or write code.

The app must run on a low-end Windows PC with approximately **4 GB RAM**, no powerful GPU, and limited storage. Therefore, it must avoid heavy local AI video/image generation and use lightweight local processing plus cloud APIs.

## 2. Core Product Goal

Create an automated “documentary video factory”:

```text
Topic
  -> Research
  -> Script writing
  -> Scene planning
  -> Voice-over generation
  -> Visual asset selection
  -> Music selection
  -> Sound design
  -> Timing synchronization
  -> Subtitles
  -> Final MP4 export
```

The first version should produce a 3–5 minute video. Later versions may support 8–15 minute videos, series, thumbnails, YouTube metadata, and scheduled publishing.

## 3. Primary Users

### Main user

A beginner creator who wants to make educational, historical, cultural, informational, or story-based YouTube videos without editing skills.

### Requirements

- Arabic UI by default.
- French and English UI options.
- Arabic, French, English, Spanish, Turkish, German, and other major languages for script and voice-over.
- RTL support for Arabic.
- Simple error messages in the user’s language.
- No programming knowledge required.

## 4. Mandatory UX Rules

The application must be a real desktop GUI application.

It must:

- Have a desktop icon.
- Launch by double-click.
- Show no console/Terminal window.
- Run all background processes silently.
- Show clear progress states.
- Save all projects in a user-selected folder.
- Allow canceling a running job.
- Allow retrying a failed step without restarting the whole project.
- Keep API keys locally and securely.
- Work offline for local steps where possible.
- Never expose terminal commands to the user.

Use a task queue and background workers so the UI remains responsive during generation.

## 5. Application Screens

### 5.1 Home / Create Video

Fields:

- Video title.
- Optional extra instructions.
- Language: Arabic, French, English, etc.
- Target duration: 3, 5, 8, 10, or custom minutes.
- Content type: documentary, history, biography, science, travel, motivation, mystery, news explainer, etc.
- Audience: general, children, young adults, experts.
- Tone: calm, dramatic, educational, mysterious, inspiring.
- Voice mode: automatic or manual.
- Music mode: automatic or manual.
- Visual mode: stock media, AI images, mixed.
- Output resolution: 720p default; 1080p optional.
- Create Video button.

The UI must show a live progress panel:

```text
1. Researching topic...
2. Writing script...
3. Planning scenes...
4. Generating voice-over...
5. Finding images and videos...
6. Selecting music...
7. Creating subtitles...
8. Assembling video...
9. Exporting final MP4...
```

### 5.2 Project Library

Show all previous projects with:

- Title.
- Creation date.
- Status: draft, failed, completed.
- Duration.
- Thumbnail.
- Buttons: open folder, regenerate, edit script, export, delete.

### 5.3 Script Editor

Allow the user to:

- View the generated script.
- Edit text manually.
- Regenerate a section.
- Approve the script before production.
- See scene-by-scene visual prompts.
- See estimated duration per scene.

This is important: automatic generation should never be fully blind. The user should be able to review and correct facts before rendering.

### 5.4 Voice Studio

Allow the user to:

- Choose automatic voice selection.
- Choose a specific voice.
- Preview a sample sentence.
- Adjust speed, pitch, emotion, pauses, and volume.
- Regenerate individual scenes.
- Choose between free and premium voice providers.

### 5.5 Music and Sound Studio

Allow the user to:

- Let AI choose music automatically.
- Search a music library.
- Upload their own music.
- Set music volume.
- Enable audio ducking under narration.
- Add fade-in and fade-out.
- Add optional sound effects.
- Preview the final audio mix.

### 5.6 Visual Studio

Allow the user to:

- Choose stock images, stock videos, AI images, or mixed visuals.
- Search and replace individual scene visuals.
- Preview each scene.
- Apply Ken Burns motion: slow zoom, pan, or subtle movement.
- Add text overlays and scene titles.
- Choose transition style.

### 5.7 Settings / API Connections

Tabs:

```text
AI Provider
Voices
Music
Images / Video
Languages
Output
Account
```

Each provider must have:

- Name.
- Status: connected / not connected.
- API key field.
- Test connection button.
- Free-tier indicator.
- Usage/cost estimate when available.
- Secure local storage.

The user must be able to connect or disconnect providers without editing configuration files.

## 6. Recommended Technology Stack

Use a lightweight, maintainable stack suitable for low-end Windows machines.

### Recommended stack

- Language: Python 3.11 or newer.
- GUI: PySide6 or CustomTkinter.
- Background jobs: `concurrent.futures`, `threading`, or `asyncio`.
- HTTP requests: `httpx` or `requests`.
- Configuration: local JSON or SQLite.
- Database: SQLite.
- Media processing: FFmpeg.
- Audio processing: `pydub` or direct FFmpeg filters.
- Subtitles: generate `.srt` and optionally burn subtitles into video.
- Packaging: PyInstaller.
- Logging: rotating log files.
- Error reporting: user-friendly Arabic messages, with technical details stored in logs.

### Why this stack

Python is suitable for automation, APIs, media processing, and rapid development. PySide6 provides a professional desktop interface. FFmpeg is efficient for assembling images, audio, subtitles, transitions, and final MP4 output.

PyInstaller supports `--onefile`, `--windowed`/`--noconsole`, and custom icons, allowing the developer to produce a Windows executable that opens without a console window. [web:16][web:17][web:18]

## 7. System Architecture

```text
DocuMaker DZ Desktop App
├── UI Layer
│   ├── Home screen
│   ├── Script editor
│   ├── Voice studio
│   ├── Music studio
│   ├── Visual studio
│   ├── Settings
│   └── Project library
│
├── Application Layer
│   ├── Project manager
│   ├── Job queue
│   ├── Settings manager
│   ├── Error handler
│   └── Localization manager
│
├── AI Services Layer
│   ├── Research agent
│   ├── Script writer
│   ├── Scene planner
│   ├── Voice selector
│   ├── Music selector
│   ├── Visual prompt generator
│   └── Quality reviewer
│
├── Media Services Layer
│   ├── TTS providers
│   ├── Stock media providers
│   ├── AI image providers
│   ├── Music providers
│   └── Sound-effect providers
│
└── Production Layer
    ├── Audio normalizer
    ├── Subtitle generator
    ├── Scene renderer
    ├── Audio/video synchronizer
    ├── Music mixer
    ├── FFmpeg renderer
    └── Export manager
```

## 8. Video Generation Pipeline

### Step 1 — Topic intake

Accept:

- Title.
- Optional description.
- Language.
- Duration.
- Tone.
- Audience.
- Content type.

Validate input and create a project folder:

```text
Projects/
  2026-11-26_history-of-bejaia/
    project.json
    research/
    script/
    audio/
    visuals/
    music/
    subtitles/
    output/
    logs/
```

### Step 2 — Research

Use the selected AI provider to produce:

- A research brief.
- Key facts.
- Timeline or structure.
- Important names, dates, places, and definitions.
- Sources with URLs.
- Warnings about uncertain or disputed claims.

The app must save sources and show them in the script editor.

Important rule: the system must distinguish verified facts from generated speculation. It should prefer reliable sources and include citations in the research document.

### Step 3 — Script writing

Generate a documentary script with:

- Hook in the first 5–10 seconds.
- Clear introduction.
- Logical sections.
- Scene-by-scene narration.
- Natural transitions.
- Conclusion and call to action.
- Estimated spoken duration.
- Source references.

The script must be original, not copied from websites.

For Arabic, ensure:

- Proper Modern Standard Arabic.
- Natural sentence rhythm.
- Correct handling of names and places.
- No awkward literal translations.
- Suitable pacing for TTS.

### Step 4 — Scene planning

Convert the script into a structured JSON format:

```json
{
  "project_id": "abc123",
  "language": "ar",
  "title": "تاريخ مدينة بجاية",
  "scenes": [
    {
      "id": 1,
      "narration": "تقع مدينة بجاية على ساحل البحر المتوسط...",
      "visual_prompt": "Aerial view of Béjaïa, Mediterranean coast, historical city, cinematic documentary",
      "visual_type": "stock_video_or_image",
      "estimated_duration_seconds": 12,
      "music_mood": "calm_historical",
      "transition": "slow_fade",
      "sources": ["https://example.com/source"]
    }
  ]
}
```

Each scene must contain:

- Narration.
- Visual description.
- Search keywords for stock media.
- Optional AI-image prompt.
- Estimated duration.
- Music mood.
- Transition.
- Source references.

### Step 5 — Voice generation

Generate narration per scene, not as one huge audio file.

This enables:

- Better synchronization.
- Easier regeneration.
- Lower memory use.
- Per-scene timing control.

For each scene:

1. Generate audio.
2. Measure exact duration.
3. Normalize loudness.
4. Save WAV/MP3.
5. Generate word-level or sentence-level timing data.

The exact audio duration must become the master timing reference for the visual scene.

### Step 6 — Visual asset selection

Use stock APIs first because they are fast, legal, and lightweight.

Recommended providers:

- Pexels: free API for photos and videos. [web:27][web:28][web:30]
- Pixabay: images, videos, and music.
- Wikimedia Commons: useful for historical/public-domain material, with license checking.
- User-uploaded media.

For each scene:

1. Use the visual prompt and keywords.
2. Search stock libraries.
3. Download 2–4 candidates.
4. Score relevance, resolution, orientation, and license.
5. Let the user replace unsuitable visuals.
6. Cache downloads to avoid repeated API calls.

If AI image generation is enabled, use a cloud provider. Do not run local image-generation models on a 4 GB RAM machine.

### Step 7 — Music selection

The AI must analyze:

- Topic.
- Language.
- Emotional tone.
- Scene structure.
- Target audience.
- Video duration.

Then choose a music direction such as:

- Calm historical ambient.
- Cinematic orchestral.
- Oriental/Andalusian-inspired instrumental.
- Mysterious documentary.
- Emotional piano.
- Inspiring corporate.
- Modern tech electronic.

The app must support:

- Free music libraries.
- User-uploaded music.
- AI-generated music through an API.
- Automatic music trimming and looping.
- Fade-in and fade-out.
- Ducking under narration.

ElevenLabs provides APIs for voice, music, sound effects, dubbing, and transcription, which makes it a strong optional premium provider for higher-quality output. [web:32][web:35][web:36]

### Step 8 — Sound design

Optional but valuable:

- Ambient background sounds.
- Transition whooshes.
- Subtle historical/environmental effects.
- Intro/outro sound.

The AI should choose effects only when they improve the story. Avoid excessive effects.

ElevenLabs offers a Sound Effects API that turns text descriptions into sound effects with control over timing, style, and complexity. [web:31][web:33][web:40]

### Step 9 — Synchronization

This is a core feature.

For every scene:

```text
audio_duration = measured narration length
scene_duration = audio_duration + padding
```

Rules:

- The visual must last at least as long as the narration.
- Add 0.5–1.5 seconds of padding between scenes.
- Use slow zoom or pan to avoid static images.
- Match visual changes to sentence boundaries when possible.
- Fade music down when narration begins.
- Fade music up during pauses or transitions.
- Add fade-out at the end.

The final timeline must be generated as a JSON storyboard before rendering.

### Step 10 — Subtitles

Generate subtitles from the narration.

Options:

- Soft subtitles: `.srt` file.
- Burned-in subtitles: rendered into the video.
- Stylish captions for YouTube Shorts.
- Arabic RTL support.
- French and English support.

Use accurate timing based on actual generated audio, not estimated reading speed.

### Step 11 — Final render

Use FFmpeg to combine:

- Images/videos.
- Ken Burns motion.
- Transitions.
- Narration.
- Music.
- Sound effects.
- Subtitles.
- Intro/outro.
- Watermark/logo if enabled.

Default export:

- MP4.
- H.264 video.
- AAC audio.
- 720p at 30 fps.
- CRF around 23–26 for a balance between quality and file size.

Allow 1080p as an optional setting, but warn the user that it takes longer and uses more storage.

## 9. AI Decision System

Create a “Creative Director” module.

It receives the topic and produces a production plan:

```json
{
  "language": "ar",
  "voice": {
    "gender": "male",
    "style": "deep_documentary",
    "pace": "slow",
    "emotion": "calm"
  },
  "music": {
    "style": "cinematic_oriental_ambient",
    "mood": "mysterious",
    "energy": "low",
    "instrumentation": ["oud", "strings", "ambient_pad"]
  },
  "visual_style": "historical_documentary",
  "color_grade": "warm_earthy",
  "pacing": "slow",
  "target_duration_seconds": 300
}
```

The Creative Director must not invent facts. It only chooses presentation style.

It should consider:

- Historical topic: calm, deep, cinematic.
- Science topic: clear, modern, curious.
- Motivation topic: energetic, inspiring.
- Horror/mystery: dark, tense, suspenseful.
- Travel: bright, adventurous.
- Business: confident, modern.

## 10. Provider Abstraction

Do not hard-code one provider.

Create provider interfaces:

```text
AIProvider
TTSProvider
MusicProvider
ImageProvider
VideoProvider
SoundEffectProvider
SearchProvider
```

Each provider implements the same interface. This allows the user to switch between free and premium services without changing the app.

### Minimum providers for version 1

| Function | Free default | Premium optional |
|---|---|---|
| Research/script | OpenAI, Gemini, Groq, or OpenRouter | Same |
| Voice-over | Edge-TTS | ElevenLabs |
| Images/videos | Pexels | Pexels + AI image provider |
| Music | Pixabay / YouTube Audio Library | ElevenLabs Music |
| Sound effects | None or free library | ElevenLabs Sound Effects |
| Rendering | FFmpeg | FFmpeg |

Pexels provides a free API for accessing its photo and video library. [web:27][web:28][web:30]

## 11. Multilingual Support

### UI languages

- Arabic: default, RTL.
- French.
- English.

Use a translation file system, not hardcoded strings.

### Content languages

At minimum:

- Arabic.
- French.
- English.

Later:

- Spanish.
- Turkish.
- German.
- Italian.
- Portuguese.
- Russian.

The app must handle:

- RTL text rendering.
- Arabic font selection.
- Correct subtitle direction.
- Language-specific TTS voices.
- Correct date and number formatting.
- Correct search keywords for each language.

## 12. Low-End PC Constraints

The app must be designed for:

- 4 GB RAM.
- No dedicated GPU.
- Windows 10/11.
- Limited disk space.
- Average internet connection.

### Required constraints

- Do not load entire videos into memory.
- Process scenes one by one.
- Download media sequentially, not all at once.
- Use 720p as default.
- Use efficient H.264 encoding.
- Clean temporary files after rendering.
- Limit concurrent downloads.
- Show estimated storage requirements before starting.
- Support resume/retry for failed steps.
- Avoid local diffusion models, local LLMs, and local video-generation models.

Local text-to-video generation is impractical on 4 GB RAM; cloud APIs should handle heavy generative work. [web:9]

## 13. Safety, Licensing, and Quality

### Content safety

- Do not automatically publish to YouTube.
- Require user review before export or upload.
- Flag potentially sensitive topics: politics, religion, war, health, finance, crime.
- Show source links for factual claims.
- Warn when sources are weak or conflicting.

### Copyright

- Use only licensed or clearly permitted media.
- Store license/attribution data for every asset.
- Prevent export if a required asset has unknown licensing.
- Allow the user to add attribution when required.
- Do not scrape copyrighted music or video from random websites.

### AI disclosure

Add an optional setting:

- “This video was created with AI assistance.”

This is good practice for transparency.

## 14. Error Handling

Every failure must show a simple Arabic message, for example:

- “تعذر الاتصال بالإنترنت.”
- “مفتاح Pexels غير صالح.”
- “لم يتم العثور على صور مناسبة لهذا المشهد.”
- “تعذر توليد الصوت، حاول مرة أخرى.”
- “المساحة غير كافية لتصدير الفيديو.”

The app must:

- Save technical logs.
- Identify the failed step.
- Allow retry from the failed step.
- Never lose completed work.
- Never show raw stack traces to normal users.

## 15. Data Storage

Store locally:

```text
AppData/
  DocuMakerDZ/
    config.json
    api_keys.enc
    logs/
    cache/
    projects/
```

Use encrypted storage or Windows Credential Manager for API keys. Do not store keys in plain text if possible.

Each project must be self-contained so the user can move or back it up.

## 16. Minimum Viable Product

Build version 1.0 with only these features:

1. Arabic desktop GUI.
2. Topic input.
3. Language selection: Arabic, French, English.
4. Duration selection: 3 or 5 minutes.
5. AI research and script generation.
6. Scene-by-scene script structure.
7. Edge-TTS voice-over.
8. Pexels image/video search.
9. Automatic scene duration based on audio.
10. Music from Pixabay or user upload.
11. Audio ducking.
12. Subtitles.
13. FFmpeg MP4 export.
14. Project folder with all assets.
15. API-key settings screen.
16. Progress bar and error messages.
17. No Terminal window.
18. Packaged `.exe` with custom icon.

Do not include YouTube upload, advanced editing, voice cloning, or complex AI video generation in version 1.

## 17. Version 2 Features

Add after version 1 works reliably:

- Script editing and regeneration.
- Voice preview.
- Multiple TTS providers.
- ElevenLabs integration.
- AI-generated music.
- AI-generated images.
- Thumbnail generator.
- YouTube title, description, tags, and chapters.
- Templates for different niches.
- Batch creation.
- 1080p export.
- Background removal.
- Better subtitles.
- Project templates.
- Multi-language UI.

## 18. Version 3 Features

Add later:

- YouTube upload with OAuth.
- Scheduled publishing.
- Channel brand kit.
- Automatic series creation.
- Fact-checking workflow.
- Advanced audio mastering.
- Voice cloning with explicit consent only.
- Collaboration features.
- Analytics integration.
- Mobile companion app.

## 19. Acceptance Criteria

The application is successful if a non-technical user can:

1. Install and open it without using Terminal.
2. Enter a topic in Arabic, French, or English.
3. Connect an API key from the Settings screen.
4. Press “Create Video”.
5. See clear progress.
6. Receive a complete MP4 video.
7. Receive script, audio, subtitles, and sources.
8. Edit the script and regenerate only affected parts.
9. Use the app on a 4 GB RAM PC without crashes.
10. Understand every error message in their chosen language.

## 20. Developer Instructions

Build the application as a modular, production-quality desktop product.

Prioritize:

1. Stability.
2. Low memory usage.
3. Clear Arabic UX.
4. Reliable audio-video synchronization.
5. Legal media usage.
6. Modular API providers.
7. Simple first version.
8. Extensible architecture.

Do not build a monolithic script. Create separate modules for UI, AI, media, storage, rendering, settings, localization, and error handling.

The first deliverable should be a working MVP that creates one complete 3–5 minute Arabic documentary video from a title, using free APIs and FFmpeg, then package it as a Windows `.exe` with an icon and no console window.
