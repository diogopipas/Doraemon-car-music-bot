"""
Wake word detection (Android/Termux only).

Uses termux-microphone-record (or sox + PulseAudio) and Google Speech Recognition
to detect "Doraemon" only. No Picovoice — it does not work on Termux.
"""

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from . import config


def _normalise_phrase(s: str) -> str:
    """Strip spaces, hyphens, punctuation for fuzzy match."""
    import re
    return re.sub(r"[\s\-'\".,!?]+", "", s.lower())


# Normalized forms Google might use for "Doraemon"
_WAKE_NORMALIZED_FORMS = frozenset({
    "doraemon",
    "doramon",   # single m
    "doraimon", # with i
})


def _matches_wake_word(text: str, wake_word: str) -> bool:
    """
    Check whether *text* is or contains "Doraemon" (or common mishearings).
    Tolerates transcription variants and spelling (Doramon, Dora e mon, etc.).
    """
    if not (text or "").strip():
        return False
    normalise = _normalise_phrase
    target = normalise(text)
    # Exact match (user said only "Doraemon")
    if target in _WAKE_NORMALIZED_FORMS:
        return True
    # Wake word appears inside what was said
    for form in _WAKE_NORMALIZED_FORMS:
        if form in target:
            return True
    return False


# Sample rate for Google Speech Recognition (16 kHz is standard)
SAMPLE_RATE = 16000


def _record_segment_termux(duration_sec: int, sample_rate: int):
    """
    Record a short segment on Termux. Prefer termux-microphone-record (real mic)
    if available; otherwise fall back to sox + PulseAudio (often only captures
    speaker monitor, not mic).

    Returns (raw_pcm_bytes, sample_rate) or (None, None) on failure.
    """
    import time

    debug = getattr(config, "TERMUX_DEBUG", False)

    # 1) Try Termux:API microphone (actual mic on Android)
    _limit_opt = "-l"
    termux_rec = shutil.which("termux-microphone-record")
    ffmpeg_path = shutil.which("ffmpeg")
    if termux_rec and ffmpeg_path:
        try:
            time.sleep(0.4)
            cache_dir = Path(__file__).resolve().parent / "cache"
            cache_dir.mkdir(exist_ok=True)
            rec_path = str(cache_dir / f"termux_rec_{time.monotonic_ns()}.opus")
            subprocess.run(
                [
                    termux_rec,
                    _limit_opt,
                    str(duration_sec),
                    "-f", rec_path,
                    "-e", "opus",
                    "-r", "16000",
                    "-c", "1",
                ],
                capture_output=True,
                timeout=duration_sec + 8,
            )
            time.sleep(max(1.0, duration_sec * 0.3))
            data = b""
            for _ in range(5):
                try:
                    with open(rec_path, "rb") as f:
                        data = f.read()
                except FileNotFoundError:
                    pass
                if data and len(data) >= 100:
                    break
                time.sleep(1)
            try:
                os.unlink(rec_path)
            except Exception:
                pass
            if data and len(data) >= 100:
                if debug:
                    print(f"[Termux debug] opus file: {len(data)} bytes")
                with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as tmp:
                    tmp.write(data)
                    tmp_path = tmp.name
                try:
                    opusdec_path = shutil.which("opusdec")
                    if opusdec_path:
                        proc = subprocess.run(
                            [
                                opusdec_path,
                                "--rate", str(sample_rate),
                                "--quiet",
                                tmp_path,
                                "-",
                            ],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            timeout=10,
                        )
                        if proc.returncode == 0 and proc.stdout:
                            if debug:
                                print(f"[Termux debug] PCM: {len(proc.stdout)} bytes (opusdec)")
                            return proc.stdout, sample_rate
                        if debug and proc.stderr:
                            err = proc.stderr.decode("utf-8", errors="replace").strip()
                            print(f"[Termux debug] opusdec failed: {err[:150]}")
                    proc = subprocess.run(
                        [
                            ffmpeg_path,
                            "-y",
                            "-i", tmp_path,
                            "-f", "s16le",
                            "-ar", str(sample_rate),
                            "-ac", "1",
                            "-",
                        ],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=10,
                    )
                    if proc.returncode == 0 and proc.stdout:
                        if debug:
                            print(f"[Termux debug] PCM: {len(proc.stdout)} bytes (ffmpeg)")
                        return proc.stdout, sample_rate
                    if debug and proc.stderr:
                        err = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
                        print(f"[Termux debug] ffmpeg failed: {err[:200]}")
                finally:
                    try:
                        os.unlink(tmp_path)
                    except Exception:
                        pass
            elif debug:
                print(f"[Termux debug] termux-microphone-record: no data (file empty or missing)")
        except subprocess.TimeoutExpired:
            if not getattr(_record_segment_termux, "_timeout_warned", False):
                _record_segment_termux._timeout_warned = True
                print(
                    "[Termux] termux-microphone-record timed out; using PulseAudio (sox) for mic. "
                    "If you need the real mic, grant microphone permission to Termux:API and try again."
                )
            if debug:
                print("[Termux debug] trying PulseAudio (sox).")
        except Exception as e:
            if debug:
                print(f"[Termux debug] termux record error: {e}")

    # 2) Fallback: sox from PulseAudio
    sox_path = shutil.which("sox")
    if not sox_path:
        return None, None
    pulse_source = getattr(config, "PULSE_SOURCE", "default") or "default"
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
                "trim", "0", str(duration_sec),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=duration_sec + 5,
        )
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout, sample_rate
    except Exception:
        pass
    return None, None


