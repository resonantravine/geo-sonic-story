"""Metadata Extractor — robust audio metadata extraction.

Priority: ExifTool → ffprobe → filesystem stats.

Clearly distinguishes between embedded GPS, geocoded from user input,
and manual unresolved location.
"""

import json
import os
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ── Public data classes ──

class AudioMetadata:
    def __init__(self, audio_file: str, duration_sec: float,
                 recording_time: Optional[str] = None,
                 recording_time_source: Optional[str] = None,
                 recording_time_confidence: str = "none",
                 original_detected_time: Optional[str] = None,
                 user_override_time: Optional[str] = None,
                 lat: Optional[float] = None,
                 lon: Optional[float] = None,
                 location_source: Optional[str] = None,
                 location_confidence: str = "none",
                 location_precision: Optional[str] = None,
                 needs_manual_location: bool = True,
                 location_note: Optional[str] = None):
        self.audio_file = audio_file
        self.duration_sec = duration_sec
        self.recording_time = recording_time
        self.recording_time_source = recording_time_source
        self.recording_time_confidence = recording_time_confidence
        self.original_detected_time = original_detected_time
        self.user_override_time = user_override_time
        self.lat = lat
        self.lon = lon
        self.location_source = location_source
        self.location_confidence = location_confidence
        self.location_precision = location_precision
        self.needs_manual_location = needs_manual_location
        self.location_note = location_note

    def to_dict(self) -> dict:
        d = {
            "audio_file": self.audio_file,
            "duration_sec": self.duration_sec,
            "recording_time": self.recording_time,
            "recording_time_source": self.recording_time_source,
            "recording_time_confidence": self.recording_time_confidence,
            "lat": self.lat,
            "lon": self.lon,
            "location_source": self.location_source,
            "location_confidence": self.location_confidence,
            "location_precision": self.location_precision,
            "needs_manual_location": self.needs_manual_location,
        }
        if self.original_detected_time:
            d["original_detected_time"] = self.original_detected_time
        if self.user_override_time:
            d["user_override_time"] = self.user_override_time
        if self.location_note:
            d["location_note"] = self.location_note
        return d

    def save(self, output_path: str):
        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=False))


# ── ExifTool ──

_EXIFTOOL_TIME_FIELDS = [
    "DateTimeOriginal", "CreateDate", "CreationDate",
    "MediaCreateDate", "TrackCreateDate", "ModifyDate", "FileModifyDate",
]

_EXIFTOOL_GPS_FIELDS = [
    "GPSLatitude", "GPSLongitude", "GPSPosition",
    "GPSCoordinates", "Location",
]


def _find_exiftool() -> Optional[str]:
    """Locate the exiftool binary."""
    for candidate in ["exiftool", "/usr/local/bin/exiftool", "/opt/homebrew/bin/exiftool"]:
        try:
            r = subprocess.run([candidate, "-ver"], capture_output=True, text=True, timeout=5)
            if r.returncode == 0:
                return candidate
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    return None


