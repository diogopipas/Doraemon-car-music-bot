"""Load configuration from environment variables."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (parent of doraemon package)
PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")


def _get_str(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _get_int(key: str, default: int) -> int:
    try:
        return int(os.environ.get(key, str(default)))
    except ValueError:
        return default


# Wake word: only "Doraemon" triggers the bot. Recognized via Google Speech Recognition.
WAKE_WORD: str = _get_str("WAKE_WORD", "doraemon")

# Language for TTS feedback. "pt" = Doraemon persona (Portuguese phrases, Spanish accent). E.g. "pt", "en".
FEEDBACK_LANGUAGE: str = _get_str("FEEDBACK_LANGUAGE", "pt")

# Optional: language for recognizing the song name. Defaults to SPEECH_LANGUAGE.
# Set to "en-US" if you say song names in English; keep SPEECH_LANGUAGE for wake word (your language).
_phrase = _get_str("PHRASE_LANGUAGE", "")
PHRASE_LANGUAGE: str | None = _phrase.strip() if _phrase.strip() else None

# Optional: PulseAudio source for mic (Termux). Use "default" or run
# "pactl list sources short" and set to the source name (e.g. mic) if default fails.
PULSE_SOURCE: str = _get_str("PULSE_SOURCE", "default")

# Optional: speech recognition language for the wake word (e.g. "pt-PT", "en-US").
# Set to your language so "Doraemon" is recognized (e.g. pt-PT for Portuguese).
SPEECH_LANGUAGE: str = _get_str("SPEECH_LANGUAGE", "pt-PT")

# Speech recognition timeouts (seconds). Shorter LISTEN_TIMEOUT = faster silence detection.
LISTEN_TIMEOUT: int = _get_int("LISTEN_TIMEOUT", 3)
PHRASE_TIME_LIMIT: int = _get_int("PHRASE_TIME_LIMIT", 10)

# Optional: set to 1 to print wake-word recording diagnostics on Termux
TERMUX_DEBUG: bool = _get_str("TERMUX_DEBUG", "").lower() in ("1", "true", "yes")

# Optional: path for termux-microphone-record output (default: doraemon/cache/termux_rec.opus).
# If recording stays empty, try a path in shared storage, e.g. $HOME/storage/downloads/doraemon_rec.opus
# (run termux-setup-storage first).
TERMUX_RECORD_PATH: str = _get_str("TERMUX_RECORD_PATH")
