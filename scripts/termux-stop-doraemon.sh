#!/data/data/com.termux/files/usr/bin/bash
# Stop Doraemon. Use with Termux:Widget for one-tap stop.
# Copy to ~/.shortcuts/ on your phone and add as a widget (see README).

if pkill -f "python.*main.py" 2>/dev/null; then
  termux-toast "Doraemon stopped." 2>/dev/null || true
else
  termux-toast "Doraemon was not running." 2>/dev/null || true
fi