def _extract_via_exiftool(audio_file: str) -> Optional[dict]:
    """Extract metadata using ExifTool. Returns dict of fields or None."""
    exiftool = _find_exiftool()
    if not exiftool:
        return None

    try:
        result = subprocess.run(
            [exiftool, "-j", "-api", "QuickTimeUTC=1", "-ee", audio_file],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        if not data:
            return None
        return data[0]  # first element of JSON array
    except Exception:
        return None


def _parse_iso6709(value: str) -> Optional[tuple[float, float]]:
    """Parse ISO 6709 coordinate string, e.g. '+39.928900+116.388300+000.000/'."""
    # Pattern: ±DD.DDDDDD±DDD.DDDDDD±DDD.DDDD/
    match = re.match(r'([+-]\d+\.\d+)\s*([+-]\d+\.\d+)', value)
    if match:
        return float(match.group(1)), float(match.group(2))
    return None


def _extract_time_from_exiftool(data: dict) -> Optional[tuple[str, str, str]]:
    """Extract recording time from ExifTool output. Returns (time, source, confidence)."""
    for field in _EXIFTOOL_TIME_FIELDS:
        val = data.get(field)
        if val and val != "0000:00:00 00:00:00":
            try:
                # ExifTool format: "2026:06:27 19:48:39"
                dt = datetime.strptime(str(val).split("+")[0].split("-")[0].strip(),
                                       "%Y:%m:%d %H:%M:%S")
                return dt.replace(tzinfo=timezone.utc).isoformat(), f"exiftool:{field}", "high"
            except ValueError:
                pass
    return None


def _extract_gps_from_exiftool(data: dict) -> Optional[tuple[float, float, str, str, str]]:
    """Extract GPS from ExifTool. Returns (lat, lon, source, confidence, precision)."""
    for field in _EXIFTOOL_GPS_FIELDS:
        val = data.get(field)
        if not val:
            continue

        # Try numeric lat/lon fields
        if field in ("GPSLatitude", "GPSLongitude"):
            lat = data.get("GPSLatitude", "")
            lon = data.get("GPSLongitude", "")
            # ExifTool returns "39.9289 N" or "39 deg 55' 44.04\" N"
            lat_val = _parse_gps_dms(lat) if isinstance(lat, str) else float(lat) if lat else None
            lon_val = _parse_gps_dms(lon) if isinstance(lon, str) else float(lon) if lon else None
            if lat_val is not None and lon_val is not None:
                return lat_val, lon_val, "embedded_gps", "high", "dms_to_decimal"

        # Try position string
        if isinstance(val, str):
            coords = _parse_iso6709(val)
            if coords:
                return coords[0], coords[1], "embedded_gps", "high", "iso6709"

            # Try "39.9289, 116.3883" format
            parts = re.split(r'[,;\s]+', val)
            if len(parts) >= 2:
                try:
                    return float(parts[0]), float(parts[1]), "embedded_gps", "medium", "raw_string"
                except ValueError:
                    pass

    # Check location.ISO6709 in nested structure
    for key in data:
        if "iso6709" in key.lower() or "location" in key.lower():
            val = data[key]
            if isinstance(val, str):
                coords = _parse_iso6709(val)
                if coords:
                    return coords[0], coords[1], "embedded_gps", "high", "iso6709_nested"

    return None


def _parse_gps_dms(value: str) -> Optional[float]:
    """Parse GPS in DMS format like '39 deg 55\\' 44.04\" N' or '39.9289 N'."""
    if not value:
        return None
    # Simple decimal: "39.9289 N" or "39.9289"
    simple = re.match(r'([+-]?\d+\.?\d*)\s*[NSEW]?', str(value).strip())
    if simple:
        val = float(simple.group(1))
        direction = str(value).strip()[-1].upper()
        if direction in ('S', 'W'):
            val = -val
        return val

    # DMS: "39 deg 55' 44.04\" N"
    dms = re.match(r'(\d+)\s*deg\s+(\d+)\s*[\'′]\s*([\d.]+)\s*[\"″]\s*([NSEW])?', str(value))
    if dms:
        deg, minutes, seconds = float(dms.group(1)), float(dms.group(2)), float(dms.group(3))
        decimal = deg + minutes / 60 + seconds / 3600
        direction = dms.group(4)
        if direction and direction.upper() in ('S', 'W'):
            decimal = -decimal
        return decimal

    return None


# ── Filename timestamp parser ──

def _parse_filename_timestamp(audio_file: str) -> Optional[str]:
    """Parse recording time from filename patterns like:
    - '260627_194839.m4a' → 2026-06-27 19:48:39
    - '20260627_194839.m4a' → 2026-06-27 19:48:39
    - '2026-06-27 19.48.39.m4a' → 2026-06-27 19:48:39
    """
    basename = Path(audio_file).stem

    # Try YYMMDD_HHMMSS anywhere in filename (e.g. "q1 Voice 260627_194839")
    m = re.search(r'(\d{2})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', basename)
    if m:
        yy, mm, dd, hh, mi, ss = m.groups()
        year = 2000 + int(yy)
        # Sanity check: year should be 2000-2099
        if 0 <= int(yy) <= 99:
            try:
                return datetime(year, int(mm), int(dd), int(hh), int(mi), int(ss),
                               tzinfo=timezone.utc).isoformat()
            except ValueError:
                pass

    # Try YYYYMMDD_HHMMSS anywhere in filename
    m = re.search(r'(\d{4})(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})', basename)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                           int(m.group(4)), int(m.group(5)), int(m.group(6)),
                           tzinfo=timezone.utc).isoformat()
        except ValueError:
            pass

    # Try ISO-like: YYYY-MM-DD HH.MM.SS anywhere
    m = re.search(r'(\d{4})-(\d{2})-(\d{2})\s+(\d{2})\.(\d{2})\.(\d{2})', basename)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                           int(m.group(4)), int(m.group(5)), int(m.group(6)),
                           tzinfo=timezone.utc).isoformat()
        except ValueError:
            pass

    return None


