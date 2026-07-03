"""Script Generator — generate narration script data structure.

v0.2: fiction disclaimer required in script.md, metadata, and audio.
Script must open from present recording — not from past time.
"""

import json
from pathlib import Path
from typing import Optional


FICTION_DISCLAIMER = (
    "这是一个基于真实地点资料、历史背景与现场录音生成的历史虚构故事，并非真实历史还原。\n"
    "This is a fictional story inspired by real place context, "
    "historical background, and the uploaded recording. "
    "It is not a factual reconstruction."
)

# v0.3: natural, story-like disclaimers — for audio narration
FICTION_DISCLAIMER_AUDIO = (
    "这是一个借今天这段录音想象出来的历史虚构小故事。"
)

FICTION_DISCLAIMER_AUDIO_CLOSE = (
    "这两个故事都是历史虚构，不是对真实人物或真实事件的还原。"
)

AUDIO_ENTRY_NOTE = (
    "这段录音不是过去的声音证据，而是今天的声音入口。"
)

FICTION_DISCLAIMER_SHORT = (
    "这是一个历史虚构故事，并非真实历史还原。"
)

# v0.3: metadata disclaimer — for brief.md, not audio
FICTION_DISCLAIMER_BRIEF = (
    "这是一个基于真实地点资料、历史背景与现场录音生成的历史虚构故事，"
    "并非真实历史还原。"
)


class Script:
    def __init__(self, title: str, duration_target_sec: int,
                 narration_text: str, sound_design_notes: str,
                 language: str = "zh",
                 fiction_disclaimer: str = FICTION_DISCLAIMER,
                 fiction_disclaimer_audio: str = FICTION_DISCLAIMER_AUDIO,
                 audio_entry_note: str = AUDIO_ENTRY_NOTE,
                 fiction_disclaimer_required: bool = True,
                 fiction_disclaimer_in_script: bool = True):
        self.title = title
        self.duration_target_sec = duration_target_sec
        self.narration_text = narration_text
        self.sound_design_notes = sound_design_notes
        self.language = language
        self.fiction_disclaimer = fiction_disclaimer
        self.fiction_disclaimer_audio = fiction_disclaimer_audio
        self.audio_entry_note = audio_entry_note
        self.fiction_disclaimer_required = fiction_disclaimer_required
        self.fiction_disclaimer_in_script = fiction_disclaimer_in_script

    def to_dict(self) -> dict:
        return {
            "title": self.title,
            "duration_target_sec": self.duration_target_sec,
            "language": self.language,
            "narration_text": self.narration_text,
            "sound_design_notes": self.sound_design_notes,
            "fiction_disclaimer": self.fiction_disclaimer,
            "fiction_disclaimer_audio": self.fiction_disclaimer_audio,
            "audio_entry_note": self.audio_entry_note,
            "fiction_disclaimer_required": self.fiction_disclaimer_required,
            "fiction_disclaimer_in_script": self.fiction_disclaimer_in_script,
        }

    def save_json(self, output_path: str):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))

    def save_markdown(self, output_path: str):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        content = f"""# {self.title}

> {FICTION_DISCLAIMER_SHORT}

> Target duration: {self.duration_target_sec}s | Language: {self.language}

## Narration

{self.narration_text}

## Sound Design Notes

{self.sound_design_notes}

---

*{self.fiction_disclaimer}*
"""
        path.write_text(content, encoding='utf-8')
