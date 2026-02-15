"""
Wake word detection.

On desktop (macOS/Linux/Windows): uses Picovoice Porcupine for efficient,
always-on wake word detection with low latency.

On Termux (Android): Porcupine's Python SDK does not support Android CPUs,
so we fall back to recording short audio clips with sox and checking them
against Google Speech Recognition for the wake word.
"""

from pathlib import Path

from . import config
from .audio import IS_TERMUX


# ---------------------------------------------------------------------------
# Porcupine backend (desktop only)
# ---------------------------------------------------------------------------

def _create_porcupine():
    """Create Porcupine instance with custom .ppn or built-in keyword."""
    import pvporcupine  # imported here so Termux never loads it

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


def _wait_porcupine(*, stop_event=None) -> bool:
    """Desktop path: use Porcupine for wake word detection."""
    from .audio import AudioRecorder

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


# ---------------------------------------------------------------------------
# Speech-recognition backend (Termux fallback)
# ---------------------------------------------------------------------------

def _wait_speech_recognition(*, stop_event=None) -> bool:
    """
    Termux path: continuously record short clips with sox and run speech
    recognition to detect the wake word.

    Records 2-second segments in a loop.  If the recognized text contains
    the configured wake word (default "doraemon"), returns True.
    """
    import io
    import shutil
    import struct
    import subprocess
    import wave

    import speech_recognition as sr

    wake_word = config.WAKE_WORD.lower()
    segment_duration = 2  # seconds per listening segment
    sample_rate = config.PORCUPINE_SAMPLE_RATE  # 16 000 Hz
    sample_width = 2  # 16-bit
    channels = 1

    sox_path = shutil.which("sox")
    if not sox_path:
        raise FileNotFoundError(
            "sox not found. In Termux run: pkg install sox pulseaudio"
        )

    recognizer = sr.Recognizer()
    print(f"[Termux] Listening for wake word \"{config.WAKE_WORD}\" …")

    while True:
        if stop_event is not None and stop_event.is_set():
            return False

        # Record a short segment
        try:
            proc = subprocess.run(
                [
                    sox_path,
                    "-t", "pulseaudio", "default",
                    "-t", "raw",
                    "-r", str(sample_rate),
                    "-b", "16",
                    "-e", "signed-integer",
                    "-L",
                    "-c", str(channels),
                    "-",
                    "trim", "0", str(segment_duration),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=segment_duration + 5,
            )
            raw_data = proc.stdout
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue

        if not raw_data:
            continue

        # Wrap raw PCM in AudioData for SpeechRecognition
        audio = sr.AudioData(raw_data, sample_rate, sample_width)

        try:
            text = recognizer.recognize_google(audio)
        except (sr.UnknownValueError, sr.RequestError):
            continue

        if text and wake_word in text.lower():
            return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def wait_for_wake_word(*, stop_event=None) -> bool:
    """
    Block until the wake word is detected.

    On desktop: uses Porcupine (efficient, offline).
    On Termux:  uses sox + Google Speech Recognition (online fallback).
    """
    if IS_TERMUX:
        return _wait_speech_recognition(stop_event=stop_event)
    return _wait_porcupine(stop_event=stop_event)
