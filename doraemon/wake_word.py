"""Wake word detection using Picovoice Porcupine."""

from pathlib import Path

import pvporcupine

from . import config
from .audio import AudioRecorder


def _create_porcupine():
    """Create Porcupine instance with custom .ppn or built-in keyword."""
    access_key = config.PICOVOICE_ACCESS_KEY
    if not access_key:
        raise ValueError(
            "PICOVOICE_ACCESS_KEY is required. Set it in .env (see .env.example)."
        )

    model_path = (config.WAKE_WORD_MODEL_PATH or "").strip()
    if model_path and Path(model_path).expanduser().exists():
        return pvporcupine.create(
            access_key=access_key,
            keyword_paths=[str(Path(model_path).expanduser().resolve())],
        )
    # Fallback to built-in keyword for testing without custom "Doraemon" model
    return pvporcupine.create(
        access_key=access_key,
        keywords=["computer"],
    )


def wait_for_wake_word(*, stop_event=None):
    """
    Block until the wake word ("Doraemon" or fallback "computer") is detected.

    Uses Porcupine for wake word detection and the platform-aware AudioRecorder
    (PvRecorder on desktop, sox on Termux) for microphone input.
    """
    porcupine = _create_porcupine()
    recorder = AudioRecorder(frame_length=porcupine.frame_length)

    try:
        recorder.start()
        while True:
            if stop_event is not None and stop_event.is_set():
                return False
            frame = recorder.read()
            keyword_index = porcupine.process(frame)
            if keyword_index >= 0:
                return True
    finally:
        recorder.delete()
        porcupine.delete()
