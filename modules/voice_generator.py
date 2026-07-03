"""Voice Generator — generate TTS audio or save fallback note."""

from pathlib import Path


def note_not_configured(output_dir: str):
    """Write a TTS_NOT_CONFIGURED note when TTS is unavailable."""
    path = Path(output_dir) / "TTS_NOT_CONFIGURED.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("""# TTS Not Configured

Voice audio was not generated because no TTS provider is configured.

The script is available in `script.md` and `script.json`.
To generate audio:
- Configure a ListenHub API key
- Or use an alternative TTS provider

See: https://docs.colaos.ai/
""", encoding='utf-8')


def save_audio(audio_data: bytes, output_path: str):
    """Save generated audio to a file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(audio_data)
