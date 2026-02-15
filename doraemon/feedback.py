"""Voice feedback using Google Text-to-Speech and mpv for playback.

Uses mpv instead of pygame for audio playback so it works on all platforms
including Termux (Android) where pygame audio is unsupported.
"""

import hashlib
import shutil
import subprocess
from pathlib import Path

from gtts import gTTS

# Cache directory for generated TTS files
_CACHE_DIR = Path(__file__).resolve().parent / "cache"
_CACHE_DIR.mkdir(exist_ok=True)


def _find_mpv() -> str:
    """Return path to mpv executable."""
    path = shutil.which("mpv")
    if not path:
        raise FileNotFoundError(
            "mpv not found. Install it: brew install mpv (macOS), "
            "apt install mpv (Linux), or pkg install mpv (Termux)."
        )
    return path


def _cache_path(text: str) -> Path:
    """Path to cached MP3 for this phrase."""
    key = hashlib.md5(text.encode("utf-8")).hexdigest()
    return _CACHE_DIR / f"{key}.mp3"


def _get_tts_path(text: str) -> Path:
    """Return path to MP3 file for text, generating and caching if needed."""
    path = _cache_path(text)
    if path.exists():
        return path
    tts = gTTS(text=text, lang="en")
    tts.save(str(path))
    return path


def speak(text: str, *, block: bool = True) -> None:
    """
    Speak the given text using Google TTS and mpv for playback.

    If block is True, waits until playback finishes. Otherwise returns immediately.
    """
    text = (text or "").strip()
    if not text:
        return
    path = _get_tts_path(text)
    mpv_path = _find_mpv()
    try:
        cmd = [mpv_path, "--no-video", "--no-terminal", str(path)]
        if block:
            subprocess.run(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            subprocess.Popen(
                cmd,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except Exception:
        pass


def speak_async(text: str) -> None:
    """Speak the text without blocking."""
    speak(text, block=False)
