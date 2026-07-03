"""Audio Ingest — read audio file metadata using ffmpeg."""

import json
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


class AudioMetadata:
    def __init__(self, file_path: str, duration_sec: float,
                 creation_time: Optional[str] = None,
                 gps_lat: Optional[float] = None,
                 gps_lon: Optional[float] = None):
        self.file_path = file_path
        self.duration_sec = duration_sec
        self.creation_time = creation_time
        self.gps_lat = gps_lat
        self.gps_lon = gps_lon

    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "duration_sec": self.duration_sec,
            "creation_time": self.creation_time,
            "gps_lat": self.gps_lat,
            "gps_lon": self.gps_lon,
        }


def ingest_audio(file_path: str) -> AudioMetadata:
    """Extract metadata from an audio file using ffmpeg."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {file_path}")

    # Get duration
    duration = _get_duration(str(path))

    # Get creation time
    creation_time = _get_creation_time(str(path))

    # Try GPS metadata
    gps_lat, gps_lon = _get_gps(str(path))

    return AudioMetadata(
        file_path=str(path.resolve()),
        duration_sec=duration,
        creation_time=creation_time,
        gps_lat=gps_lat,
        gps_lon=gps_lon,
    )


def _get_duration(file_path: str) -> float:
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", file_path, "-f", "null", "-"],
            capture_output=True, text=True, timeout=30,
        )
        # ffmpeg prints duration to stderr
        for line in result.stderr.split('\n'):
            if 'Duration' in line:
                # Format: Duration: 00:00:42.50
                dur_str = line.split('Duration:')[1].strip().split(',')[0].strip()
                h, m, s = dur_str.split(':')
                return float(h) * 3600 + float(m) * 60 + float(s)
    except Exception:
        pass
    return 0.0


def _get_creation_time(file_path: str) -> Optional[str]:
    try:
        result = subprocess.run(
            ["ffmpeg", "-i", file_path, "-f", "ffmetadata", "-"],
            capture_output=True, text=True, timeout=30,
        )
        for line in result.stdout.split('\n') + result.stderr.split('\n'):
            if 'creation_time' in line.lower():
                val = line.split('=', 1)[-1].strip()
                if val:
                    return val
    except Exception:
        pass

    # Fallback: file stat
    try:
        stat = Path(file_path).stat()
        return datetime.fromtimestamp(stat.st_ctime, tz=timezone.utc).isoformat()
    except Exception:
        pass

    return None


def _get_gps(file_path: str) -> tuple[Optional[float], Optional[float]]:
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_format", "-show_streams", file_path],
            capture_output=True, text=True, timeout=30,
        )
        data = json.loads(result.stdout)
        # Walk through format tags for GPS
        tags = data.get("format", {}).get("tags", {})
        lat = tags.get("location") or tags.get("com.apple.quicktime.location.ISO6709")
        if lat:
            parts = lat.replace("+", "").replace("/", "").split("-")
        return None, None
    except Exception:
        return None, None
