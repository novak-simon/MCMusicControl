"""Safe translation of stable note events into keyboard actions."""

from __future__ import annotations

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


class PynputKeySink:
    """Production keyboard sink; importing pynput is deferred until use."""

    def __init__(self) -> None:
        try:
            from pynput.keyboard import Controller
        except ImportError as error:
            raise RuntimeError("pynput is not installed") from error
        self._controller = Controller()

    def press(self, key: str) -> None:
        self._controller.press(self._resolve_key(key))

    def release(self, key: str) -> None:
        self._controller.release(self._resolve_key(key))

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
        clock: Callable[[], float] = time.monotonic,
        focus_checker: Callable[[], bool] | None = None,
    ) -> None:
        if release_delay_seconds < 0:
            raise ValueError("release_delay_seconds must not be negative")
        self.sink = sink
        self.mappings = mappings or {}
        self.release_delay_seconds = release_delay_seconds
        self._clock = clock
        self._focus_checker = focus_checker
        self.active = False
        self.focused = True
        self._held_by_note: dict[tuple[str, int], str] = {}
        self._held_keys: dict[str, int] = {}
        self._pending_release_at: dict[tuple[str, int], float] = {}
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

    def release_all(self) -> None:
        for key in list(self._held_keys):
            self.sink.release(key)
        self._held_by_note.clear()
        self._held_keys.clear()
        self._pending_release_at.clear()

    def _activate_mapping(self, note: tuple[str, int]) -> None:
        mapping = self.mappings.get(note)
        if mapping is None or not mapping.enabled:
            return
        self._pending_release_at.pop(note, None)
        if mapping.mode is ControlMode.TRIGGER:
            self.sink.press(mapping.key)
            self.sink.release(mapping.key)
            self.last_action = f"{mapping.key} (trigger)"
            return
        if note not in self._held_by_note:
            self._held_by_note[note] = mapping.key
            count = self._held_keys.get(mapping.key, 0)
            self._held_keys[mapping.key] = count + 1
            if count == 0:
                self.sink.press(mapping.key)
            self.last_action = f"{mapping.key} (held)"

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
