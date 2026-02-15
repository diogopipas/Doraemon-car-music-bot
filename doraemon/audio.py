"""
Platform-aware audio recording.

On desktop (macOS/Linux/Windows), uses PvRecorder (Picovoice).
On Termux (Android), uses sox rec piped to stdout since PyAudio/PvRecorder
cannot access microphone devices in Termux's environment.

Both backends yield int16 PCM frames at 16kHz, one channel.
"""

import os
import shutil
import struct
import subprocess

from . import config

# Detect Termux by checking for its standard prefix directory
IS_TERMUX = os.path.isdir("/data/data/com.termux")


class AudioRecorder:
    """Uniform interface for recording int16 PCM frames at 16kHz."""

    def __init__(self, frame_length: int = config.PORCUPINE_FRAME_LENGTH):
        self.frame_length = frame_length
        self._started = False

        if IS_TERMUX:
            self._backend = "sox"
        else:
            self._backend = "pvrecorder"

        # Lazily initialised
        self._recorder = None  # PvRecorder instance
        self._process = None  # sox subprocess

    # ---- lifecycle ----

    def start(self):
        if self._started:
            return
        if self._backend == "pvrecorder":
            self._start_pvrecorder()
        else:
            self._start_sox()
        self._started = True

    def stop(self):
        if not self._started:
            return
        if self._backend == "pvrecorder":
            self._stop_pvrecorder()
        else:
            self._stop_sox()
        self._started = False

    def delete(self):
        self.stop()
        if self._recorder is not None:
            try:
                self._recorder.delete()
            except Exception:
                pass
            self._recorder = None

    # ---- read ----

    def read(self) -> list[int]:
        """Return one frame of int16 samples (length == self.frame_length)."""
        if self._backend == "pvrecorder":
            return self._recorder.read()
        return self._read_sox()

    # ---- PvRecorder backend ----

    def _start_pvrecorder(self):
        from pvrecorder import PvRecorder
        self._recorder = PvRecorder(
            frame_length=self.frame_length,
            sample_rate=config.PORCUPINE_SAMPLE_RATE,
        )
        self._recorder.start()

    def _stop_pvrecorder(self):
        if self._recorder is not None:
            try:
                self._recorder.stop()
            except Exception:
                pass

    # ---- sox backend (Termux) ----

    def _start_sox(self):
        sox_path = shutil.which("sox")
        if not sox_path:
            raise FileNotFoundError(
                "sox not found. In Termux run: pkg install sox pulseaudio"
            )
        # rec is a sox alias; using sox with type=pulseaudio input
        # Outputs raw signed 16-bit little-endian mono PCM at 16kHz to stdout
        self._process = subprocess.Popen(
            [
                sox_path,
                "-t", "pulseaudio", "default",  # input from PulseAudio
                "-t", "raw",                     # output format
                "-r", str(config.PORCUPINE_SAMPLE_RATE),
                "-b", "16",
                "-e", "signed-integer",
                "-L",                            # little-endian
                "-c", "1",                       # mono
                "-",                             # stdout
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    def _stop_sox(self):
        if self._process is not None:
            try:
                self._process.terminate()
                self._process.wait(timeout=3)
            except Exception:
                if self._process.poll() is None:
                    self._process.kill()
            self._process = None

    def _read_sox(self) -> list[int]:
        """Read frame_length int16 samples from the sox pipe."""
        byte_count = self.frame_length * 2  # 2 bytes per int16
        data = b""
        while len(data) < byte_count:
            chunk = self._process.stdout.read(byte_count - len(data))
            if not chunk:
                raise RuntimeError("sox audio stream ended unexpectedly")
            data += chunk
        # Unpack little-endian int16 samples
        return list(struct.unpack(f"<{self.frame_length}h", data))
