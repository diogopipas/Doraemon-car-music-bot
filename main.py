#!/usr/bin/env python3
"""
Doraemon voice-activated music bot.

Say the wake word ("Doraemon" or "computer" if no custom model), then say a song name
to play it from YouTube. Say "stop" to stop playback. Say "go to sleep" to turn off (hands-free).
"""

import sys
import time

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


def main() -> None:
    # Picovoice key is required when Porcupine is the active wake-word backend.
    # On Termux where Porcupine may be unavailable, the SR fallback doesn't need it.
    porcupine_needed = not IS_TERMUX or wake_word._porcupine_mod is not None
    if porcupine_needed and not config.PICOVOICE_ACCESS_KEY:
        print("Error: PICOVOICE_ACCESS_KEY is not set. Copy .env.example to .env and add your key.")
        print("Get a key at https://console.picovoice.ai/")
        sys.exit(1)

    print("Doraemon is listening. Say the wake word, then say a song name.")
    print("Say 'stop' to stop playback. Say 'go to sleep' to turn off (no taps).\n")

    while True:
        try:
            detected = wake_word.wait_for_wake_word()
            if not detected:
                continue
            feedback.speak("Yes?", block=True)
            # Short pause so user hears "Yes?" and can start speaking
            time.sleep(0.6)
            phrase = listener.listen_for_song_name()
            if not phrase:
                feedback.speak("Try again?", block=True)
                phrase = listener.listen_for_song_name()
            if not phrase:
                feedback.speak("Sorry, I didn't catch that.", block=True)
                continue
            phrase_lower = phrase.strip().lower()
            if phrase_lower in ("stop", "stop the music", "stop music"):
                player.stop_playback()
                feedback.speak("Stopped.", block=True)
                continue
            if phrase_lower in SLEEP_PHRASES:
                player.stop_playback()
                feedback.speak("Goodbye.", block=True)
                print("Goodbye.")
                sys.exit(0)
            result = player.play_song(phrase)
            if result.success:
                feedback.speak(f"Playing {result.title}.", block=True)
            else:
                feedback.speak(f"Could not find or play {phrase}.", block=True)
        except KeyboardInterrupt:
            print("\nBye!")
            player.stop_playback()
            break
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            feedback.speak("Something went wrong. Try again.", block=True)


if __name__ == "__main__":
    main()
