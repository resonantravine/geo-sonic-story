#!/usr/bin/env python3
"""Geo-Sonic Story — 地方回声.

Turns a real audio recording into a short fictional audio story
grounded in a real place and a chosen historical time.

Default mode (grounding package):
    python run.py --audio <file> --location <place> --story-time <period>

Full pipeline (agent-assisted):
    python run.py --audio <file> --location <place> --story-time <period> --full

For complete story generation (narration, TTS, mixing), see the
agent-assisted workflow documented in README.md.
"""

import argparse
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from modules import metadata_extractor, anchor_extractor, story_time_resolver
from modules import context_retriever, brief_builder
from modules import story_seed_generator, script_generator, voice_generator
from modules import audio_mixer, audio_relevance_qa

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
    parser.add_argument("--full", action="store_true",
                        help="Run full pipeline including seeds, script, mixing slots, and QA")
    parser.add_argument("--tts", action="store_true",
                        help="Attempt TTS voice generation (requires provider)")
    return parser.parse_args()


def main():
    args = parse_args()

    run_id = str(uuid.uuid4())[:8]
    output_dir = args.output_dir or f"runs/{run_id}"
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*60}")
    print(f"  Geo-Sonic Story — 地方回声")
    print(f"  Run ID: {run_id}")
    print(f"  Mode: {'full' if args.full else 'grounding package'}")
    print(f"  Output: {output_dir}")
    print(f"{'='*60}\n")

    # ── Step 1: Metadata Extraction ──
    print("[1/7] Extracting metadata...")
    try:
        audio_meta = metadata_extractor.extract(
            args.audio,
            user_location=args.location,
        )
        print(f"      File: {audio_meta.audio_file}")
        print(f"      Duration: {audio_meta.duration_sec:.1f}s")
        if audio_meta.recording_time:
            print(f"      Recording time: {audio_meta.recording_time} "
                  f"(source: {audio_meta.recording_time_source}, "
                  f"confidence: {audio_meta.recording_time_confidence})")
        if audio_meta.lat is not None:
            print(f"      GPS: {audio_meta.lat:.4f}, {audio_meta.lon:.4f} "
                  f"(source: {audio_meta.location_source}, "
                  f"confidence: {audio_meta.location_confidence})")
        if audio_meta.needs_manual_location:
            print(f"      ⚠ Location unresolved — geocoded from user input: {args.location}")
        if audio_meta.location_note:
            print(f"      ⓘ {audio_meta.location_note}")
    except Exception as e:
        print(f"      ERROR: {e}")
        return 1

    # Save full metadata
    meta_dict = {
        "audio_file": audio_meta.audio_file,
        "duration_sec": audio_meta.duration_sec,
        "recording_time": audio_meta.recording_time,
        "recording_time_source": audio_meta.recording_time_source,
        "recording_time_confidence": audio_meta.recording_time_confidence,
        "lat": audio_meta.lat, "lon": audio_meta.lon,
        "location_source": audio_meta.location_source,
        "location_confidence": audio_meta.location_confidence,
        "needs_manual_location": audio_meta.needs_manual_location,
        "location_note": audio_meta.location_note,
    }
    Path(output_dir, "metadata.json").write_text(
        json.dumps(meta_dict, indent=2, ensure_ascii=False)
    )

    # ── Step 2: Anchor Extractor ──
    print("\n[2/7] Building anchor...")
    recording_time = args.recording_time or audio_meta.recording_time or NOW.isoformat()
    sound_cues = [s.strip() for s in args.sound_cues.split(",") if s.strip()]
    anchor = anchor_extractor.build_anchor(
        audio_file=args.audio,
        duration_sec=audio_meta.duration_sec,
        recording_time=recording_time,
        location=args.location,
        lat=audio_meta.lat,
        lon=audio_meta.lon,
        sound_cues=sound_cues,
    )
    anchor.save(f"{output_dir}/anchor.json")
    print(f"      Location: {anchor.location_text}")
    print(f"      Sound cues: {anchor.sound_cues}")

    # ── Step 3: Story Time Resolver ──
    print("\n[3/7] Resolving story time...")
    story_time = story_time_resolver.resolve(args.story_time, recording_time)
    story_time.save(f"{output_dir}/story_time.json")
    print(f"      Input: '{story_time.story_time_input}'")
    print(f"      Resolved: {story_time.resolved_label}")
    print(f"      Search range: {story_time.start_year}–{story_time.end_year}")

    # ── Step 4: Context Retriever ──
    print("\n[4/7] Preparing context retrieval...")
    ctx = context_retriever.create_context(args.location, story_time.resolved_label)
    ctx.save(f"{output_dir}/retrieved_context.json")
    print(f"      Generated {len(ctx.search_queries)} search queries:")
    for q in ctx.search_queries:
        print(f"        - {q}")

    # ── Step 5: Place-Time Brief ──
    print("\n[5/7] Building Place-Time Brief...")
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

    # ── Step 6: Seeds, Script, Mixing, QA ──
    if args.full:
        print("\n[6/7] Running full pipeline...")

        # Story seeds
        seeds = story_seed_generator.create_empty_collection()
        seeds.save(f"{output_dir}/story_seeds.json")
        print("      Created story_seeds.json (empty — fill via agent or provider)")

        # Script placeholder
        placeholder_script = script_generator.Script(
            title="(pending)",
            duration_target_sec=90,
            narration_text="(to be generated by agent or provider)",
            sound_design_notes="(to be generated by agent or provider)",
            language=args.language,
        )
        placeholder_script.save_json(f"{output_dir}/script.json")
        placeholder_script.save_markdown(f"{output_dir}/script.md")

        # Mixing slots
        mix_report = audio_mixer.MixReport(
            original_audio_used=True,
            generated_ambience_used=False,
            narration_duration_sec=0,
            final_mix_duration_sec=0,
            disclaimer_in_audio=True,
            present_audio_not_used_as_past_evidence=True,
        )
        mix_report.save(f"{output_dir}/mix_report.json")
        print("      Created mix_report.json (empty — fill after narration generation)")

        # QA slots
        qa = audio_relevance_qa.AudioRelevanceQA(
            original_audio_mixed=False,
            audio_relevance_score=0.0,
            story_segments_count=2,
        )
        qa.save(f"{output_dir}/audio_relevance_qa.json")
        print("      Created audio_relevance_qa.json (empty — fill after script generation)")

        # TTS
        if args.tts:
            voice_generator.note_not_configured(f"{output_dir}/output")
            print("      ⓘ TTS requires provider integration — wrote TTS_NOT_CONFIGURED.md")
    else:
        print("\n[6/7] Creating output slots...")
        seeds = story_seed_generator.create_empty_collection()
        seeds.save(f"{output_dir}/story_seeds.json")

        placeholder_script = script_generator.Script(
            title="(pending)",
            duration_target_sec=90,
            narration_text="(to be generated by agent)",
            sound_design_notes="(to be generated by agent)",
            language=args.language,
        )
        placeholder_script.save_json(f"{output_dir}/script.json")
        placeholder_script.save_markdown(f"{output_dir}/script.md")

        voice_generator.note_not_configured(f"{output_dir}/output")
        print(f"      Saved story_seeds.json, script.md, TTS_NOT_CONFIGURED.md")

    # ── Step 7: Summary ──
    print(f"\n[7/7] Summary")
    print(f"{'='*60}")
    if args.full:
        print(f"  FULL PIPELINE SCAFFOLD COMPLETE")
    else:
        print(f"  GROUNDING PACKAGE COMPLETE")
    print(f"{'='*60}")

    if not args.full:
        print(f"\nNext steps (agent-assisted):")
        print(f"  1. Run search queries from retrieved_context.json")
        print(f"  2. Fill entities & period context → retrieved_context.json")
        print(f"  3. Rebuild place_time_brief.md with retrieved data")
        print(f"  4. Generate story seeds → story_seeds.json")
        print(f"  5. Generate narration script → script.md + script.json")
        print(f"  6. Generate voice audio via TTS provider")
        print(f"  7. Mix narration + original audio → output/")
        print(f"  8. Run QA validation → audio_relevance_qa.json")
        print(f"\nOr re-run with --full for complete output slots.")
    else:
        print(f"\nNext steps (agent-assisted):")
        print(f"  1. Run search queries and fill retrieved_context.json")
        print(f"  2. Write story seeds → story_seeds.json")
        print(f"  3. Write narration script → script.md + script.json")
        print(f"  4. Generate narration audio via provider")
        print(f"  5. Mix with audio_mixer → output/final_mix.mp3")
        print(f"  6. Run audio_relevance_qa on final output")

    print(f"\nFiles created:")
    for f in sorted(Path(output_dir).rglob("*")):
        if f.is_file():
            print(f"  {f}")

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
