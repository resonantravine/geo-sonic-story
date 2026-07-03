"""Voice Style — 3-level dialect strategy for narration voices.

Level 1: standard_mandarin (default, safest)
Level 2: local_flavored_mandarin (light regional rhythm)
Level 3: dialect_or_accent (real dialect, only with verified TTS support)
"""

import json
from pathlib import Path
from typing import Optional


class VoiceStyle:
    def __init__(self, mode: str = "local_flavored_mandarin",
                 target_locale: str = "",
                 dialect_strength: str = "light",
                 fallback_voice: str = "standard_zh_narrator",
                 speaker_id: Optional[str] = None,
                 description: str = ""):
        self.mode = mode
        self.target_locale = target_locale
        self.dialect_strength = dialect_strength
        self.fallback_voice = fallback_voice
        self.speaker_id = speaker_id
        self.description = description

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "target_locale": self.target_locale,
            "dialect_strength": self.dialect_strength,
            "fallback_voice": self.fallback_voice,
            "speaker_id": self.speaker_id,
            "description": self.description,
        }

    def save(self, output_path: str):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))


# ── Locale → voice style mapping ──

LOCALE_STYLES = {
    "北京": VoiceStyle(
        mode="local_flavored_mandarin",
        target_locale="Beijing / Xicheng",
        dialect_strength="light",
        fallback_voice="standard_zh_narrator",
        description="普通话为主，带轻微北京口语节奏。不夸张模仿，不喜剧化。Documentary-fiction 气质。",
    ),
    "上海": VoiceStyle(
        mode="local_flavored_mandarin",
        target_locale="Shanghai",
        dialect_strength="light",
        fallback_voice="standard_zh_narrator",
        description="普通话为主，轻微吴语节奏倾向。",
    ),
    "广州": VoiceStyle(
        mode="local_flavored_mandarin",
        target_locale="Guangzhou / Canton",
        dialect_strength="light",
        fallback_voice="standard_zh_narrator",
        description="普通话为主，轻微粤语节奏倾向。",
    ),
}


def resolve_voice_style(location: str, language: str = "zh") -> VoiceStyle:
    """Resolve voice style from location. Falls back to standard mandarin."""
    if language != "zh":
        return VoiceStyle(
            mode="standard_mandarin",
            description="标准普通话旁白",
        )

    for key, style in LOCALE_STYLES.items():
        if key in location:
            return style

    return VoiceStyle(
        mode="standard_mandarin",
        fallback_voice="standard_zh_narrator",
        description="标准普通话旁白",
    )
