#!/usr/bin/env python3
"""
Doraemon voice-activated music bot.

Mobile only — runs on Android via Termux. No PC/desktop use.

Say the wake word "Doraemon", then say a song name to play from YouTube.
Response: "Si?" (then e.g. "toca avenged sevenfold" → "Ah claro amigo!"). All in Portuguese with Spanish accent.
Say "stop" to stop playback. Say "go to sleep" to turn off (hands-free).
"""

import sys
import time

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


def main() -> None:
    # Mobile only: exit on PC/desktop.
    if not IS_TERMUX:
        print("Doraemon is for Android (Termux) only. No PC/desktop support. Exiting.")
        sys.exit(1)

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
                print(f"[Playing] {result.title}")
                feedback.speak_phrase("playing", block=True, title=result.title)
            else:
                print(f"[Could not play] {phrase}")
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
