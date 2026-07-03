---
name: echoes-of-place
description: >
  Turn a real audio recording into a fictional place-time-grounded audio story.
  Use when a user provides an audio file and asks to make it into a story,
  or mentions "Echoes of Place", "地方回声", "audio story", "field recording story",
  "把录音变成故事", "声音故事", or gives a recording with a location and time period.
  Also use when the user wants to generate a Geo-Sonic Story.
metadata:
  category: creative
---

# Echoes of Place / 地方回声

Turn a field recording into a fictional two-part audio story grounded in place and time. The original recording opens the piece, then the story is told by a single warm narrator over a bed of the original ambience.

Project root: `/Users/martaliu/cola/outputs/Geo-Sonic-Story-MVP/`
Modules: `modules/` directory at project root.

## Pipeline

This is an agent-assisted pipeline. Cola executes every step — the modules provide data structures and utilities, but the agent orchestrates, searches the web, writes stories, generates TTS, and mixes audio.

### Step 1: Gather Inputs

Ask the user for:
- **audio file** (required) — absolute path
- **location** (required) — place name, e.g. "国子监", "武汉郊外"
- **story time** (required) — "30 years ago", "2016", "the 1980s"
- **sound cues** (optional) — comma-separated, e.g. "footsteps, chatter, vendors"
- **language** (optional, default zh) — zh or en

If the user only gives an audio file, ask for location and story time before proceeding.

### Step 2: Metadata Extraction

```python
import sys; sys.path.insert(0, '/Users/martaliu/cola/outputs/Geo-Sonic-Story-MVP')
from modules import metadata_extractor
meta = metadata_extractor.extract(audio_path, user_location=location)
```

This gives you: `duration_sec`, `recording_time` (with source/confidence), GPS coordinates (with source/confidence), `needs_manual_location`, `location_note`.

Save: `metadata.json` using `meta.to_dict()`.

If `needs_manual_location` is true, the coordinates were geocoded from user input — this is fine for storytelling. Trust the user's location text even without GPS.

### Step 3: Anchor Extraction

```python
from modules import anchor_extractor
anchor = anchor_extractor.build_anchor(
    audio_file=audio_path, duration_sec=meta.duration_sec,
    recording_time=meta.recording_time, location=location,
    lat=meta.lat, lon=meta.lon,
    location_source=meta.location_source,
    sound_cues=sound_cues_list,
)
anchor.save(f"{run_dir}/anchor.json")
```

### Step 4: Story Time Resolution

```python
from modules import story_time_resolver
story_time = story_time_resolver.resolve(story_time_input, meta.recording_time)
story_time.save(f"{run_dir}/story_time.json")
```

This converts "30 years ago" into a concrete year range with search bounds.

### Step 5: Context Retrieval (AGENT STEP — web search)

```python
from modules import context_retriever
ctx = context_retriever.create_context(location, story_time.resolved_label)
ctx.save(f"{run_dir}/retrieved_context.json")
```

`ctx.search_queries` gives you a list of search strings. **Execute these searches** using `web_search` to find:
- Place entities (landmarks, geography, history)
- Period facts (what was happening there at that time)

Fill the results into `ctx.nearby_entities`, `ctx.period_context`, `ctx.uncertainties`, then save again.

### Step 6: Brief Building

```python
from modules import brief_builder
brief_md = brief_builder.build_markdown(...)
brief_builder.save_brief(brief_md, f"{run_dir}/place_time_brief.md")
```

Pass all collected context — entities, period facts, sound cues, time range.

### Step 7: Story Seed Generation (AGENT STEP — LLM)

Generate 2 story seeds. Each seed needs:
- A title
- A character (concrete: "姓周的老人", "毕业旅行的女孩")
- A sound motif from the recording
- Sensory details (NOT abstract words — use concrete: 车声, 门帘, 蒲扇, 青砖, 水声)
- An `audio_dependency` dict with: `present_day_frame`, `sonic_motif`, `then_vs_now_contrast`, `script_required_lines`

Save to `story_seeds.json`.

### Step 8: Script Generation (AGENT STEP — LLM)

