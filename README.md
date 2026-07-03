# Geo-Sonic Story

Turn real audio recordings into fictional place‑time‑grounded audio stories.

A recording of a street corner becomes a two‑part audio story — one anchored in the sounds you captured, another woven from the history of the place. The original recording opens the piece, then fades into a warm single‑narrator telling over a bed of real ambience.

## Pipeline

```
original recording
  → metadata extraction (time, location, duration)
  → anchor extraction (sound cues from the audio)
  → story‑time resolution (when in history)
  → context retrieval (place history + period facts)
  → brief building (place‑time‑audio vision)
  → story seed generation (2 seeds with audio motifs)
  → script generation (v0.4: concrete sensory, no meta markers)
  → podcast‑quality narration (ListenHub, single narrator)
  → stem mixing (15s pure recording intro → narration + 15% ambience)
  → QA validation (storytelling quality + audio grounding)
```

## Modules

| Module | Role |
|---|---|
| `metadata_extractor.py` | Time, location, duration from audio file |
| `audio_ingest.py` | Read and normalize input audio |
| `anchor_extractor.py` | Identify salient sound cues |
| `story_time_resolver.py` | Resolve "30 years ago" → concrete year |
| `context_retriever.py` | Place entities + period facts |
| `brief_builder.py` | Assemble place‑time‑audio vision |
| `story_seed_generator.py` | Two narrative seeds with audio motifs |
| `script_generator.py` | Full script with natural disclaimer |
| `voice_generator.py` | TTS / podcast narration generation |
| `voice_style.py` | 3‑level dialect strategy |
| `audio_mixer.py` | Stem‑based ffmpeg mixing |
| `audio_relevance_qa.py` | Storytelling quality validation |

## Quick start

```bash
pip install -r requirements.txt
python run.py --input <your_recording.mp3> --location "Beijing, 国子监" --story-time "2016"
```
