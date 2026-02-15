"""
Wake word detection.

On desktop (macOS/Linux/Windows): uses Picovoice Porcupine for efficient,
always-on wake word detection with low latency.

On Termux (Android): attempts to use Porcupine by patching the CPU detection
for mobile ARM cores (Cortex-A55, A73, A75, A77, A78, etc.) that are binary-
compatible with Raspberry Pi CPUs but not recognised by the Python SDK.
If Porcupine still cannot load (e.g. the native .so is incompatible with
Android's Bionic libc), falls back to sox + Google Speech Recognition.
"""

import platform
import subprocess
import sys
from pathlib import Path

from . import config
from .audio import IS_TERMUX


# ---------------------------------------------------------------------------
# Mobile ARM → Raspberry Pi CPU-part mapping (hex identifiers from cpuinfo)
# ---------------------------------------------------------------------------
# pvporcupine only recognises a handful of CPU parts (Pi Zero, Pi 3/4/5).
# Mobile SoCs use different cores that are architecturally compatible.
_MOBILE_CPU_MAP = {
    "0xd04": "0xd03",  # Cortex-A35  → A53  (ARMv8-A little)
    "0xd05": "0xd03",  # Cortex-A55  → A53  (ARMv8.2-A little)
    "0xd09": "0xd08",  # Cortex-A73  → A72  (ARMv8-A big)
    "0xd0a": "0xd08",  # Cortex-A75  → A72  (ARMv8.2-A big)
    "0xd0d": "0xd0b",  # Cortex-A77  → A76  (ARMv8.2-A big)
    "0xd41": "0xd0b",  # Cortex-A78  → A76
    "0xd44": "0xd0b",  # Cortex-X1   → A76
    "0xd46": "0xd0b",  # Cortex-A510 → A76
    "0xd47": "0xd0b",  # Cortex-A710 → A76
    "0xd48": "0xd0b",  # Cortex-X2   → A76
    "0xd4d": "0xd0b",  # Cortex-A715 → A76
    "0xd4e": "0xd0b",  # Cortex-X3   → A76
}


def _verify_native_library(pvporcupine_module):
    """
    Try to actually load the Porcupine native C library (.so/.dylib/.dll).

    The Python package can import fine, but the shared library may fail to load
    on platforms like Android/Termux where glibc is not available.

    Returns the module if the library loads, or None.
    """
    try:
        from ctypes import cdll
        from pvporcupine._util import pv_library_path
        cdll.LoadLibrary(pv_library_path())
        return pvporcupine_module
    except OSError as exc:
        print(f"[wake_word] Porcupine native library failed to load: {exc}")
        return None
    except Exception as exc:
        print(f"[wake_word] Porcupine library verification failed: {exc}")
        return None


def _try_import_porcupine():
    """
    Import pvporcupine, applying a CPU-detection patch for mobile ARM if the
    normal import fails with ``NotImplementedError("Unsupported CPU …")``.

    Returns the pvporcupine module on success, or *None* if it cannot be loaded.
    """
    # --- 1. Try a plain import first ---
    try:
        import pvporcupine
        return _verify_native_library(pvporcupine)
    except ImportError:
        # Package not installed at all
        return None
    except NotImplementedError:
        pass  # Unsupported CPU — try patching below

    # --- 2. Identify the CPU part from /proc/cpuinfo ---
    try:
        cpu_info_raw = subprocess.check_output(["cat", "/proc/cpuinfo"]).decode()
        cpu_parts = [l for l in cpu_info_raw.split("\n") if "CPU part" in l]
        actual_part = cpu_parts[0].split()[-1].lower() if cpu_parts else ""
    except Exception:
        return None

    if actual_part not in _MOBILE_CPU_MAP:
        return None
    replacement_part = _MOBILE_CPU_MAP[actual_part]

    # --- 3. Remove broken partial imports from the first attempt ---
    for key in list(sys.modules):
        if key.startswith("pvporcupine"):
            del sys.modules[key]

    # --- 4. Monkey-patch subprocess.check_output so pvporcupine sees a
    #         recognised CPU part when it reads /proc/cpuinfo at import time ---
    _real_check_output = subprocess.check_output

    def _patched_check_output(cmd, *args, **kwargs):
        result = _real_check_output(cmd, *args, **kwargs)
        if isinstance(cmd, list) and cmd == ["cat", "/proc/cpuinfo"]:
            if isinstance(result, bytes):
                return result.replace(
                    actual_part.encode(), replacement_part.encode()
                )
            return result.replace(actual_part, replacement_part)
        return result

    try:
        subprocess.check_output = _patched_check_output
        import pvporcupine
    except Exception as exc:
        print(f"[wake_word] Porcupine CPU patch applied but import still failed: {exc}")
        for key in list(sys.modules):
            if key.startswith("pvporcupine"):
                del sys.modules[key]
        return None
    finally:
        subprocess.check_output = _real_check_output

    # --- 5. Verify the native .so library can actually be loaded.
    #         The Python import may succeed but the C library may fail
    #         on Android due to missing glibc (libpthread.so.0 etc.) ---
    return _verify_native_library(pvporcupine)


