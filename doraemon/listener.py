"""Speech recognition for capturing song names after wake word."""

import io
import os
import shutil
import struct
import subprocess
import tempfile
import time
import wave

import speech_recognition as sr

from . import config
from .audio import IS_TERMUX


def _record_raw_termux(duration: int, sample_rate: int = 16000):
    """
    Record audio in Termux. Prefer termux-microphone-record (real mic) if
    available; otherwise sox + PulseAudio (often only speaker monitor).
    Returns (raw_pcm_bytes, sample_rate) or (None, None).
    """
    sample_width = 2
    termux_rec = shutil.which("termux-microphone-record")
    ffmpeg_path = shutil.which("ffmpeg")
    if termux_rec and ffmpeg_path:
        try:
            with tempfile.NamedTemporaryFile(suffix=".opus", delete=False) as f:
                rec_path = f.name
            subprocess.run(
                [
                    termux_rec,
                    "-l", str(duration),
                    "-f", rec_path,
                    "-e", "opus",
                    "-r", "16000",
                    "-c", "1",
                ],
                capture_output=True,
                timeout=5,
            )
            time.sleep(duration + 1)
            try:
                with open(rec_path, "rb") as f:
                    data = f.read()
            finally:
                try:
                    os.unlink(rec_path)
                except Exception:
                    pass
            if not data or len(data) < 100:
                return None, None
            proc = subprocess.run(
                [
                    ffmpeg_path,
                    "-i", "-",
                    "-f", "s16le",
                    "-acodec", "pcm_s16le",
                    "-ar", str(sample_rate),
                    "-ac", "1",
                    "-",
                ],
                input=data,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
            if proc.returncode == 0 and proc.stdout:
                return proc.stdout, sample_rate
        except Exception:
            pass
        return None, None

    sox_path = shutil.which("sox")
    if not sox_path:
        return None, None
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
                "-c", "1",
                "-",
                "trim", "0", str(duration),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=duration + 5,
        )
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout, sample_rate
    except Exception:
        pass
    return None, None


def _record_wav_termux(duration: int) -> sr.AudioData | None:
    """
    Record audio in Termux and return SpeechRecognition AudioData.
    Uses termux-microphone-record (Termux:API) when available for the real mic;
    otherwise sox + PulseAudio.
    """
    sample_rate = 16000
    sample_width = 2
    raw_data, rate = _record_raw_termux(duration, sample_rate)
    if not raw_data:
        return None
    return sr.AudioData(raw_data, rate, sample_width)


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
