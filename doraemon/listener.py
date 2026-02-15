"""Speech recognition for capturing song names after wake word."""

import io
import shutil
import struct
import subprocess
import wave

import speech_recognition as sr

from . import config
from .audio import IS_TERMUX


def _record_wav_termux(duration: int) -> sr.AudioData | None:
    """
    Record audio using sox in Termux and return it as SpeechRecognition AudioData.

    Since PyAudio/sr.Microphone cannot access the mic in Termux, we capture
    a fixed-length WAV via sox, then wrap it for the recognizer.
    """
    sox_path = shutil.which("sox")
    if not sox_path:
        raise FileNotFoundError(
            "sox not found. In Termux run: pkg install sox pulseaudio"
        )

    sample_rate = 16000
    sample_width = 2  # 16-bit
    channels = 1

    # Record raw PCM bytes for `duration` seconds
    byte_count = sample_rate * sample_width * channels * duration
    frame_count = sample_rate * duration

    pulse_source = config.PULSE_SOURCE or "default"
    try:
        proc = subprocess.run(
            [
                sox_path,
                "-t", "pulseaudio", pulse_source,
                "-t", "raw",
                "-r", str(sample_rate),
                "-b", "16",
                "-e", "signed-integer",
                "-L",
                "-c", str(channels),
                "-",
                "trim", "0", str(duration),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=duration + 5,
        )
        raw_data = proc.stdout
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None

    if not raw_data:
        return None

    # Wrap raw PCM into WAV bytes for SpeechRecognition
    wav_buf = io.BytesIO()
    with wave.open(wav_buf, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(raw_data)
    wav_bytes = wav_buf.getvalue()

    return sr.AudioData(raw_data, sample_rate, sample_width)


def listen_for_song_name() -> str | None:
    """
    Listen to the microphone and return the recognized phrase (song name) or None.

    Uses Google Web Speech API. On desktop, uses sr.Microphone (PyAudio).
    On Termux, captures audio via sox and feeds it to the recognizer.
    """
    recognizer = sr.Recognizer()

    if IS_TERMUX:
        audio = _record_wav_termux(duration=config.PHRASE_TIME_LIMIT)
        if audio is None:
            return None
    else:
        with sr.Microphone() as source:
            try:
                recognizer.adjust_for_ambient_noise(source, duration=0.3)
                audio = recognizer.listen(
                    source,
                    timeout=config.LISTEN_TIMEOUT,
                    phrase_time_limit=config.PHRASE_TIME_LIMIT,
                )
            except sr.WaitTimeoutError:
                return None

    kwargs = {}
    if config.SPEECH_LANGUAGE:
        kwargs["language"] = config.SPEECH_LANGUAGE
    try:
        text = recognizer.recognize_google(audio, **kwargs)
        return (text or "").strip() or None
    except sr.UnknownValueError:
        return None
    except sr.RequestError:
        return None
