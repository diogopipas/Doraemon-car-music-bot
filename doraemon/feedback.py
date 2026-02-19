"""Voice feedback using Google Text-to-Speech and mpv for playback.

Uses mpv instead of pygame for audio playback so it works on all platforms
including Termux (Android) where pygame audio is unsupported.
Uses FEEDBACK_LANGUAGE so prompts (Yes?, Stopped, etc.) are in your language.
"""

import hashlib
import shutil
import subprocess
from pathlib import Path

from gtts import gTTS

from . import config

# Cache directory for generated TTS files
_CACHE_DIR = Path(__file__).resolve().parent / "cache"
_CACHE_DIR.mkdir(exist_ok=True)

# Fixed phrases by language (key = first 2 chars of FEEDBACK_LANGUAGE, e.g. "pt", "en").
# Add more languages by adding entries and using FEEDBACK_LANGUAGE=e.g. "es".
PHRASES: dict[str, dict[str, str]] = {
    "en": {
        "yes": "Yes?",
        "sorry": "Sorry, I didn't catch that.",
        "playing": "Playing {title}.",
        "stopped": "Stopped.",
        "goodbye": "Goodbye.",
        "try_again": "Try again?",
        "not_found": "Could not find or play {phrase}.",
        "error": "Something went wrong. Try again.",
    },
    "pt": {
        "yes": "Sim?",
        "sorry": "Não percebi.",
        "playing": "A tocar {title}.",
        "stopped": "Parado.",
        "goodbye": "Adeus.",
        "try_again": "Tenta outra vez?",
        "not_found": "Não encontrei ou não consegui tocar {phrase}.",
        "error": "Algo correu mal. Tenta outra vez.",
    },
}


def _feedback_lang() -> str:
    """Return FEEDBACK_LANGUAGE for gTTS (e.g. 'pt', 'en')."""
    return (getattr(config, "FEEDBACK_LANGUAGE", "en") or "en").strip()[:2].lower() or "en"


def _phrase_lang_key() -> str:
    """Return key for PHRASES dict (e.g. 'pt', 'en')."""
    lang = (getattr(config, "FEEDBACK_LANGUAGE", "en") or "en").strip().lower()
    if lang.startswith("pt"):
        return "pt"
    if lang.startswith("es"):
        return "es"
    return "en"


def _find_mpv() -> str:
    """Return path to mpv executable."""
    path = shutil.which("mpv")
    if not path:
        raise FileNotFoundError(
            "mpv not found. Install it: brew install mpv (macOS), "
            "apt install mpv (Linux), or pkg install mpv (Termux)."
        )
    return path


def _cache_path(text: str, lang: str) -> Path:
    """Path to cached MP3 for this phrase and language."""
    raw = f"{lang}:{text}"
    key = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return _CACHE_DIR / f"{key}.mp3"


def _get_tts_path(text: str, lang: str) -> Path:
    """Return path to MP3 file for text, generating and caching if needed."""
    path = _cache_path(text, lang)
    if path.exists():
        return path
    tts = gTTS(text=text, lang=lang)
    tts.save(str(path))
    return path


def speak_phrase(phrase_key: str, *, block: bool = True, **format_kwargs: str) -> None:
    """
    Speak a fixed phrase in the user's language (FEEDBACK_LANGUAGE).
    phrase_key: one of yes, sorry, playing, stopped, goodbye, try_again, not_found, error.
    format_kwargs: e.g. title="...", phrase="..." for playing / not_found.
    """
    key = _phrase_lang_key()
    phrases = PHRASES.get(key, PHRASES["en"])
    template = phrases.get(phrase_key, PHRASES["en"].get(phrase_key, phrase_key))
    text = template.format(**format_kwargs)
    speak(text, block=block)


def speak(text: str, *, block: bool = True, lang: str | None = None) -> None:
    """
    Speak the given text using Google TTS and mpv for playback.

    If block is True, waits until playback finishes. Otherwise returns immediately.
    lang: override FEEDBACK_LANGUAGE for this utterance (e.g. "pt", "en").
    """
    text = (text or "").strip()
    if not text:
        return
    if lang is None:
        lang = _feedback_lang()
    path = _get_tts_path(text, lang)
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
