# Echoes of Place

> Repo slug: `geo-sonic-story`

**把一段真实录音，转化为基于地点、年代和声音线索的历史虚构声音故事。**

**Turn real recordings into place-based historical fiction audio stories.**

Echoes of Place is an agent-assisted audio storytelling scaffold. It takes a real recording, extracts or confirms its time and location, retrieves place-time context, and helps generate a historical fiction story grounded in the recording's sound cues.

The story is fictional. The place, time anchor, and historical background are treated as grounding constraints.

## Demo

Two complete audio stories — source recording + narrated final mix:

| | Mississippi Steam Boat | Wuhan Market |
|---|---|---|
| **Story** | 1985, a paddle steamer on the Mississippi River with an old bargeman and a boy | 1994, a mother and daughter at a rural vegetable market on the outskirts of Wuhan |
| **Opener** | A steam whistle echoing across the water | Footsteps, chatter, and vendors in the morning mist |
| **Narrator** | 常四爷 — mature, magnetic, slow storytelling voice | 常四爷 |
| **Listen** | [Download →](https://github.com/resonantravine/geo-sonic-story/releases/tag/v0.4-demos) | [Download →](https://github.com/resonantravine/geo-sonic-story/releases/tag/v0.4-demos) |

Both stories begin with 15 seconds of the original recording, then the narration enters over a soft ambience bed, and each closes with a warm ending that brings the listener back to the present moment.

**[📦 All demos + source recordings → v0.4-demos release](https://github.com/resonantravine/geo-sonic-story/releases/tag/v0.4-demos)**

## How it works

### What this repo is

This is an **agent‑assisted scaffold** — the CLI handles metadata extraction, grounding, context queries, and output slots. Story writing, TTS narration, and final mixing are currently performed by an AI agent (Cola) using the modules in this repo.

### What `run.py` does

```bash
# Demo: BBC archive recording of Wuhan vegetable market, 1990s
python run.py --audio samples/wuhan-market.wav --location "武汉郊外" --story-time "30 years ago"
```

Outputs:
- `metadata.json` — recording time (with source, confidence, detected vs. override), GPS/location (with source, precision), duration
- `anchor.json` — sound cues, time anchor, location anchor (with real location source, never mislabeled as "gps")
- `story_time.json` — resolved historical period
- `retrieved_context.json` — search queries for place entities + period facts
- `place_time_brief.md` — assembled place‑time‑audio vision
- `story_seeds.json` — empty seed slots
- `script.md` / `script.json` — placeholder output slots

### Agent‑assisted workflow (what happens after `run.py`)

The AI agent then:
1. Runs the search queries from `retrieved_context.json`
2. Writes story seeds → `story_seeds.json`
3. Writes narration script → `script.md` + `script.json`
4. Generates narration audio via ListenHub podcast engine
5. Mixes narration + original recording via `audio_mixer.py`
6. Validates output via `audio_relevance_qa.py`

### Full scaffold mode

```bash
python run.py --audio samples/wuhan-market.wav --location "武汉郊外" --story-time "30 years ago" --full-scaffold
```

Full scaffold mode does **not** generate the final story. It creates all file slots and QA placeholders for the complete agent-assisted pipeline (including `mix_report.json` and `audio_relevance_qa.json`).

### ⚠️ Geocoding note

The built-in geocoder in `metadata_extractor.py` is a **demo lookup** with a small hand‑maintained dictionary of known places. It is not a real geocoding service. In production, replace `_geocode_place()` with:
- [Nominatim](https://nominatim.org) (OpenStreetMap, free, rate‑limited)
- [Google Geocoding API](https://developers.google.com/maps/documentation/geocoding)
- [Amap / 高德](https://lbs.amap.com) or [Baidu Maps](https://lbsyun.baidu.com) for China

Coordinates from this demo geocoder are approximate and should not be relied on for accuracy.

## Pipeline

```
field recording
  → metadata extraction (ExifTool → ffprobe → filename → filesystem)
  → anchor extraction (sound cues from audio + time/location anchors)
  → story‑time resolution (when in history)
  → context retrieval (place history + period facts)
  → brief building (place‑time‑audio vision)
  → [agent] story seed generation (2 seeds with audio motifs)
  → [agent] script generation (concrete sensory storytelling, no meta markers)
  → [agent] podcast‑quality narration (ListenHub, single narrator)
  → [agent] stem mixing (15s pure recording intro → narration + 15% ambience)
  → [agent] QA validation (storytelling quality + audio grounding)
```

## Modules

| Module | Role |
|---|---|
| `metadata_extractor.py` | Time, location, duration (ExifTool/ffprobe, demo geocoder) |
| `audio_ingest.py` | Read and normalize input audio |
| `anchor_extractor.py` | Sound cues + time/location anchors (preserves real location_source) |
| `story_time_resolver.py` | Resolve "30 years ago" → concrete year |
| `context_retriever.py` | Place entities + period facts search queries |
| `brief_builder.py` | Assemble place‑time‑audio vision |
| `story_seed_generator.py` | Two narrative seeds with audio motifs |
| `script_generator.py` | Full script with natural disclaimer |
| `voice_generator.py` | TTS / podcast narration generation slots |
| `voice_style.py` | 3‑level dialect strategy |
| `audio_mixer.py` | Stem‑based ffmpeg mixing (narration + original + ambience) |
| `audio_relevance_qa.py` | Storytelling quality validation (40+ checks) |

## Quick start

```bash
# Grounding package (demo)
python run.py --audio samples/wuhan-market.wav --location "武汉郊外" --story-time "30 years ago"

# Full scaffold (all output slots, no final audio)
python run.py --audio samples/wuhan-market.wav --location "武汉郊外" --story-time "30 years ago" --full-scaffold

# With sound cues
python run.py --audio samples/wuhan-market.wav --location "武汉郊外" --story-time "30 years ago" --sound-cues "footsteps, chatter, vendors"
```

### Demo sample

Download the demo recording from BBC Sound Effects:

1. Visit [BBC Sound Effects](https://sound-effects.bbcrewind.co.uk/)
2. Search: `wuhan vegetable market rural`
3. Download **"China - Wuhan: Vegetable market (rural area near Wuhan)"** (3:06, WAV)
4. Save as `samples/wuhan-market.wav`

Requirements:
```bash
pip install -r requirements.txt
```

Optional: install ExifTool for best metadata extraction:
```bash
brew install exiftool  # macOS
```
