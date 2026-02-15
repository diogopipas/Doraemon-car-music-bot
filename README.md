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

### 1. Install Termux

- Install **[Termux](https://f-droid.org/packages/com.termux/)** from F-Droid (not the Play Store version).
- Install **[Termux:API](https://f-droid.org/packages/com.termux.api/)** from F-Droid (needed for microphone permissions).

### 2. Install system packages

Open Termux and run:

```bash
pkg update && pkg upgrade
pkg install python mpv ffmpeg sox pulseaudio git
```

### 3. Start PulseAudio

PulseAudio bridges Android's audio to command-line tools:

```bash
pulseaudio --start --load="module-sles-source" --load="module-sles-sink"
```

> Add this to your `~/.bashrc` so it starts automatically:
> ```bash
> echo 'pulseaudio --start --load="module-sles-source" --load="module-sles-sink" 2>/dev/null' >> ~/.bashrc
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

### 7. Run

```bash
python main.py
```

Connect your phone to your car via **Bluetooth** or **aux cable** for audio output.

---

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

1. Run `python main.py`.
2. Say the wake word: **"Doraemon"** (or **"computer"** if no custom model is set).
3. When you hear "Yes?", say a song name (e.g. "Bohemian Rhapsody by Queen").
4. The bot searches YouTube and streams audio. It says "Playing [title]."
5. To stop: say the wake word, then **"stop"**.
6. Press **Ctrl+C** to quit.

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
