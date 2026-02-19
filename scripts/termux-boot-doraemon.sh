#!/data/data/com.termux/files/usr/bin/bash
# Optional: start Doraemon on device boot. Copy to ~/.termux/boot/ on your phone.
# Requires Termux:Boot from F-Droid. Disable battery optimization for Termux if it gets killed.

termux-wake-lock

PROJECT_DIR="${DORAEMON_DIR:-$HOME/Doraemon-car-music-bot}"
cd "$PROJECT_DIR" || exit 1

pulseaudio --start 2>/dev/null
nohup python main.py >> "$HOME/doraemon.log" 2>&1 &