# ---------------------------------------------------------------------------
# Resolve which backend to use at import time
# ---------------------------------------------------------------------------
if IS_TERMUX:
    _porcupine_mod = _try_import_porcupine()
    if _porcupine_mod is not None:
        print("[wake_word] Porcupine loaded successfully on Termux!")
    else:
        print(
            "[wake_word] Porcupine unavailable on Termux — "
            "using speech-recognition fallback."
        )
else:
    # Desktop: import normally — a failure here is a real error.
    import pvporcupine as _porcupine_mod  # noqa: F811


# ---------------------------------------------------------------------------
# Porcupine backend
# ---------------------------------------------------------------------------

def _create_porcupine():
    """Create Porcupine instance with custom .ppn or built-in keyword."""
    access_key = config.PICOVOICE_ACCESS_KEY
    if not access_key:
        raise ValueError(
            "PICOVOICE_ACCESS_KEY is required. Set it in .env (see .env.example)."
        )

    model_path = (config.WAKE_WORD_MODEL_PATH or "").strip()
    if model_path and Path(model_path).expanduser().exists():
        return _porcupine_mod.create(
            access_key=access_key,
            keyword_paths=[str(Path(model_path).expanduser().resolve())],
        )
    # Fallback to built-in keyword for testing without custom "Doraemon" model
    return _porcupine_mod.create(
        access_key=access_key,
        keywords=["computer"],
    )


def _wait_porcupine(*, stop_event=None) -> bool:
    """Use Porcupine for wake word detection (works on desktop and patched Termux)."""
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
# Speech-recognition fallback (Termux only)
# ---------------------------------------------------------------------------

def _matches_wake_word(text: str, wake_word: str) -> bool:
    """
    Check whether *text* contains the wake word, tolerating the many ways
    speech recognition might transcribe "doraemon":
      "Doraemon", "Dora Emon", "dora e mon", "Doremon", "Dora Amon", etc.

    Strategy: strip all spaces/hyphens/punctuation from both strings and
    do a substring check, so "dora e mon" → "doraemon" matches "doraemon".
    """
    import re
    normalise = lambda s: re.sub(r"[\s\-'\".,!?]+", "", s.lower())
    return normalise(wake_word) in normalise(text)