# ── ffprobe/ffmpeg fallback ──

def _extract_via_ffprobe(audio_file: str) -> dict:
    """Extract metadata using ffprobe (or ffmpeg if ffprobe unavailable)."""
    result = {
        "duration_sec": 0.0,
        "creation_time": None,
        "tags": {},
    }

    # Try ffprobe first
    probe_bin = None
    for candidate in ["ffprobe", "/usr/local/bin/ffprobe"]:
        try:
            r = subprocess.run([candidate, "-version"], capture_output=True, timeout=5)
            if r.returncode == 0:
                probe_bin = candidate
                break
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass

    # Fall back to ffmpeg
    ffmpeg_bin = None
    if not probe_bin:
        for candidate in ["ffmpeg", "/usr/local/bin/ffmpeg"]:
            try:
                r = subprocess.run([candidate, "-version"], capture_output=True, timeout=5)
                if r.returncode == 0:
                    ffmpeg_bin = candidate
                    break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                pass

    if probe_bin:
        try:
            r = subprocess.run(
                [probe_bin, "-v", "quiet", "-print_format", "json",
                 "-show_format", "-show_streams", audio_file],
                capture_output=True, text=True, timeout=30,
            )
            if r.returncode == 0 and r.stdout.strip():
                data = json.loads(r.stdout)
                fmt = data.get("format", {})
                dur = fmt.get("duration")
                if dur:
                    result["duration_sec"] = float(dur)
                tags = fmt.get("tags", {})
                result["tags"] = tags
                for key in ("creation_time", "CreationTime", "date", "DATE"):
                    val = tags.get(key)
                    if val:
                        result["creation_time"] = val
                        break
        except Exception:
            pass

    # ffmpeg fallback for duration only
    if result["duration_sec"] == 0.0 and ffmpeg_bin:
        try:
            r = subprocess.run(
                [ffmpeg_bin, "-i", audio_file, "-f", "null", "-"],
                capture_output=True, text=True, timeout=30,
            )
            for line in r.stderr.split('\n'):
                if 'Duration' in line:
                    dur_str = line.split('Duration:')[1].strip().split(',')[0].strip()
                    h, m, s = dur_str.split(':')
                    result["duration_sec"] = float(h) * 3600 + float(m) * 60 + float(s)
                    break
        except Exception:
            pass

    return result


# ── File system fallback ──

def _get_filesystem_time(audio_file: str) -> str:
    """Get file modification time as ISO string."""
    try:
        stat = os.stat(audio_file)
        return datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat()
    except Exception:
        return datetime.now(timezone.utc).isoformat()


# ── Main extract function ──

