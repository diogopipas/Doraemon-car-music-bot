#!/usr/bin/env python3
"""
Doraemon voice-activated music bot.

Say the wake word ("Doraemon" or "computer" if no custom model), then say a song name
to play it from YouTube. Say "stop" to stop playback.
"""

import sys

from doraemon import config
from doraemon import feedback
from doraemon import listener
from doraemon import player
from doraemon import wake_word


def main() -> None:
    if not config.PICOVOICE_ACCESS_KEY:
        print("Error: PICOVOICE_ACCESS_KEY is not set. Copy .env.example to .env and add your key.")
        print("Get a key at https://console.picovoice.ai/")
        sys.exit(1)

    print("Doraemon is listening. Say the wake word, then say a song name.")
    print("Say 'stop' after the wake word to stop playback. Press Ctrl+C to quit.\n")

    while True:
        try:
            detected = wake_word.wait_for_wake_word()
            if not detected:
                continue
            feedback.speak("Yes?", block=True)
            phrase = listener.listen_for_song_name()
            if not phrase:
                feedback.speak("Sorry, I didn't catch that.", block=True)
                continue
            phrase_lower = phrase.strip().lower()
            if phrase_lower in ("stop", "stop the music", "stop music"):
                player.stop_playback()
                feedback.speak("Stopped.", block=True)
                continue
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
