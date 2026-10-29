"""Windows foreground-window safety check for gameplay keyboard input."""

from __future__ import annotations

import ctypes
import os


def minecraft_is_focused() -> bool:
    """Return whether the foreground window title identifies Minecraft."""
    if os.name != "nt":
        return True
    user32 = ctypes.windll.user32
    window = user32.GetForegroundWindow()
    if not window:
        return False
    title = ctypes.create_unicode_buffer(512)
    user32.GetWindowTextW(window, title, len(title))
    return "minecraft" in title.value.lower()
