"""Safe translation of stable note events into keyboard and mouse actions."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
from dataclasses import dataclass
from enum import Enum
import time
from typing import Callable, Protocol

from note_state import NoteEvent


class ControlMode(str, Enum):
    SUSTAINED = "sustained"
    TRIGGER = "trigger"


@dataclass(frozen=True)
class NoteMapping:
    key: str
    mode: ControlMode
    enabled: bool = True


class KeySink(Protocol):
    def press(self, key: str) -> None: ...

    def release(self, key: str) -> None: ...

    def move(self, dx: int, dy: int) -> None: ...

    def move_raw(self, dx: int, dy: int) -> None: ...


# ---------------------------------------------------------------------------
# Win32 SendInput structures for raw relative mouse movement.
# Used by move_raw() so that games using DirectInput / Raw Input (e.g.
# Minecraft with "Raw Input" ON) receive the delta without it being filtered
# by the Windows cursor position API.
# ---------------------------------------------------------------------------

_PUL = ctypes.POINTER(ctypes.c_ulong)


class _MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", wintypes.LONG),
        ("dy", wintypes.LONG),
        ("mouseData", wintypes.DWORD),
        ("dwFlags", wintypes.DWORD),
        ("time", wintypes.DWORD),
        ("dwExtraInfo", _PUL),
    ]


class _INPUT_UNION(ctypes.Union):
    _fields_ = [("mi", _MOUSEINPUT)]


class _INPUT(ctypes.Structure):
    _fields_ = [("type", wintypes.DWORD), ("u", _INPUT_UNION)]


_MOUSEEVENTF_MOVE = 0x0001  # Relative movement (no MOUSEEVENTF_ABSOLUTE)
_INPUT_MOUSE = 0


def _send_input_move(dx: int, dy: int) -> None:
    """Inject a relative mouse-move event via Win32 SendInput.

    Unlike pynput's move() (which calls SetCursorPos / mouse_event),
    SendInput with MOUSEEVENTF_MOVE and no MOUSEEVENTF_ABSOLUTE bypasses
    the desktop cursor and is picked up by Raw-Input readers such as
    Minecraft Java Edition.
    """
    mi = _MOUSEINPUT(
        dx=dx,
        dy=dy,
        mouseData=0,
        dwFlags=_MOUSEEVENTF_MOVE,
        time=0,
        dwExtraInfo=None,
    )
    event = _INPUT(type=_INPUT_MOUSE, u=_INPUT_UNION(mi=mi))
    ctypes.windll.user32.SendInput(1, ctypes.byref(event), ctypes.sizeof(event))


class PynputKeySink:
    """Production keyboard/mouse sink; imports are deferred until use."""

    def __init__(self) -> None:
        try:
            from pynput.keyboard import Controller
            from pynput.mouse import Controller as MouseController
        except ImportError as error:
            raise RuntimeError("pynput is not installed") from error
        self._controller = Controller()
        self._mouse_controller = MouseController()

    def press(self, key: str) -> None:
        mouse_button = self._resolve_mouse_button(key)
        if mouse_button is not None:
            self._mouse_controller.press(mouse_button)
        else:
            self._controller.press(self._resolve_key(key))

    def release(self, key: str) -> None:
        mouse_button = self._resolve_mouse_button(key)
        if mouse_button is not None:
            self._mouse_controller.release(mouse_button)
        else:
            self._controller.release(self._resolve_key(key))

    def move(self, dx: int, dy: int) -> None:
        """Standard OS-cursor move — works in desktop apps and Minecraft
        inventory screens (when Raw Input is not capturing the pointer)."""
        self._mouse_controller.move(dx, dy)

    def move_raw(self, dx: int, dy: int) -> None:
        """Raw SendInput move — works in Minecraft in-game view even with
        Raw Input enabled, because it injects into the hardware input stream
        instead of repositioning the OS cursor."""
        _send_input_move(dx, dy)

    @staticmethod
    def _resolve_mouse_button(key: str):
        from pynput.mouse import Button

        aliases = {
            "mouse_left": Button.left,
            "mouse_right": Button.right,
            "mouse_middle": Button.middle,
        }
        return aliases.get(key.lower())

    @staticmethod
    def _resolve_mouse_movement(key: str) -> tuple[int, int] | None:
        """Resolve standard (pynput) mouse-move key names."""
        aliases = {
            "mouse_move_up": (0, -1),
            "mouse_up": (0, -1),
            "mouse_move_down": (0, 1),
            "mouse_down": (0, 1),
            "mouse_move_left": (-1, 0),
            "mouse_move_right": (1, 0),
        }
        return aliases.get(key.lower())

    @staticmethod
    def _resolve_raw_mouse_movement(key: str) -> tuple[int, int] | None:
        """Resolve raw (SendInput) mouse-move key names.

        These work in Minecraft even with Raw Input enabled and should be used
        for in-game camera look. They carry a separate sensitivity setting
        (``mouse_sensitivity_raw``) to allow tuning independently from the
        regular pynput moves used in inventory screens.
        """
        aliases = {
            "mouse_raw_up": (0, -1),
            "mouse_raw_down": (0, 1),
            "mouse_raw_left": (-1, 0),
            "mouse_raw_right": (1, 0),
        }
        return aliases.get(key.lower())

    @staticmethod
    def _resolve_key(key: str):
        """Resolve config-friendly names such as ``space`` to pynput keys."""
        if len(key) == 1:
            return key
        from pynput.keyboard import Key

        aliases = {
            "backspace": Key.backspace,
            "delete": Key.delete,
            "down": Key.down,
            "end": Key.end,
            "enter": Key.enter,
            "esc": Key.esc,
            "escape": Key.esc,
            "home": Key.home,
            "left": Key.left,
            "page_down": Key.page_down,
            "page_up": Key.page_up,
            "right": Key.right,
            "space": Key.space,
            "tab": Key.tab,
            "up": Key.up,
            "shift": Key.shift,
            "ctrl": Key.ctrl,
            "alt": Key.alt,
        }
        try:
            return aliases[key.lower()]
        except KeyError as error:
            raise ValueError(f"Unsupported keyboard key name: {key}") from error


class KeyboardController:
    """Safety-gated controller with reference-counted sustained keys."""

    def __init__(
        self,
        sink: KeySink,
        mappings: dict[tuple[str, int], NoteMapping] | None = None,
        release_delay_seconds: float = 0.08,
        trigger_hold_seconds: float = 0.06,
        mouse_sensitivity: float = 10,
        mouse_sensitivity_raw: float = 5,
        clock: Callable[[], float] = time.monotonic,
        focus_checker: Callable[[], bool] | None = None,
    ) -> None:
        if release_delay_seconds < 0:
            raise ValueError("release_delay_seconds must not be negative")
        if trigger_hold_seconds <= 0:
            raise ValueError("trigger_hold_seconds must be positive")
        if mouse_sensitivity <= 0:
            raise ValueError("mouse_sensitivity must be positive")
        if mouse_sensitivity_raw <= 0:
            raise ValueError("mouse_sensitivity_raw must be positive")
        self.sink = sink
        self.mappings = mappings or {}
        self.release_delay_seconds = release_delay_seconds
        self.trigger_hold_seconds = trigger_hold_seconds
        self.mouse_sensitivity = mouse_sensitivity
        self.mouse_sensitivity_raw = mouse_sensitivity_raw
        self._clock = clock
        self._focus_checker = focus_checker
        self.active = False
        self.focused = True
        self._held_by_note: dict[tuple[str, int], str] = {}
        self._held_keys: dict[str, int] = {}
        self._pending_release_at: dict[tuple[str, int], float] = {}
        self._pending_trigger_release_at: dict[str, float] = {}
        self.last_action: str | None = None

    @property
    def held_keys(self) -> tuple[str, ...]:
        return tuple(sorted(self._held_keys))

    def activate(self) -> None:
        self.active = True

    def deactivate(self) -> None:
        self.active = False
        self.release_all()

    def emergency_stop(self) -> None:
        self.active = False
        self.release_all()

    def set_focus(self, focused: bool) -> None:
        self.focused = focused
        if not focused:
            self.release_all()

    def process(self, event: NoteEvent) -> None:
        self.tick()
        if not self.active or not self.focused:
            return
        note = self._event_note(event)
        if event.kind in {"note_on", "change"} and note is not None:
            if event.kind == "change":
                for held_note in list(self._held_by_note):
                    if held_note != note:
                        self._release_note_immediately(held_note)
            self._activate_mapping(note)
        elif event.kind == "continue" and note is not None:
            self._continue_mapping(note)
        elif event.kind == "note_off" and note is not None:
            self._schedule_note_release(note)

    def tick(self) -> None:
        if self.active and self._focus_checker is not None:
            self.set_focus(self._focus_checker())
        now = self._clock()
        for note, deadline in list(self._pending_release_at.items()):
            if now >= deadline:
                self._pending_release_at.pop(note, None)
                self._release_note_immediately(note)
        for key, deadline in list(self._pending_trigger_release_at.items()):
            if now >= deadline:
                self._pending_trigger_release_at.pop(key, None)
                self.sink.release(key)

    def release_all(self) -> None:
        keys_to_release = set(self._held_keys) | set(self._pending_trigger_release_at)
        for key in keys_to_release:
            self.sink.release(key)
        self._held_by_note.clear()
        self._held_keys.clear()
        self._pending_release_at.clear()
        self._pending_trigger_release_at.clear()

    def _activate_mapping(self, note: tuple[str, int]) -> None:
        mapping = self.mappings.get(note)
        if mapping is None or not mapping.enabled:
            return
        self._pending_release_at.pop(note, None)
        # Check raw mouse movement first (Minecraft in-game look).
        raw_movement = PynputKeySink._resolve_raw_mouse_movement(mapping.key)
        if raw_movement is not None:
            self._move_mouse_raw(mapping.key, raw_movement)
            if mapping.mode is ControlMode.TRIGGER:
                self.last_action = f"{mapping.key} (trigger)"
            else:
                self.last_action = f"{mapping.key} (moving raw)"
            return
        # Standard pynput mouse movement (inventory / desktop).
        movement = PynputKeySink._resolve_mouse_movement(mapping.key)
        if movement is not None:
            self._move_mouse(mapping.key, movement)
            if mapping.mode is ControlMode.TRIGGER:
                self.last_action = f"{mapping.key} (trigger)"
            else:
                self.last_action = f"{mapping.key} (moving)"
            return
        if mapping.mode is ControlMode.TRIGGER:
            self.sink.press(mapping.key)
            self._pending_trigger_release_at[mapping.key] = (
                self._clock() + self.trigger_hold_seconds
            )
            self.last_action = f"{mapping.key} (trigger)"
            return
        if note not in self._held_by_note:
            self._held_by_note[note] = mapping.key
            count = self._held_keys.get(mapping.key, 0)
            self._held_keys[mapping.key] = count + 1
            if count == 0:
                self.sink.press(mapping.key)
            self.last_action = f"{mapping.key} (held)"

    def _continue_mapping(self, note: tuple[str, int]) -> None:
        mapping = self.mappings.get(note)
        if mapping is None or not mapping.enabled or mapping.mode is ControlMode.TRIGGER:
            return
        raw_movement = PynputKeySink._resolve_raw_mouse_movement(mapping.key)
        if raw_movement is not None:
            self._move_mouse_raw(mapping.key, raw_movement)
            return
        movement = PynputKeySink._resolve_mouse_movement(mapping.key)
        if movement is not None:
            self._move_mouse(mapping.key, movement)

    def _move_mouse(self, key: str, direction: tuple[int, int]) -> None:
        dx, dy = direction
        self.sink.move(
            round(dx * self.mouse_sensitivity),
            round(dy * self.mouse_sensitivity),
        )

    def _move_mouse_raw(self, key: str, direction: tuple[int, int]) -> None:
        dx, dy = direction
        self.sink.move_raw(
            round(dx * self.mouse_sensitivity_raw),
            round(dy * self.mouse_sensitivity_raw),
        )

    def _schedule_note_release(self, note: tuple[str, int]) -> None:
        if note in self._held_by_note:
            self._pending_release_at[note] = self._clock() + self.release_delay_seconds

    def _release_note_immediately(self, note: tuple[str, int]) -> None:
        key = self._held_by_note.pop(note, None)
        self._pending_release_at.pop(note, None)
        if key is None:
            return
        count = self._held_keys[key] - 1
        if count == 0:
            self._held_keys.pop(key)
            self.sink.release(key)
        else:
            self._held_keys[key] = count

    @staticmethod
    def _event_note(event: NoteEvent) -> tuple[str, int] | None:
        if event.note_name is None or event.octave is None:
            return None
        return (event.note_name, event.octave)
