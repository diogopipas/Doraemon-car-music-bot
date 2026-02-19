# Doraemon-car-music-bot

Doraemon is a personal AI-powered voice recognition bot that plays songs in your car. Say its name ("Doraemon"), then say a song name to play it from YouTube.

## Features

- **Wake word activation** -- Uses Picovoice Porcupine to listen for "Doraemon" (or a built-in keyword for testing).
- **Voice commands** -- After the wake word, say a song or artist name; the bot searches YouTube and streams audio.
- **Voice feedback** -- Google TTS confirms what it heard and what it's playing.
- **Stop command** -- Say "stop" after the wake word to stop playback.
- **Cross-platform** -- Runs on macOS, Linux, Windows, and **Android via Termux**.

## Quick start (Termux / Android)

This is the primary target platform for in-car use.

### 1. Install Termux and add-ons

- Install **[Termux](https://f-droid.org/packages/com.termux/)** from F-Droid (not the Play Store version).
- Install **[Termux:API](https://f-droid.org/packages/com.termux.api/)** from F-Droid (needed for microphone permissions).
- Optional: **[Termux:Widget](https://f-droid.org/packages/com.termux.widget/)** for manual start/stop shortcuts; **[Termux:Boot](https://f-droid.org/packages/com.termux.boot/)** is used for hands-free auto-start (see step 7).

### 2. Install system packages

Open Termux and run:

```bash
pkg update && pkg upgrade
pkg install python mpv ffmpeg sox pulseaudio git termux-api
```

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

### 5. Picovoice setup

1. Sign up at [Picovoice Console](https://console.picovoice.ai/) (free).
2. Copy your **Access Key**.
3. Create a custom wake word:
   - In the Console, open **Porcupine** > create keyword (e.g. "Doraemon").
   - **Important:** select **Android** as the target platform.
   - Train and download the `.ppn` file.
   - Copy it into the project folder.

### 6. Configure

```bash
cp .env.example .env
```

Edit `.env`:
- Set `PICOVOICE_ACCESS_KEY` to your key.
- Set `WAKE_WORD_MODEL_PATH` to the `.ppn` file path (e.g. `doraemon/Dora-e-mon_pt_android_v4_0_0/Dora-e-mon_pt_android_v4_0_0.ppn`).

### 7. Hands-free like "Hey Siri" (no taps)

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

- **Use it:** Say **"Doraemon"** → it says "Yes?" → say a song name. Connect the phone to your car via **Bluetooth** or **aux** for audio.
- **Stop the music:** Say **"Doraemon"** → **"stop"**.
- **Turn off the bot:** Say **"Doraemon"** → **"go to sleep"** (or "goodbye", "stop listening"). It says "Goodbye." and exits. To have it listening again, reboot the phone or start it again (see below).

**Optional — start only when you connect to the car:**  
If you don’t want Doraemon running 24/7, use [Tasker](https://play.google.com/store/apps/details?id=net.dinglisch.android.taskerm) (or similar) plus the **Termux Plugin** for Tasker: create a profile that runs when your **car’s Bluetooth** connects, and run the script `~/Doraemon-car-music-bot/scripts/termux-start-doraemon.sh`. Then the bot only starts when you’re in the car. You still turn it off by voice: **"Doraemon"** → **"go to sleep"**.

**Optional — manual start/stop (widgets):**  
If you prefer a shortcut sometimes, you can use [Termux:Widget](https://f-droid.org/packages/com.termux.widget/) and the scripts in `scripts/` (e.g. copy to `~/.shortcuts/` and add as widgets). Not required for hands-free use.

**Test from terminal:**  
Run `python main.py` once to verify setup; say "go to sleep" to exit. For normal use, rely on boot (or Tasker) and voice only.


## Desktop setup (macOS / Linux / Windows)

### Prerequisites

- **Python 3.10+**
- **mpv** and **ffmpeg**
  - macOS: `brew install mpv ffmpeg portaudio`
  - Linux: `sudo apt install mpv ffmpeg portaudio19-dev`
  - Windows: install from official sites
- **Microphone**
- **Internet connection**

### Install

```bash
git clone https://github.com/diogopipas/Doraemon-car-music-bot.git
cd Doraemon-car-music-bot
python3 -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Configure

```bash
cp .env.example .env
```

Edit `.env`:
- Set `PICOVOICE_ACCESS_KEY` to your key.
- Optionally set `WAKE_WORD_MODEL_PATH` to a custom `.ppn` file trained for **macOS** / **Linux** / **Windows** (matching your OS).
  If left empty, the built-in keyword "computer" is used for testing.

### Run

```bash
python main.py
```

---

## Usage

1. Run `python main.py` (or let it auto-start on boot on Android).
2. Say the wake word: **"Doraemon"** (or **"computer"** if no custom model is set).
3. When you hear "Yes?", say what you want to hear. You can use natural phrasing:
   - Just the song: **"Bohemian Rhapsody"**
   - Song and artist: **"Bohemian Rhapsody by Queen"**
   - Full sentence: **"Play Bohemian Rhapsody"**, **"I want you to play this song: X by Y"** — the bot strips the extra words and searches for the song/artist.
4. The bot searches YouTube and streams audio. It says "Playing [title]."
5. To stop playback: say the wake word, then **"stop"**.
6. To turn off the bot (hands-free): say the wake word, then **"go to sleep"** (or "goodbye", "stop listening"). It says "Goodbye." and exits.
7. Press **Ctrl+C** to quit (when running in a terminal).

## Configuration (.env)

| Variable | Required | Description |
|----------|----------|-------------|
| `PICOVOICE_ACCESS_KEY` | Yes | Access key from [Picovoice Console](https://console.picovoice.ai/). |
| `WAKE_WORD_MODEL_PATH` | No | Path to custom `.ppn` wake word file. Must match your platform (Android for Termux, macOS for Mac, etc.). |
| `LISTEN_TIMEOUT` | No | Seconds to wait for speech after wake word (default: 5). |
| `PHRASE_TIME_LIMIT` | No | Max length of spoken phrase in seconds (default: 10). |

## Project structure

```
Doraemon-car-music-bot/
  main.py                   # Entry point
  requirements.txt          # Desktop dependencies
  requirements-termux.txt   # Termux (Android) dependencies
  scripts/                   # Termux boot script (hands-free) and optional widget scripts
  doraemon/
    config.py               # Environment and settings
    audio.py                # Platform-aware microphone (PvRecorder or sox)
    wake_word.py            # Porcupine wake word detection
    listener.py             # Speech recognition (song name)
    player.py               # YouTube search + mpv playback
    feedback.py             # Google TTS voice feedback via mpv
    cache/                  # Cached TTS audio files
  .env.example
```

## How it works

```
[Always listening] --wake word detected--> [Say "Yes?"]
  --> [Listen for song name] --recognized--> [Search YouTube]
  --> [Say "Playing <title>"] --> [Stream audio via mpv]
  --> [Back to listening]
```

- **Desktop:** PvRecorder captures mic audio for Porcupine; PyAudio (via SpeechRecognition) captures the song name.
- **Termux:** sox + PulseAudio captures mic audio for both Porcupine and SpeechRecognition, since PyAudio cannot access Android audio devices.
- **Playback:** mpv streams YouTube audio on all platforms.
- **TTS:** gTTS generates MP3s, mpv plays them (cached to avoid repeated API calls).

## License

Use and modify as you like for personal use.
