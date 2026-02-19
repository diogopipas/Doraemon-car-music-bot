#!/data/data/com.termux/files/usr/bin/bash
# Start Doraemon in the background. Use with Termux:Widget for one-tap start.
# Copy to ~/.shortcuts/ on your phone and add as a widget (see README).

PROJECT_DIR="${DORAEMON_DIR:-$HOME/Doraemon-car-music-bot}"
cd "$PROJECT_DIR" || exit 1

# Avoid starting twice
if pgrep -f "python.*main.py" > /dev/null; then
  termux-toast "Doraemon is already running." 2>/dev/null || true
  exit 0
fi

# Start PulseAudio if not running
pulseaudio --start 2>/dev/null

# Run in background so the widget returns immediately
nohup python main.py >> "$HOME/doraemon.log" 2>&1 &
sleep 1
if pgrep -f "python.*main.py" > /dev/null; then
  termux-toast "Doraemon started. Say the wake word for music." 2>/dev/null || true
else
  termux-toast "Failed to start Doraemon. Check ~/doraemon.log" 2>/dev/null || true
fi
