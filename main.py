#!/usr/bin/env python3
"""
Doraemon voice-activated music bot.

Say the wake word "Doraemon", then say a song name to play from YouTube.
Response: "Si?" (then e.g. "toca avenged sevenfold" → "Ah claro amigo!"). All in Portuguese with Spanish accent.
Say "stop" to stop playback. Say "go to sleep" to turn off (hands-free).
"""

import sys
import time
from pathlib import Path

from doraemon import config
from doraemon import feedback
from doraemon import listener
from doraemon import player
from doraemon import wake_word
from doraemon.audio import IS_TERMUX

# After wake word: saying any of these exits the bot (hands-free "turn off").
SLEEP_PHRASES = frozenset({
    "go to sleep", "stop listening", "goodbye", "sleep",
    "good night", "turn off", "exit", "quit",
})


def _require_doraemon_ppn() -> None:
    """Require valid Doraemon .ppn when Porcupine is used (desktop or Termux with Porcupine)."""
    if IS_TERMUX and wake_word._porcupine_mod is None:
        return  # SR fallback doesn't need .ppn
    path_str = (config.WAKE_WORD_MODEL_PATH or "").strip()
    if not path_str:
        print("Error: Doraemon wake word requires a custom .ppn. Set WAKE_WORD_MODEL_PATH in .env.")
        print("Train 'Doraemon' at https://console.picovoice.ai/ and download the .ppn for your platform.")
        sys.exit(1)
    p = Path(path_str).expanduser()
    if not p.is_absolute():
        p = config.PROJECT_ROOT / p
    p = p.resolve()
    if not p.exists():
        print(f"Error: Doraemon .ppn not found: {p}")
        print("Set WAKE_WORD_MODEL_PATH in .env to your Doraemon .ppn file.")
        sys.exit(1)


def main() -> None:
    # Picovoice key is required when Porcupine is the active wake-word backend.
    porcupine_needed = not IS_TERMUX or wake_word._porcupine_mod is not None
    if porcupine_needed and not config.PICOVOICE_ACCESS_KEY:
        print("Error: PICOVOICE_ACCESS_KEY is not set. Copy .env.example to .env and add your key.")
        print("Get a key at https://console.picovoice.ai/")
        sys.exit(1)
    if porcupine_needed:
        _require_doraemon_ppn()

    print("Doraemon is listening. Say \"Doraemon\", then say a song name.")
    print("Say 'stop' to stop playback. Say 'go to sleep' to turn off (no taps).\n")

    while True:
        try:
            detected = wake_word.wait_for_wake_word()
            if not detected:
                continue
            feedback.speak_phrase("yes", block=True)
            # Brief pause so user can start speaking (minimal for responsiveness)
            time.sleep(0.25)
            phrase = listener.listen_for_song_name()
            if not phrase:
                feedback.speak_phrase("try_again", block=True)
                phrase = listener.listen_for_song_name()
            if not phrase:
                feedback.speak_phrase("sorry", block=True)
                continue
            phrase_lower = phrase.strip().lower()
            if phrase_lower in ("stop", "stop the music", "stop music"):
                player.stop_playback()
                feedback.speak_phrase("stopped", block=True)
                continue
            if phrase_lower in SLEEP_PHRASES:
                player.stop_playback()
                feedback.speak_phrase("goodbye", block=True)
                print("Goodbye.")
                sys.exit(0)
            result = player.play_song(phrase)
            if result.success:
                feedback.speak_phrase("playing", block=True, title=result.title)
            else:
                feedback.speak_phrase("not_found", block=True, phrase=phrase)
        except KeyboardInterrupt:
            print("\nBye!")
            player.stop_playback()
            break
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            feedback.speak_phrase("error", block=True)


if __name__ == "__main__":
    main()
