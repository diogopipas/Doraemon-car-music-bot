"""Load configuration from environment variables."""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env from project root (parent of doraemon package)
_project_root = Path(__file__).resolve().parent.parent
load_dotenv(_project_root / ".env")


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
WAKE_WORD_MODEL_PATH: str = _get_str("WAKE_WORD_MODEL_PATH")

# Optional: speech recognition timeouts (seconds)
LISTEN_TIMEOUT: int = _get_int("LISTEN_TIMEOUT", 5)
PHRASE_TIME_LIMIT: int = _get_int("PHRASE_TIME_LIMIT", 10)

# Porcupine frame length (samples per frame at 16kHz)
PORCUPINE_FRAME_LENGTH = 512
PORCUPINE_SAMPLE_RATE = 16000
