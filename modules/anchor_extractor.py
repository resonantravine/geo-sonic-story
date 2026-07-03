"""Anchor Extractor — extract or accept location, time, and sound cues."""

import json
from pathlib import Path
from typing import Optional


class AnchorData:
    def __init__(self, audio_file: str, duration_sec: float,
                 recording_time: Optional[str] = None,
                 location_text: Optional[str] = None,
                 lat: Optional[float] = None,
                 lon: Optional[float] = None,
                 location_source: str = "manual",
                 sound_cues: Optional[list[str]] = None):
        self.audio_file = audio_file
        self.duration_sec = duration_sec
        self.recording_time = recording_time
        self.location_text = location_text
        self.lat = lat
        self.lon = lon
        self.location_source = location_source
        self.sound_cues = sound_cues or []

    def to_dict(self) -> dict:
        return {
            "audio_file": self.audio_file,
            "duration_sec": self.duration_sec,
            "recording_time": self.recording_time,
            "location_source": self.location_source,
            "location_text": self.location_text,
            "lat": self.lat,
            "lon": self.lon,
            "sound_cues": self.sound_cues,
        }

    def save(self, output_path: str):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))


def build_anchor(audio_file: str, duration_sec: float,
                 recording_time: Optional[str] = None,
                 location: Optional[str] = None,
                 lat: Optional[float] = None,
                 lon: Optional[float] = None,
                 sound_cues: Optional[list[str]] = None) -> AnchorData:
    """Build anchor data from user-provided inputs."""
    return AnchorData(
        audio_file=audio_file,
        duration_sec=duration_sec,
        recording_time=recording_time,
        location_text=location,
        lat=lat,
        lon=lon,
        location_source="gps" if (lat is not None and lon is not None) else "manual",
        sound_cues=sound_cues or [],
    )
