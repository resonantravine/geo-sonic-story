"""Audio Mixer — stem-based audio mixing with ffmpeg.

Pipeline:
A. Original recording → source ambience
B. Narration TTS
C. Generated ambience / SFX (optional)
D. Music bed (optional)
E. Final mix via ffmpeg
"""

import json
import subprocess
from pathlib import Path
from typing import Optional


class MixReport:
    def __init__(self, original_audio_used: bool = False,
                 generated_ambience_used: bool = False,
                 narration_duration_sec: float = 0.0,
                 final_mix_duration_sec: float = 0.0,
                 disclaimer_in_audio: bool = False,
                 present_audio_not_used_as_past_evidence: bool = True):
        self.original_audio_used = original_audio_used
        self.generated_ambience_used = generated_ambience_used
        self.narration_duration_sec = narration_duration_sec
        self.final_mix_duration_sec = final_mix_duration_sec
        self.disclaimer_in_audio = disclaimer_in_audio
        self.present_audio_not_used_as_past_evidence = present_audio_not_used_as_past_evidence

    def to_dict(self) -> dict:
        return {
            "original_audio_used": self.original_audio_used,
            "generated_ambience_used": self.generated_ambience_used,
            "narration_duration_sec": self.narration_duration_sec,
            "final_mix_duration_sec": self.final_mix_duration_sec,
            "disclaimer_in_audio": self.disclaimer_in_audio,
            "present_audio_not_used_as_past_evidence": self.present_audio_not_used_as_past_evidence,
        }

    def save(self, output_path: str):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))


def trim_audio(input_path: str, output_path: str, duration_sec: float = 10.0):
    """Trim first N seconds of audio for ambient intro."""
    subprocess.run([
        "ffmpeg", "-y", "-i", input_path,
        "-t", str(duration_sec),
        "-acodec", "copy",
        output_path,
    ], capture_output=True, timeout=30)


def mix_narration_with_ambience(
    narration_path: str,
    ambience_path: str,
    output_path: str,
    ambience_open_duration: float = 8.0,
    ambience_fade_in_duration: float = 1.0,
    ambience_bg_volume: float = 0.08,
    narration_delay: float = 5.0,
    ambience_reappear_end: float = 5.0,
) -> str:
    """Mix narration with original ambience.

    Structure:
    0–ambience_open_duration: original ambience at full volume, fade in
    narration_delay onwards: ambience drops to bg_volume, narration at full
    End: ambience briefly reappears
    """
    # Get durations
    narration_dur = _get_duration(narration_path)
    ambience_dur = _get_duration(ambience_path)

    total_dur = narration_delay + narration_dur + ambience_reappear_end

    # Build ffmpeg filter
    # Narration: start at narration_delay, full volume
    # Ambience: full at start → fade to bg_volume at narration_delay → fade up at end
    filter_complex = (
        f"[1:a]adelay={int(narration_delay * 1000)}|{int(narration_delay * 1000)}[narration];"
        f"[0:a]volume=1:enable='between(t,0,{narration_delay})'"
        f",volume={ambience_bg_volume}:enable='between(t,{narration_delay},{total_dur - ambience_reappear_end})'"
        f",volume=1:enable='gte(t,{total_dur - ambience_reappear_end})'"
        f",afade=t=in:d={ambience_fade_in_duration}"
        f",afade=t=out:st={total_dur - ambience_reappear_end}:d=2[ambience];"
        f"[narration][ambience]amix=inputs=2:duration=longest[mix]"
    )

    subprocess.run([
        "ffmpeg", "-y",
        "-i", ambience_path,
        "-i", narration_path,
        "-filter_complex", filter_complex,
        "-map", "[mix]",
        "-t", str(total_dur),
        output_path,
    ], capture_output=True, timeout=60)

    return output_path


def simple_mix(narration_path: str, ambience_path: str, output_path: str) -> str:
    """Simple mix: narration over low ambience. Fallback mode."""
    subprocess.run([
        "ffmpeg", "-y",
        "-i", narration_path,
        "-i", ambience_path,
        "-filter_complex",
        "[0:a]volume=1[n];[1:a]volume=0.06[a];[n][a]amix=inputs=2:duration=first",
        output_path,
    ], capture_output=True, timeout=60)
    return output_path


def _get_duration(file_path: str) -> float:
    """Get audio duration via ffmpeg."""
    try:
        r = subprocess.run(
            ["ffmpeg", "-i", file_path, "-f", "null", "-"],
            capture_output=True, text=True, timeout=15,
        )
        for line in r.stderr.split('\n'):
            if 'Duration' in line:
                dur_str = line.split('Duration:')[1].strip().split(',')[0].strip()
                h, m, s = dur_str.split(':')
                return float(h) * 3600 + float(m) * 60 + float(s)
    except Exception:
        pass
    return 0.0
