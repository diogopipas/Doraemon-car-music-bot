"""
Platform detection for Android (Termux).

App is mobile-only; this module only exports IS_TERMUX for consistency checks.
"""
from __future__ import annotations

import os

# Detect Termux by checking for its standard prefix directory
IS_TERMUX = os.path.isdir("/data/data/com.termux")
