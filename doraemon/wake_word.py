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


def _try_import_porcupine():
    """
    Import pvporcupine, applying a CPU-detection patch for mobile ARM if the
    normal import fails with ``NotImplementedError("Unsupported CPU …")``.

    Returns the pvporcupine module on success, or *None* if it cannot be loaded.
    """
    # --- 1. Try a plain import first ---
    try:
        import pvporcupine
        return pvporcupine
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
        return pvporcupine
    except Exception as exc:
        print(f"[wake_word] Porcupine CPU patch applied but load still failed: {exc}")
        # Clean up broken imports
        for key in list(sys.modules):
            if key.startswith("pvporcupine"):
                del sys.modules[key]
        return None
    finally:
        subprocess.check_output = _real_check_output


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

def _wait_speech_recognition(*, stop_event=None) -> bool:
    """
    Continuously record short clips with sox and run Google Speech Recognition
    to detect the wake word.

    Records 2-second segments in a loop.  If the recognised text contains
    the configured wake word (default "doraemon"), returns True.
    """
    import shutil

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
    print(f'[Termux] Listening for wake word "{config.WAKE_WORD}" …')

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

    On desktop: always uses Porcupine (efficient, offline).
    On Termux:  uses Porcupine if the native library loaded successfully,
                otherwise falls back to sox + Google Speech Recognition.
    """
    if IS_TERMUX and _porcupine_mod is None:
        return _wait_speech_recognition(stop_event=stop_event)
    return _wait_porcupine(stop_event=stop_event)
