# Doraemon-car-music-bot

**Mobile only** — runs on **Android via Termux**. No PC/desktop support.

Doraemon is a personal AI voice bot for your car. Say **"Doraemon"** (wake word only), then a song name; it replies **"Si?"** and, after your command, **"Ah claro amigo!"** and plays from YouTube. All in Portuguese with a Spanish accent (Doraemon-style).

## Features

- **Wake word: "Doraemon" only** — Google Speech Recognition (Picovoice does not work on Termux).
- **Voice commands** — After "Si?", say a song or artist (e.g. "toca avenged sevenfold"); bot says "Ah claro amigo!" and streams audio.
- **Doraemon voice** — Portuguese phrases with Spanish-accent TTS; optional pre-recorded clips for instant "Si?" and "Ah claro amigo!".
- **Stop command** — Say "stop" after the wake word to stop playback.
- **Android (Termux) only** — No desktop/PC use.

## Quick start (Termux / Android)

### 1. Install Termux and add-ons

- Install **[Termux](https://f-droid.org/packages/com.termux/)** from F-Droid (not the Play Store version).
- Install **[Termux:API](https://f-droid.org/packages/com.termux.api/)** from F-Droid (needed for microphone permissions).
- Optional: **[Termux:Widget](https://f-droid.org/packages/com.termux.widget/)** for manual start/stop shortcuts; **[Termux:Boot](https://f-droid.org/packages/com.termux.boot/)** is used for hands-free auto-start (see step 7).

### 2. Install system packages

Open Termux and run:

```bash
pkg update && pkg upgrade
pkg install python mpv ffmpeg sox pulseaudio git termux-api opus-tools
```

**opus-tools** provides `opusdec`, which is used to convert the microphone’s Opus recording to PCM when ffmpeg fails (common on Termux with exit code 234).

**Microphone:** PulseAudio on Termux often only exposes the *speaker* (sink monitor), not the mic. For the **real microphone** the bot uses **termux-microphone-record** from the `termux-api` package. You must have the **Termux:API** app installed (from F-Droid) and grant it microphone permission. If you see "Listening for wake word" but it never responds, install Termux:API and `pkg install termux-api`, then run the bot again.

### 3. Start PulseAudio

PulseAudio is used for playback (mpv). Start it with:

```bash
pulseaudio --start
```

> Add to `~/.bashrc` to start automatically:
> ```bash
> echo 'pulseaudio --start 2>/dev/null' >> ~/.bashrc
> ```

### 4. Clone and install

```bash
git clone https://github.com/diogopipas/Doraemon-car-music-bot.git
cd Doraemon-car-music-bot
pip install -r requirements-termux.txt
```

### 5. Configure

```bash
cp .env.example .env
```

Edit `.env`:
- **Language:** Set `SPEECH_LANGUAGE=pt-PT` so "Doraemon" is recognized. `FEEDBACK_LANGUAGE=pt` gives the Doraemon persona ("Si?", "Ah claro amigo!", etc., with Spanish accent). Set `PHRASE_LANGUAGE=en-US` if you say song names in English.

### 6. Hands-free like "Hey Siri" (no taps)

No tapping the screen. Doraemon starts when the phone boots and listens for the wake word. You turn it off by voice.

**One-time setup — auto-start on boot:**

1. Install [Termux:Boot](https://f-droid.org/packages/com.termux.boot/) from F-Droid (same source as Termux).
2. In Termux, run:
   ```bash
   mkdir -p ~/.termux/boot
   cp ~/Doraemon-car-music-bot/scripts/termux-boot-doraemon.sh ~/.termux/boot/
   chmod +x ~/.termux/boot/termux-boot-doraemon.sh
   ```
3. Open **Termux:Boot** once (tap its icon) so Android allows it to run at boot.
4. In Android **Settings → Apps → Termux → Battery**, set to *Unrestricted* (or disable battery optimization) so the bot isn’t killed in the background.

After that, every time the phone boots, Doraemon starts and listens for the wake word. No opening Termux, no widgets, no taps.

**Daily use (fully voice):**

- **Use it:** Say **"Doraemon"** → it says **"Si?"** → say a song name (e.g. "toca avenged sevenfold") → it says **"Ah claro amigo!"** and plays. Connect the phone to your car via **Bluetooth** or **aux** for audio.
- **Stop the music:** Say **"Doraemon"** → **"stop"**.
- **Turn off the bot:** Say **"Doraemon"** → **"go to sleep"** (or "goodbye", "stop listening"). It says "Adeus." and exits. To have it listening again, reboot the phone or start it again (see below).

**Optional — start only when you connect to the car:**  
If you don’t want Doraemon running 24/7, use [Tasker](https://play.google.com/store/apps/details?id=net.dinglisch.android.taskerm) (or similar) plus the **Termux Plugin** for Tasker: create a profile that runs when your **car’s Bluetooth** connects, and run the script `~/Doraemon-car-music-bot/scripts/termux-start-doraemon.sh`. Then the bot only starts when you’re in the car. You still turn it off by voice: **"Doraemon"** → **"go to sleep"**.

**Optional — manual start/stop (widgets):**  
If you prefer a shortcut sometimes, you can use [Termux:Widget](https://f-droid.org/packages/com.termux.widget/) and the scripts in `scripts/` (e.g. copy to `~/.shortcuts/` and add as widgets). Not required for hands-free use.

**Test from terminal:**  
Run `python main.py` once to verify setup; say "go to sleep" to exit. For normal use, rely on boot (or Tasker) and voice only.

### "No response" when I say Doraemon?

Work through these in order:

**1. Is the bot actually running?**  
Open Termux and run:
```bash
pgrep -f "python.*main.py"
```
If you see a number, it's running. If nothing, the boot script may not have started it. Check the log:
```bash
cat ~/doraemon.log
```
If the log is empty or shows a Python error, the script failed (e.g. wrong path: boot uses `$HOME/Doraemon-car-music-bot` — if you cloned elsewhere, set `DORAEMON_DIR` in the boot script or use the full path). Run manually to test:
```bash
cd ~/Doraemon-car-music-bot   # or your actual path
python main.py
```
If it crashes when you run it, fix that first (e.g. missing .env).

**2. Is the microphone working?**  
With `python main.py` running in the foreground, you should see either:
- `[Termux] Using termux-microphone-record (Termux:API) for mic.` → good, real mic.
- `termux-microphone-record not found — using PulseAudio` → mic may be speaker-only (no real mic).

If you don't have the real mic: install the **Termux:API** app from F-Droid, grant it **microphone** permission, and run `pkg install termux-api` in Termux. Then restart the bot. You should then see "Using termux-microphone-record".  
If you see **"ffmpeg failed (code 234)"** in the log but opus file size is shown: install **opus-tools** so the bot can use `opusdec` to decode Opus: run `pkg install opus-tools`, then restart the bot.

**3. Is the wake word being heard?**  
With the bot running in the foreground, say **"Doraemon"** clearly. Watch the terminal:
- If you see `[Termux] Heard: "something"` but not "doraemon", Google is hearing you but transcribing differently. Try saying **"Doraemon"** more clearly, or set `SPEECH_LANGUAGE` in `.env` to your language (e.g. `pt-PT` for Portuguese).
- If you never see `Heard:` at all, the mic isn't delivering usable audio (back to step 2).
- If you see `Heard: "doraemon"` (or similar) and the bot still doesn't say "Si?", there may be a bug — check the rest of the log.
- **Wake word only works right after start, then stops:** The bot uses a unique temp file per recording and a short pause between recordings so the mic is released. If it still happens, try closing other apps using the mic and ensure Termux:API has microphone permission and isn’t battery-restricted.
- **Songs not recognized after "Si?":** Set `PHRASE_LANGUAGE=en-US` in `.env` if you say song names in English. Say the song name clearly right after the prompt.

**4. Battery / boot.**  
If the bot runs when you start it manually but not after reboot: open **Termux:Boot** once (tap its icon), and in **Settings → Apps → Termux → Battery** set to **Unrestricted**. Then reboot and check step 1 again.

---

**No desktop support.** This app is designed for Android (Termux) only. If you run it on a PC, it will exit with a message.

---

## Usage

1. Run `python main.py` (or let it auto-start on boot on Android).
2. Say **"Doraemon"** (only this wake word triggers the bot).
3. When you hear **"Si?"**, say what you want to hear, e.g. **"toca avenged sevenfold"** or **"Bohemian Rhapsody"** or **"Play X by Y"** — the bot strips extra words and searches YouTube.
4. The bot says **"Ah claro amigo!"** and streams audio.
5. To stop playback: say **"Doraemon"**, then **"stop"**.
6. To turn off the bot (hands-free): say **"Doraemon"**, then **"go to sleep"** (or "goodbye", "stop listening"). It says "Adeus." and exits.
7. Press **Ctrl+C** to quit (when running in a terminal).

**Faster "Si?" and "Ah claro amigo!":** For instant, character-accurate replies, add your own recordings (Spanish accent, Portuguese) as `doraemon/assets/si.mp3` and `doraemon/assets/ah_claro_amigo.mp3`. Otherwise the bot uses Google TTS with Spanish accent.

## Configuration (.env)

| Variable | Required | Description |
|----------|----------|-------------|
| `FEEDBACK_LANGUAGE` | No | `pt` = Doraemon persona (Portuguese + Spanish accent). Default: `pt`. |
| `SPEECH_LANGUAGE` | No | Language for recognizing "Doraemon" (e.g. `pt-PT`). |
| `PHRASE_LANGUAGE` | No | Language for recognizing the *song name* (e.g. `en-US`). Empty = use `SPEECH_LANGUAGE`. |
| `LISTEN_TIMEOUT` | No | Seconds to wait for speech after "Si?" (default: 3). |
| `PHRASE_TIME_LIMIT` | No | Max length of spoken phrase in seconds (default: 10). |

## Project structure

```
Doraemon-car-music-bot/
  main.py                   # Entry point (Android/Termux only)
  requirements-termux.txt   # Dependencies (Termux)
  scripts/                   # Termux boot script (hands-free) and optional widget scripts
  doraemon/
    config.py               # Environment and settings
    audio.py                # Platform-aware microphone (PvRecorder or sox)
    wake_word.py            # Wake word "Doraemon" via Google Speech Recognition
    listener.py             # Speech recognition (song name)
    player.py               # YouTube search + mpv playback
    feedback.py             # Google TTS voice feedback via mpv
    cache/                  # Cached TTS audio files
  .env.example
```

## How it works

```
[Always listening] --"Doraemon" only--> [Say "Si?"]
  --> [Listen for command] --recognized--> [Search YouTube]
  --> [Say "Ah claro amigo!"] --> [Stream audio via mpv]
  --> [Back to listening]
```

- **Wake word:** Only "Doraemon" triggers, via Google Speech Recognition.
- **Voice:** Doraemon persona = Portuguese phrases with Spanish-accent TTS (gTTS). Optional pre-recorded `doraemon/assets/si.mp3` and `ah_claro_amigo.mp3` for instant response.
- **Playback:** mpv streams YouTube audio.

## License

Use and modify as you like for personal use.