Write the full narration script. **CRITICAL rules:**

- **No "故事一 / 故事二" markers** in the script
- **No meta/abstract words**: 历史背景, 资料, 地点, 生成, 还原, 基于, 检索
- **Yes concrete sensory**: 车声, 脚步, 青砖, 槐树, 马扎, 门帘, 搪瓷缸子, 蒲扇, 拖鞋, 水声
- **Natural disclaimer**: "这是一个用今天这段录音编的小故事。人是编的，声音是真的。" woven in naturally at the beginning, not a formal statement
- **Two story segments** flowing naturally, no explicit separators
- **Natural spoken long sentences** — not one line per sentence
- **~60-90s total** narrative text

Save using `script_generator.Script` and `save_markdown()`.

### Step 9: Voice Generation (AGENT STEP — ListenHub)

Generate the narration audio using the podcast engine with a single narrator:

```python
# Use tool_call with gen_podcast
# Two-stage flow:
# 1. create_podcast_text (to get episode_id)
# 2. create_podcast_audio with custom scripts — feed the v0.4 story text
#    as line-by-line scripts, all assigned to one speaker (nvdiyin-7b293152 / 暮歌)
```

Key: the podcast engine generates discussion by default. You MUST use `create_podcast_audio` with custom `scripts` — one speaker, the story text broken into natural lines. Do NOT let it generate its own analysis content.

Download the resulting `audioUrl` as `narration.mp3`.

### Step 10: Audio Mixing

```python
from modules import audio_mixer

# Create ambience: trim first 15s of original recording
# Structure: 0-15s pure original → narration with original at ~15% as bed

audio_mixer.mix_narration_with_ambience(
    narration_mp3, ambience_mp3, output_mp3,
    ambience_open_duration=15.0,      # pure recording intro
    ambience_bg_volume=0.15,          # 15% recording under narration
    narration_delay=0.0,              # narration starts immediately
    ambience_reappear_end=3.0,        # recording resurfaces at end
)
```

Use ffmpeg directly if the mixer needs custom timing:

```bash
# 1. Trim 15s ambience
ffmpeg -y -i <original> -t 15 amb_intro.mp3

# 2. Loop for narration length, lower to 15%
ffmpeg -y -stream_loop -1 -i <original> -t <duration> amb_loop.mp3
ffmpeg -y -i amb_loop.mp3 -af "volume=0.15" amb_loop_low.mp3

# 3. Delay narration by 15s, then mix
ffmpeg -y -i narration.mp3 -af "adelay=15000|15000" narration_delayed.mp3
ffmpeg -y -i ambience_full.mp3 -i narration_delayed.mp3 \
    -filter_complex "[0:a][1:a]amix=inputs=2:duration=first:weights=0.6 1" \
    final_mix.mp3
```

### Step 11: QA Validation

```python
from modules import audio_relevance_qa
qa = audio_relevance_qa.validate_script_v04(
    script_text, sound_cues=cues, original_audio_mixed=True
)
qa.save(f"{run_dir}/audio_relevance_qa.json")
```

Check that:
- `says_story_one_or_story_two` is **false**
- `metadata_read_aloud` is **false**
- `narration_style` is **"storytelling"** (not report/documentary/news)
- `story_segments_count` is **2**
- `each_segment_has_character` and `each_segment_has_sound_motif` are **true**
- `fiction_disclaimer_tone` is **"natural"**

If any check fails, fix the script and regenerate before presenting to the user.

### Step 12: Present

Deliver the final mix as `final_mix.mp3`. Show QA results. Reference the run directory.

## Fallback Behavior

- **No ExifTool available**: metadata_extractor already falls back to ffprobe → filename → filesystem
- **No GPS in audio**: geocoding from user location text is fine — note it in metadata
- **TTS fails**: deliver the script as markdown + mix the original recording with silence
- **Geocoding fails**: use the user's location text directly, set `needs_manual_location: true`

## Output Directory

Create runs under `/Users/martaliu/cola/outputs/Geo-Sonic-Story-MVP/runs/<uuid8>/output/`.