def extract(audio_file: str,
            user_location: Optional[str] = None,
            user_lat: Optional[float] = None,
            user_lon: Optional[float] = None) -> AudioMetadata:
    """Extract all metadata from an audio file.

    Priority: ExifTool → ffprobe → filesystem.
    GPS: embedded metadata → geocoded from user input → manual unresolved.
    """
    path = Path(audio_file)
    if not path.exists():
        raise FileNotFoundError(f"Audio file not found: {audio_file}")

    absolute_path = str(path.resolve())
    duration = 0.0
    recording_time = None
    recording_time_source = None
    recording_time_confidence = "none"
    lat = None
    lon = None
    location_source = None
    location_confidence = "none"
    location_precision = None
    needs_manual_location = True

    # Initialize location_note
    location_note = None

    # ── Step 1: Try ExifTool ──
    exif_data = _extract_via_exiftool(absolute_path)
    if exif_data:
        # Time
        time_result = _extract_time_from_exiftool(exif_data)
        if time_result:
            recording_time, recording_time_source, recording_time_confidence = time_result

        # GPS
        gps_result = _extract_gps_from_exiftool(exif_data)
        if gps_result:
            lat, lon, location_source, location_confidence, location_precision = gps_result
            needs_manual_location = False

    # ── Step 2: ffprobe fallback ──
    if duration == 0.0 or recording_time is None:
        ffprobe_data = _extract_via_ffprobe(absolute_path)
        if ffprobe_data["duration_sec"] and duration == 0.0:
            duration = ffprobe_data["duration_sec"]

        if recording_time is None:
            ct = ffprobe_data.get("creation_time")
            if ct:
                recording_time = ct
                recording_time_source = "ffprobe:creation_time"
                recording_time_confidence = "medium"

    # ── Step 2b: Filename timestamp ──
    if recording_time_confidence in ("none", "low"):
        original_detected_time = recording_time
        filename_time = _parse_filename_timestamp(absolute_path)
        if filename_time:
            recording_time = filename_time
            recording_time_source = "filename_parsed"
            recording_time_confidence = "medium_high"
            # Store original detected time for user override tracking
            _original_detected_time = original_detected_time

    # ── Step 3: Filesystem fallback for time ──
    if recording_time is None:
        recording_time = _get_filesystem_time(absolute_path)
        recording_time_source = "filesystem:modified_time"
        recording_time_confidence = "low"

    # ── Step 4: Handle user-provided location ──
    if needs_manual_location:
        if user_lat is not None and user_lon is not None:
            lat = user_lat
            lon = user_lon
            location_source = "manual_coordinates"
            location_confidence = "high" if user_location else "medium"
            location_precision = "user_provided"
            needs_manual_location = False
        elif user_location:
            # Try geocoding from user-provided place name
            geocoded = _geocode_place(user_location)
            if geocoded:
                lat, lon = geocoded
                location_source = "geocoded_from_user_input"
                location_confidence = "medium"
                location_precision = "place_name"
                location_note = "No embedded GPS found. Coordinates were geocoded from user-provided location text."
                needs_manual_location = False
            else:
                location_source = "manual_unresolved"
                location_confidence = "low"
                location_note = "No embedded GPS found. Manual location could not be geocoded."
                needs_manual_location = True
        else:
            location_source = "manual_unresolved"
            location_confidence = "none"

    return AudioMetadata(
        audio_file=absolute_path,
        duration_sec=duration,
        recording_time=recording_time,
        recording_time_source=recording_time_source,
        recording_time_confidence=recording_time_confidence,
        lat=lat,
        lon=lon,
        location_source=location_source,
        location_confidence=location_confidence,
        location_precision=location_precision,
        needs_manual_location=needs_manual_location,
        location_note=location_note,
    )


# ── Simple geocoding (place name → lat/lon) ──

def _geocode_place(place: str) -> Optional[tuple[float, float]]:
    """Very simple geocoding using a built-in lookup for common places.
    In production, use a real geocoding API (Google, Nominatim, etc.)
    """
    # Beijing landmarks
    known = {
        "北京": (39.9042, 116.4074),
        "北京市": (39.9042, 116.4074),
        "西城区": (39.9122, 116.3658),
        "北京西城区": (39.9122, 116.3658),
        "新风街": (39.9510, 116.3612),  # Approximate
        "北京西城区新风街": (39.9510, 116.3612),
        "德胜门外": (39.9530, 116.3720),
    }

    # Exact match
    if place in known:
        return known[place]

    # Substring match
    for key, coords in known.items():
        if key in place or place in key:
            return coords

    return None