def _wait_speech_recognition(*, stop_event=None) -> bool:
    """
    Continuously record short clips and run Google Speech Recognition
    to detect the wake word "Doraemon".
    """
    import speech_recognition as sr

    wake_word_str = config.WAKE_WORD.lower()
    segment_duration = 3
    sample_width = 2

    use_termux_api = shutil.which("termux-microphone-record") is not None
    if use_termux_api:
        print('[Termux] Using termux-microphone-record (Termux:API) for mic.')
    else:
        print(
            '[Termux] termux-microphone-record not found — using PulseAudio. '
            'If the mic does not work, install Termux:API and pkg install termux-api'
        )
    print('[Termux] Listening for wake word "Doraemon" …')

    recognizer = sr.Recognizer()
    debug = getattr(config, "TERMUX_DEBUG", False)
    no_speech_count = 0

    while True:
        if stop_event is not None and stop_event.is_set():
            return False

        raw_data, rate = _record_segment_termux(segment_duration, SAMPLE_RATE)
        if not raw_data:
            continue

        audio = sr.AudioData(raw_data, rate, sample_width)

        kwargs = {}
        if getattr(config, "SPEECH_LANGUAGE", ""):
            kwargs["language"] = config.SPEECH_LANGUAGE

        try:
            text = recognizer.recognize_google(audio, **kwargs)
        except sr.UnknownValueError:
            no_speech_count += 1
            if debug and no_speech_count % 5 == 1:
                print(
                    "[Termux debug] Google: no speech in segment. "
                    "Say the wake word clearly in one go; set SPEECH_LANGUAGE in .env to your language (e.g. pt-PT)."
                )
            continue
        except sr.RequestError as exc:
            print(f"[Termux] Speech API error: {exc}")
            continue

        if not text:
            continue

        if _matches_wake_word(text, wake_word_str):
            print(f'[Termux] Wake word detected: "{text}"')
            return True
        # Always show what was heard so you can fix SPEECH_LANGUAGE or pronunciation
        print(f'[Termux] Heard (not wake word): "{text}"')


def wait_for_wake_word(*, stop_event=None) -> bool:
    """
    Block until the wake word "Doraemon" is detected.
    Uses Google Speech Recognition (no Picovoice on Termux).
    """
    return _wait_speech_recognition(stop_event=stop_event)
