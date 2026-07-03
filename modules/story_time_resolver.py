"""Story Time Resolver — parse user time input into a resolved period."""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class StoryTime:
    def __init__(self, story_time_input: str,
                 recording_time: Optional[str],
                 resolved_label: str,
                 start_year: int,
                 end_year: int):
        self.story_time_input = story_time_input
        self.recording_time = recording_time
        self.resolved_label = resolved_label
        self.start_year = start_year
        self.end_year = end_year

    def to_dict(self) -> dict:
        return {
            "story_time_input": self.story_time_input,
            "recording_time": self.recording_time,
            "resolved_story_period": {
                "label": self.resolved_label,
                "start_year": self.start_year,
                "end_year": self.end_year,
            },
        }

    def save(self, output_path: str):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))


def resolve(story_time_input: str, recording_time: Optional[str] = None) -> StoryTime:
    """Resolve a user-friendly time input into a numeric year range."""
    now = datetime.now(timezone.utc)
    ref_year = now.year

    if recording_time:
        try:
            ref_year = int(recording_time[:4])
        except (ValueError, TypeError):
            pass

    inp = story_time_input.strip().lower()

    # Handle common patterns
    if inp in ("present day", "present", "now", "当前", "现在"):
        return StoryTime(story_time_input, recording_time,
                         f"present day (around {ref_year})",
                         ref_year - 2, ref_year)

    # "100 years ago"
    import re
    match = re.match(r'(\d+)\s+years?\s+ago', inp)
    if match:
        delta = int(match.group(1))
        year = ref_year - delta
        return StoryTime(story_time_input, recording_time,
                         f"around {year}",
                         year - 8, year + 7)

    # "the 1980s", "1980s"
    match = re.match(r'(?:the\s+)?(\d{4})s?$', inp)
    if match:
        decade_start = int(match.group(1))
        return StoryTime(story_time_input, recording_time,
                         f"the {decade_start}s",
                         decade_start, decade_start + 9)

    # Specific year: "2010", "1926"
    match = re.match(r'^(\d{4})$', inp)
    if match:
        year = int(match.group(1))
        return StoryTime(story_time_input, recording_time,
                         f"around {year}",
                         year - 5, year + 5)

    # "late 19th century"
    century_map = {
        "19th": (1850, 1900), "20th": (1900, 1950), "21st": (2000, 2050),
    }
    for century, (start, end) in century_map.items():
        if century in inp:
            if "late" in inp:
                return StoryTime(story_time_input, recording_time,
                                 f"late {century} century",
                                 end - 30, end)
            if "early" in inp:
                return StoryTime(story_time_input, recording_time,
                                 f"early {century} century",
                                 start, start + 30)
            return StoryTime(story_time_input, recording_time,
                             f"mid {century} century",
                             start + 20, end - 20)

    # Fallback: treat as literal, try to extract year
    digits = re.findall(r'\d{4}', inp)
    if digits:
        year = int(digits[0])
        return StoryTime(story_time_input, recording_time,
                         f"around {year}",
                         year - 5, year + 5)

    # Default: present
    return StoryTime(story_time_input, recording_time,
                     f"present day (around {ref_year})",
                     ref_year - 2, ref_year)