def _record_segment_termux(duration_sec: int, sample_rate: int):
    """
    Record a short segment on Termux. Prefer termux-microphone-record (real mic)
    if available; otherwise fall back to sox + PulseAudio (often only captures
    speaker monitor, not mic).

    Returns (raw_pcm_bytes, sample_rate) or (None, None) on failure.
    """
    import os
    import shutil
    import time

    debug = getattr(config, "TERMUX_DEBUG", False)

    # 1) Try Termux:API microphone (actual mic on Android)
    termux_rec = shutil.which("termux-microphone-record")
    ffmpeg_path = shutil.which("ffmpeg")
    if termux_rec and ffmpeg_path:
        rec_path = getattr(config, "TERMUX_RECORD_PATH", "").strip()
        if not rec_path:
            cache_dir = Path(__file__).resolve().parent / "cache"
            cache_dir.mkdir(exist_ok=True)
            rec_path = str(cache_dir / "termux_rec.opus")
        else:
            rec_path = Path(rec_path).expanduser().resolve()
            rec_path.parent.mkdir(parents=True, exist_ok=True)
            rec_path = str(rec_path)
        try:
            subprocess.run(
                [
                    termux_rec,
                    "-l", str(duration_sec),
                    "-f", rec_path,
                    "-e", "opus",
                    "-r", "16000",
                    "-c", "1",
                ],
                capture_output=True,
                timeout=10,
            )
            # API records in background; wait for recording + write
            time.sleep(duration_sec + 2)
            for _ in range(3):
                try:
                    with open(rec_path, "rb") as f:
                        data = f.read()
                except FileNotFoundError:
                    data = b""
                if data and len(data) >= 100:
                    break
                time.sleep(1)
            try:
                os.unlink(rec_path)
            except Exception:
                pass
            if not data or len(data) < 100:
                if debug:
                    print(f"[Termux debug] termux-microphone-record: no data (file empty or missing)")
                return None, None
            if debug:
                print(f"[Termux debug] opus file: {len(data)} bytes")
            # Convert opus → raw 16kHz mono 16-bit PCM (tell ffmpeg stdin is opus)
            proc = subprocess.run(
                [
                    ffmpeg_path,
                    "-f", "opus",
                    "-i", "-",
                    "-f", "s16le",
                    "-ar", str(sample_rate),
                    "-ac", "1",
                    "-",
                ],
                input=data,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                timeout=10,
            )
            if proc.returncode != 0 or not proc.stdout:
                if debug:
                    print(f"[Termux debug] ffmpeg failed (code {proc.returncode})")
                return None, None
            if debug:
                print(f"[Termux debug] PCM: {len(proc.stdout)} bytes")
            return proc.stdout, sample_rate
        except Exception as e:
            if debug:
                print(f"[Termux debug] termux record error: {e}")
            return None, None

    # 2) Fallback: sox from PulseAudio (on many Termux setups only sink.monitor = speaker)
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
    to detect the wake word.

    On Termux, uses termux-microphone-record (Termux:API) when available so
    the real mic is used; otherwise sox+PulseAudio (which often only has
    speaker monitor, not mic).
    """
    import os
    import shutil

    import speech_recognition as sr

    wake_word = config.WAKE_WORD.lower()
    segment_duration = 3
    sample_rate = config.PORCUPINE_SAMPLE_RATE
    sample_width = 2

    use_termux_api = shutil.which("termux-microphone-record") is not None
    if use_termux_api:
        print('[Termux] Using termux-microphone-record (Termux:API) for mic.')
    else:
        print(
            '[Termux] termux-microphone-record not found — using PulseAudio. '
            'If the mic does not work, install Termux:API and pkg install termux-api'
        )
    print(f'[Termux] Listening for wake word "{config.WAKE_WORD}" …')

    recognizer = sr.Recognizer()
    debug = getattr(config, "TERMUX_DEBUG", False)
    no_speech_count = 0

    while True:
        if stop_event is not None and stop_event.is_set():
            return False

        raw_data, rate = _record_segment_termux(segment_duration, sample_rate)
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
                print("[Termux debug] Google: no speech in segment")
            continue
        except sr.RequestError as exc:
            print(f"[Termux] Speech API error: {exc}")
            continue

        if not text:
            continue

        print(f'[Termux] Heard: "{text}"')

        if _matches_wake_word(text, wake_word):
            return True


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def wait_for_wake_word(*, stop_event=None) -> bool:
    """
    Block until the wake word is detected.

    On desktop: always uses Porcupine (efficient, offline).
    On Termux:  uses Porcupine if the native library loaded successfully,
                otherwise falls back to sox + Google Speech Recognition.
    """
    if IS_TERMUX and _porcupine_mod is None:
        return _wait_speech_recognition(stop_event=stop_event)
    return _wait_porcupine(stop_event=stop_event)
