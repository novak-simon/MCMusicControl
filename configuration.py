"""Loading and validating the user-editable Stage 4 mapping configuration."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path

from keyboard_controller import ControlMode, NoteMapping


@dataclass(frozen=True)
class AppConfig:
    mappings: dict[tuple[str, int], NoteMapping]
    release_delay_seconds: float = 0.08
    trigger_hold_seconds: float = 0.06
    mouse_sensitivity: float = 10
    mouse_sensitivity_raw: float = 5


def load_config(path: Path) -> AppConfig:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise ValueError(f"Configuration file not found: {path}") from None
    except json.JSONDecodeError as error:
        raise ValueError(f"Invalid JSON in {path}: {error.msg}") from error
    if not isinstance(raw, dict):
        raise ValueError("Configuration root must be an object")

    mappings: dict[tuple[str, int], NoteMapping] = {}
    raw_mappings = raw.get("mappings")
    if not isinstance(raw_mappings, dict):
        raise ValueError("Configuration must contain a mappings object")
    for note_text, raw_mapping in raw_mappings.items():
        note = _parse_note(note_text)
        if not isinstance(raw_mapping, dict):
            raise ValueError(f"Mapping for {note_text} must be an object")
        key = raw_mapping.get("key")
        mode = raw_mapping.get("mode")
        enabled = raw_mapping.get("enabled", True)
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"Mapping for {note_text} needs a non-empty key")
        try:
            control_mode = ControlMode(mode)
        except ValueError:
            raise ValueError(f"Invalid mode for {note_text}: {mode}") from None
        if not isinstance(enabled, bool):
            raise ValueError(f"Enabled flag for {note_text} must be boolean")
        mappings[note] = NoteMapping(key.strip().lower(), control_mode, enabled)

    release_delay = _positive_number(raw, "release_delay_seconds", allow_zero=True)
    trigger_hold = _positive_number(raw, "trigger_hold_seconds")
    mouse_sensitivity = (
        _positive_number(raw, "mouse_sensitivity")
        if "mouse_sensitivity" in raw
        else 10
    )
    mouse_sensitivity_raw = (
        _positive_number(raw, "mouse_sensitivity_raw")
        if "mouse_sensitivity_raw" in raw
        else 5
    )
    return AppConfig(mappings, release_delay, trigger_hold, mouse_sensitivity, mouse_sensitivity_raw)


def _parse_note(value: str) -> tuple[str, int]:
    if not isinstance(value, str) or len(value) < 2:
        raise ValueError(f"Invalid note name: {value}")
    name = value[:-1]
    try:
        octave = int(value[-1])
    except ValueError:
        raise ValueError(f"Invalid note name: {value}") from None
    if name not in {"A", "A#", "B", "C", "C#", "D", "D#", "E", "F", "F#", "G", "G#"}:
        raise ValueError(f"Invalid note name: {value}")
    return name, octave


def _positive_number(raw: dict, key: str, allow_zero: bool = False) -> float:
    value = raw.get(key)
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError(f"{key} must be a number")
    result = float(value)
    if result < 0 or (result == 0 and not allow_zero):
        raise ValueError(f"{key} must be {'non-negative' if allow_zero else 'positive'}")
    return result
