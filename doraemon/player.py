"""YouTube search and audio playback via yt-dlp and mpv."""
from __future__ import annotations

import re
import shutil
import subprocess
import sys
from typing import NamedTuple

import yt_dlp

from .audio import IS_TERMUX

# Track current playback so it can be stopped when a new song is requested
_current_process: subprocess.Popen | None = None

# Phrases to strip from the start of a voice command so the search query is just song/artist.
# User can say "play X", "toca X", "I want you to play this song: X by Y", etc.
_SEARCH_PREFIXES = (
    r"^(?:play\s+)+",
    r"^toca\s+",  # Portuguese "play"
    r"^tocar\s+",
    r"^i want (?:you to )?play\s+",
    r"^i want to hear\s+",
    r"^can you play\s+",
    r"^could you play\s+",
    r"^please play\s+",
    r"^play (?:the )?song\s*:?\s*",
    r"^play (?:the )?track\s*:?\s*",
    r"^this song\s*:?\s*",
    r"^the song\s*:?\s*",
)


class PlayResult(NamedTuple):
    title: str
    """Video/song title for feedback."""
    success: bool


def _find_mpv() -> str:
    """Return path to mpv executable."""
    path = shutil.which("mpv")
    if not path:
        raise FileNotFoundError(
            "mpv not found. Install it: brew install mpv (macOS) or apt install mpv (Linux)."
        )
    return path


def _normalize_search_query(raw: str) -> str:
    """Strip common leading phrases so 'play X' or 'I want you to play X by Y' becomes 'X' or 'X by Y'."""
    s = (raw or "").strip()
    for pat in _SEARCH_PREFIXES:
        s = re.sub(pat, "", s, flags=re.IGNORECASE)
    return s.strip()


def stop_playback() -> None:
    """Stop the currently playing track, if any."""
    global _current_process
    if _current_process is not None:
        try:
            _current_process.terminate()
            _current_process.wait(timeout=5)
        except (ProcessLookupError, subprocess.TimeoutExpired):
            if _current_process.poll() is None:
                _current_process.kill()
        _current_process = None


def play_song(query: str) -> PlayResult:
    """
    Search YouTube for the query, then stream the first result with mpv (audio only).

    Stops any currently playing track before starting the new one.
    Returns (title, success). On failure, title is the query and success is False.
    """
    global _current_process
    stop_playback()

    query = _normalize_search_query(query or "")
    if not query:
        return PlayResult(title="", success=False)

    ydl_opts = {
        "format": "bestaudio/best",
        "skip_download": True,
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(f"ytsearch1:{query}", download=False)
            if not info:
                print(f"[player] No result for: {query}", file=sys.stderr)
                return PlayResult(title=query, success=False)
            # ytsearch1 returns a single result
            title = info.get("title") or query
            url = info.get("webpage_url") or info.get("url")
            if not url:
                print(f"[player] No URL for: {title}", file=sys.stderr)
                return PlayResult(title=title, success=False)
    except Exception as e:
        print(f"[player] yt-dlp error: {e}", file=sys.stderr)
        return PlayResult(title=query, success=False)

    mpv_path = _find_mpv()
    # On Termux, force PulseAudio so audio actually plays
    mpv_cmd = [mpv_path, "--no-video", "--no-terminal", url]
    if IS_TERMUX:
        mpv_cmd.insert(-1, "--ao=pulse")
    try:
        _current_process = subprocess.Popen(
            mpv_cmd,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return PlayResult(title=title, success=True)
    except Exception as e:
        print(f"[player] mpv error: {e}", file=sys.stderr)
        return PlayResult(title=title, success=False)
