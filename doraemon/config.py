"""Load configuration from environment variables."""

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


# Required
PICOVOICE_ACCESS_KEY: str = _get_str("PICOVOICE_ACCESS_KEY")

# Optional: path to custom wake word .ppn file (e.g. "Doraemon")
# Use a path matching your platform (Android .ppn on Termux, macOS .ppn on Mac).
# Relative paths are resolved from PROJECT_ROOT so the same .env works on both.
WAKE_WORD_MODEL_PATH: str = _get_str("WAKE_WORD_MODEL_PATH")

# Wake word phrase for Termux speech-recognition fallback (default: "doraemon")
WAKE_WORD: str = _get_str("WAKE_WORD", "doraemon")

# Optional: PulseAudio source for mic (Termux). Use "default" or run
# "pactl list sources short" and set to the source name (e.g. mic) if default fails.
PULSE_SOURCE: str = _get_str("PULSE_SOURCE", "default")

# Optional: speech recognition language (e.g. "en-US", "pt-PT"). Empty = auto.
# Helps Google recognize words; set to your language if "no speech detected" often.
SPEECH_LANGUAGE: str = _get_str("SPEECH_LANGUAGE", "en-US")

# Optional: speech recognition timeouts (seconds)
LISTEN_TIMEOUT: int = _get_int("LISTEN_TIMEOUT", 5)
PHRASE_TIME_LIMIT: int = _get_int("PHRASE_TIME_LIMIT", 10)

# Optional: set to 1 to print wake-word recording diagnostics on Termux
TERMUX_DEBUG: bool = _get_str("TERMUX_DEBUG", "").lower() in ("1", "true", "yes")

# Optional: path for termux-microphone-record output (default: doraemon/cache/termux_rec.opus).
# If recording stays empty, try a path in shared storage, e.g. $HOME/storage/downloads/doraemon_rec.opus
# (run termux-setup-storage first).
TERMUX_RECORD_PATH: str = _get_str("TERMUX_RECORD_PATH")

# Porcupine frame length (samples per frame at 16kHz)
PORCUPINE_FRAME_LENGTH = 512
PORCUPINE_SAMPLE_RATE = 16000
