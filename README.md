# Geo-Sonic Story

Turn real audio recordings into fictional place‑time‑grounded audio stories.

A recording of a street corner becomes a two‑part audio story — one anchored in the sounds you captured, another woven from the history of the place. The original recording opens the piece, then fades into a warm single‑narrator telling over a bed of real ambience.

## What this repo is

This is an **agent‑assisted scaffold** — the CLI handles metadata extraction, grounding, context queries, and output slots. Story writing, TTS narration, and final mixing are currently performed by an AI agent (Cola) using the modules in this repo.

### Current CLI (what `run.py` does right now)

```bash
python run.py --audio <your_recording.mp3> --location "Beijing, 国子监" --story-time "30 years ago"
```

Outputs:
- `metadata.json` — recording time, GPS/location, duration, confidence levels (ExifTool → ffprobe → filename → filesystem fallback)
- `anchor.json` — sound cues, time anchor, location anchor
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
python run.py --audio <file> --location <place> --story-time <period> --full
```

Creates all output slots including `mix_report.json` and `audio_relevance_qa.json` for the complete pipeline.

## Pipeline

```
original recording
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
| `metadata_extractor.py` | Time, location, duration from audio file (ExifTool/ffprobe) |
| `audio_ingest.py` | Read and normalize input audio |
| `anchor_extractor.py` | Identify salient sound cues and time/location anchors |
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
# Grounding package only
python run.py --audio <your_recording.mp3> --location "Beijing, 国子监" --story-time "30 years ago"

# Full scaffold (all output slots)
python run.py --audio <your_recording.mp3> --location "Beijing, 国子监" --story-time "30 years ago" --full
```

Requirements:
```bash
pip install -r requirements.txt
```

Optional: install ExifTool for best metadata extraction:
```bash
brew install exiftool  # macOS
```
