#!/usr/bin/env python3
"""Geo-Sonic Story — 地方回声.

Turns a real audio recording into a short fictional audio story
grounded in a real place and a chosen historical time.

Usage:
    python run.py --audio <file> --location <place> --story-time <period> [OPTIONS]

Example:
    python run.py \\
        --audio samples/sample.wav \\
        --location "Yanaka, Tokyo, Japan" \\
        --story-time "100 years ago" \\
        --sound-cues "distant train, footsteps, evening ambience" \\
        --language zh
"""

import argparse
import uuid
from datetime import datetime, timezone
from pathlib import Path

from modules import audio_ingest, anchor_extractor, story_time_resolver
from modules import context_retriever, brief_builder
from modules import story_seed_generator, script_generator, voice_generator


NOW = datetime.now(timezone.utc)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Geo-Sonic Story — turn recordings into place-time-grounded audio stories."
    )
    parser.add_argument("--audio", required=True, help="Path to audio file")
    parser.add_argument("--location", required=True, help="Place name or address")
    parser.add_argument("--story-time", required=True,
                        help="Story time period, e.g. '100 years ago', 'the 1980s', '2010'")
    parser.add_argument("--recording-time", default=None,
                        help="Recording datetime, ISO format. Default: audio metadata or now.")
    parser.add_argument("--sound-cues", default="",
                        help="Comma-separated sound cues, e.g. 'train, footsteps, birds'")
    parser.add_argument("--language", default="zh", choices=["zh", "en"],
                        help="Output language (default: zh)")
    parser.add_argument("--style", default="documentary-fiction",
                        help="Story style (default: documentary-fiction)")
    parser.add_argument("--output-dir", default=None,
                        help="Output directory. Default: runs/<run-id>/")
    parser.add_argument("--tts", action="store_true",
                        help="Attempt TTS voice generation")
    return parser.parse_args()


def main():
    args = parse_args()

    # Generate run ID
    run_id = str(uuid.uuid4())[:8]
    output_dir = args.output_dir or f"runs/{run_id}"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Geo-Sonic Story — 地方回声")
    print(f"  Run ID: {run_id}")
    print(f"  Output: {output_dir}")
    print(f"{'='*60}\n")

    # ── Step 1: Audio Ingest ──
    print("[1/6] Ingesting audio...")
    try:
        audio_meta = audio_ingest.ingest_audio(args.audio)
        print(f"      File: {audio_meta.file_path}")
        print(f"      Duration: {audio_meta.duration_sec:.1f}s")
        if audio_meta.creation_time:
            print(f"      Creation time: {audio_meta.creation_time}")
    except Exception as e:
        print(f"      ERROR: {e}")
        return 1

    # ── Step 2: Anchor Extractor ──
    print("\n[2/6] Building anchor...")
    recording_time = args.recording_time or audio_meta.creation_time or NOW.isoformat()
    sound_cues = [s.strip() for s in args.sound_cues.split(",") if s.strip()]
    anchor = anchor_extractor.build_anchor(
        audio_file=args.audio,
        duration_sec=audio_meta.duration_sec,
        recording_time=recording_time,
        location=args.location,
        lat=audio_meta.gps_lat,
        lon=audio_meta.gps_lon,
        sound_cues=sound_cues,
    )
    anchor.save(f"{output_dir}/metadata.json")
    print(f"      Location: {anchor.location_text}")
    print(f"      Sound cues: {anchor.sound_cues}")

    # ── Step 3: Story Time Resolver ──
    print("\n[3/6] Resolving story time...")
    story_time = story_time_resolver.resolve(args.story_time, recording_time)
    story_time.save(f"{output_dir}/story_time.json")
    print(f"      Input: '{story_time.story_time_input}'")
    print(f"      Resolved: {story_time.resolved_label}")
    print(f"      Search range: {story_time.start_year}–{story_time.end_year}")

    # ── Step 4: Context Retriever ──
    print("\n[4/6] Preparing context retrieval...")
    ctx = context_retriever.create_context(args.location, story_time.resolved_label)
    ctx.save(f"{output_dir}/retrieved_context.json")
    print(f"      Generated {len(ctx.search_queries)} search queries:")
    for q in ctx.search_queries:
        print(f"        - {q}")

    # ── Step 5: Place-Time Brief (partial) ──
    print("\n[5/6] Building Place-Time Brief (pending retrieval)...")
    brief_md = brief_builder.build_markdown(
        audio_file=args.audio,
        recording_time=recording_time,
        duration_sec=audio_meta.duration_sec,
        location=args.location,
        lat=anchor.lat,
        lon=anchor.lon,
        sound_cues=anchor.sound_cues,
        story_time_input=story_time.story_time_input,
        resolved_label=story_time.resolved_label,
        start_year=story_time.start_year,
        end_year=story_time.end_year,
        nearby_entities=ctx.nearby_entities,
        period_context=ctx.period_context,
        uncertainties=ctx.uncertainties,
    )
    brief_builder.save_brief(brief_md, f"{output_dir}/place_time_brief.md")
    print(f"      Saved to place_time_brief.md")

    # ── Step 6: Seeds & Script — agent-assisted ──
    print("\n[6/6] Preparing output slots for agent-assisted generation...")

    # Empty seed collection
    seeds = story_seed_generator.create_empty_collection()
    seeds.save(f"{output_dir}/story_seeds.json")

    # Empty script placeholder
    placeholder_script = script_generator.Script(
        title="(pending)",
        duration_target_sec=90,
        narration_text="(to be generated by agent)",
        sound_design_notes="(to be generated by agent)",
        language=args.language,
    )
    placeholder_script.save_json(f"{output_dir}/script.json")
    placeholder_script.save_markdown(f"{output_dir}/script.md")

    # TTS fallback
    voice_generator.note_not_configured(f"{output_dir}/output")
    print(f"      Saved TTS_NOT_CONFIGURED.md (fallback)")

    # ── Summary ──
    print(f"\n{'='*60}")
    print(f"  PIPELINE COMPLETE (partial)")
    print(f"{'='*60}")
    print(f"\nFiles created:")
    for f in sorted(Path(output_dir).rglob("*")):
        if f.is_file():
            print(f"  {f}")

    print(f"\nNext steps for agent (Cola):")
    print(f"  1. Run search queries from retrieved_context.json")
    print(f"  2. Fill entities & period context → retrieved_context.json")
    print(f"  3. Rebuild place_time_brief.md with retrieved data")
    print(f"  4. Generate 3 story seeds → story_seeds.json")
    print(f"  5. Generate narration script → script.md + script.json")
    print(f"  6. (Optional) Generate voice audio via TTS")

    return {
        "run_id": run_id,
        "output_dir": output_dir,
        "ctx": ctx,
        "story_time": story_time,
        "anchor": anchor,
    }


if __name__ == "__main__":
    result = main()
    if isinstance(result, dict):
        print(f"\nDone. Run ID: {result['run_id']}")
