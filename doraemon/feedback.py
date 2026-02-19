"""Voice feedback using Google Text-to-Speech and mpv for playback.

Uses mpv for playback on all platforms including Termux.
Doraemon persona: Portuguese phrases with Spanish-accent TTS (lang=es).
Optional pre-recorded assets in doraemon/assets/ for instant "Si?" and "Ah claro amigo!".
"""
from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path

from gtts import gTTS

from . import config

# Cache directory for generated TTS files
_CACHE_DIR = Path(__file__).resolve().parent / "cache"
_CACHE_DIR.mkdir(exist_ok=True)

# Optional pre-recorded clips (Spanish accent, Portuguese) for fastest response
_ASSETS_DIR = Path(__file__).resolve().parent / "assets"
_ASSETS_DIR.mkdir(exist_ok=True)

# Fixed phrases by language. "doraemon" = Portuguese text, spoken with Spanish accent (TTS lang=es).
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
    "doraemon": {
        "yes": "Si?",
        "sorry": "Não percebi.",
        "playing": "Ah claro amigo!",
        "stopped": "Parado.",
        "goodbye": "Adeus.",
        "try_again": "Tenta outra vez?",
        "not_found": "Não encontrei. Tenta outra vez?",
        "error": "Algo correu mal. Tenta outra vez.",
    },
}


def _phrase_lang_key() -> str:
    """Return key for PHRASES dict. pt => doraemon persona (Portuguese + Spanish accent)."""
    lang = (getattr(config, "FEEDBACK_LANGUAGE", "pt") or "pt").strip().lower()
    if lang.startswith("pt"):
        return "doraemon"
    if lang.startswith("es"):
        return "es"
    return "en"


def _feedback_lang() -> str:
    """Return gTTS lang: Spanish (es) for Doraemon persona, else FEEDBACK_LANGUAGE."""
    key = _phrase_lang_key()
    if key == "doraemon":
        return "es"  # Spanish accent for Portuguese phrases
    return (getattr(config, "FEEDBACK_LANGUAGE", "pt") or "pt").strip()[:2].lower() or "en"


def _find_mpv() -> str:
    """Return path to mpv executable."""
    path = shutil.which("mpv")
    if not path:
        raise FileNotFoundError(
            "mpv not found. Install it: brew install mpv (macOS), "
            "apt install mpv (Linux), or pkg install mpv (Termux)."
        )
    return path


def _cache_path(text: str, lang: str, tld: str = "com") -> Path:
    """Path to cached MP3 for this phrase, language and TLD (accent)."""
    raw = f"{lang}:{tld}:{text}"
    key = hashlib.md5(raw.encode("utf-8")).hexdigest()
    return _CACHE_DIR / f"{key}.mp3"


def _get_tts_path(text: str, lang: str, tld: str = "es") -> Path:
    """Return path to MP3 file for text, generating and caching if needed."""
    path = _cache_path(text, lang, tld)
    if path.exists():
        return path
    tts = gTTS(text=text, lang=lang, tld=tld)
    tts.save(str(path))
    return path


def _play_audio_file(path: Path, *, block: bool = True) -> None:
    """Play an audio file (e.g. pre-recorded asset) with mpv."""
    mpv_path = _find_mpv()
    cmd = [mpv_path, "--no-video", "--no-terminal", str(path)]
    try:
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


def speak_phrase(phrase_key: str, *, block: bool = True, **format_kwargs: str) -> None:
    """
    Speak a fixed phrase. Uses pre-recorded assets if present (si.mp3, ah_claro_amigo.mp3).
    phrase_key: one of yes, sorry, playing, stopped, goodbye, try_again, not_found, error.
    format_kwargs: e.g. title="...", phrase="..." for playing / not_found (ignored for doraemon "playing").
    """
    key = _phrase_lang_key()
    # Pre-recorded clips for instant, character-accurate response
    if phrase_key == "yes":
        si_mp3 = _ASSETS_DIR / "si.mp3"
        if si_mp3.exists():
            _play_audio_file(si_mp3, block=block)
            return
    if phrase_key == "playing":
        ah_claro = _ASSETS_DIR / "ah_claro_amigo.mp3"
        if ah_claro.exists():
            _play_audio_file(ah_claro, block=block)
            return
    phrases = PHRASES.get(key, PHRASES["en"])
    template = phrases.get(phrase_key, PHRASES["en"].get(phrase_key, phrase_key))
    # Doraemon "playing" has no placeholder; others might
    try:
        text = template.format(**format_kwargs)
    except KeyError:
        text = template
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
    tld = "es" if lang == "es" else "com"
    path = _get_tts_path(text, lang, tld=tld)
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
