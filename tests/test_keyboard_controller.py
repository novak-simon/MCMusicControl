from keyboard_controller import ControlMode, KeyboardController, NoteMapping, PynputKeySink
from note_state import NoteEvent


class MockKeyboard:
    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []

    def press(self, key: str) -> None:
        self.events.append(("press", key))

    def release(self, key: str) -> None:
        self.events.append(("release", key))

    def move(self, dx: int, dy: int) -> None:
        self.events.append(("move", f"{dx},{dy}"))

    def move_raw(self, dx: int, dy: int) -> None:
        self.events.append(("move_raw", f"{dx},{dy}"))


def event(kind: str, note: str = "A", octave: int = 4) -> NoteEvent:
    return NoteEvent(kind, note, octave, 440.0, 0.9)


def controller(
    mock: MockKeyboard,
    clock: list[float],
    mappings: dict[tuple[str, int], NoteMapping] | None = None,
) -> KeyboardController:
    return KeyboardController(
        mock,
        mappings or {("A", 4): NoteMapping("w", ControlMode.SUSTAINED)},
        release_delay_seconds=0.1,
        clock=lambda: clock[0],
    )


def test_control_is_explicitly_gated() -> None:
    mock, clock = MockKeyboard(), [0.0]
    control = controller(mock, clock)
    control.process(event("note_on"))
    assert mock.events == []
    control.activate()
    control.process(event("note_on"))
    assert mock.events == [("press", "w")]


def test_sustained_note_has_one_press_and_delayed_release() -> None:
    mock, clock = MockKeyboard(), [0.0]
    control = controller(mock, clock)
    control.activate()
    control.process(event("note_on"))
    control.process(event("continue"))
    control.process(event("note_off"))
    assert mock.events == [("press", "w")]
    clock[0] = 0.11
    control.tick()
    assert mock.events == [("press", "w"), ("release", "w")]


def test_trigger_note_presses_once() -> None:
    mock, clock = MockKeyboard(), [0.0]
    control = controller(
        mock,
        clock,
        {("A", 4): NoteMapping("space", ControlMode.TRIGGER)},
    )
    control.activate()
    control.process(event("note_on"))
    control.process(event("continue"))
    assert mock.events == [("press", "space")]
    clock[0] = 0.06
    control.tick()
    assert mock.events == [("press", "space"), ("release", "space")]


def test_trigger_hold_can_be_configured() -> None:
    mock, clock = MockKeyboard(), [0.0]
    control = KeyboardController(
        mock,
        {("A", 4): NoteMapping("e", ControlMode.TRIGGER)},
        trigger_hold_seconds=0.2,
        clock=lambda: clock[0],
    )
    control.activate()
    control.process(event("note_on"))
    clock[0] = 0.1
    control.tick()
    assert mock.events == [("press", "e")]
    clock[0] = 0.2
    control.tick()
    assert mock.events == [("press", "e"), ("release", "e")]


def test_shared_key_releases_only_after_both_notes_end() -> None:
    mock, clock = MockKeyboard(), [0.0]
    control = controller(
        mock,
        clock,
        {
            ("A", 4): NoteMapping("w", ControlMode.SUSTAINED),
            ("G", 4): NoteMapping("w", ControlMode.SUSTAINED),
        },
    )
    control.activate()
    control.process(event("note_on", "A"))
    control.process(event("note_on", "G"))
    control.process(event("note_off", "A"))
    clock[0] = 0.11
    control.tick()
    assert mock.events == [("press", "w")]
    control.process(event("note_off", "G"))
    clock[0] = 0.22
    control.tick()
    assert mock.events == [("press", "w"), ("release", "w")]


def test_pitch_change_releases_previous_note() -> None:
    mock, clock = MockKeyboard(), [0.0]
    control = controller(
        mock,
        clock,
        {
            ("A", 4): NoteMapping("w", ControlMode.SUSTAINED),
            ("G", 4): NoteMapping("s", ControlMode.SUSTAINED),
        },
    )
    control.activate()
    control.process(event("note_on", "A"))
    control.process(event("change", "G"))
    assert mock.events == [("press", "w"), ("release", "w"), ("press", "s")]


def test_focus_loss_and_emergency_stop_release_everything() -> None:
    mock, clock = MockKeyboard(), [0.0]
    control = controller(mock, clock)
    control.activate()
    control.process(event("note_on"))
    control.set_focus(False)
    assert mock.events == [("press", "w"), ("release", "w")]
    control.set_focus(True)
    control.activate()
    control.process(event("note_on"))
    control.emergency_stop()
    assert mock.events == [("press", "w"), ("release", "w"), ("press", "w"), ("release", "w")]


def test_pynput_resolves_space_and_escape_names() -> None:
    from pynput.keyboard import Key
    from pynput.mouse import Button

    assert PynputKeySink._resolve_key("space") is Key.space
    assert PynputKeySink._resolve_key("escape") is Key.esc
    assert PynputKeySink._resolve_key("w") == "w"
    assert PynputKeySink._resolve_mouse_button("mouse_left") is Button.left
    assert PynputKeySink._resolve_mouse_button("mouse_right") is Button.right


def test_sustained_mouse_movement_repeats_with_configured_sensitivity() -> None:
    mock, clock = MockKeyboard(), [0.0]
    control = KeyboardController(
        mock,
        {("A", 4): NoteMapping("mouse_move_right", ControlMode.SUSTAINED)},
        mouse_sensitivity=7,
        clock=lambda: clock[0],
    )
    control.activate()
    control.process(event("note_on"))
    control.process(event("continue"))
    assert mock.events == [("move", "7,0"), ("move", "7,0")]


def test_trigger_mouse_movement_does_not_repeat_on_continue() -> None:
    mock, clock = MockKeyboard(), [0.0]
    control = KeyboardController(
        mock,
        {("A", 4): NoteMapping("mouse_move_up", ControlMode.TRIGGER)},
        mouse_sensitivity=4,
        clock=lambda: clock[0],
    )
    control.activate()
    control.process(event("note_on"))
    control.process(event("continue"))
    assert mock.events == [("move", "0,-4")]


def test_mouse_movement_aliases_are_distinct_from_buttons() -> None:
    assert PynputKeySink._resolve_mouse_movement("mouse_up") == (0, -1)
    assert PynputKeySink._resolve_mouse_movement("mouse_move_left") == (-1, 0)
    assert PynputKeySink._resolve_mouse_movement("mouse_left") is None


def test_raw_mouse_movement_uses_move_raw_and_raw_sensitivity() -> None:
    """mouse_raw_* keys must call move_raw() with mouse_sensitivity_raw."""
    mock, clock = MockKeyboard(), [0.0]
    control = KeyboardController(
        mock,
        {("A", 4): NoteMapping("mouse_raw_right", ControlMode.SUSTAINED)},
        mouse_sensitivity=10,
        mouse_sensitivity_raw=3,
        clock=lambda: clock[0],
    )
    control.activate()
    control.process(event("note_on"))
    control.process(event("continue"))
    # Should use move_raw, not move, with sensitivity 3
    assert mock.events == [("move_raw", "3,0"), ("move_raw", "3,0")]


def test_raw_mouse_trigger_does_not_repeat_on_continue() -> None:
    mock, clock = MockKeyboard(), [0.0]
    control = KeyboardController(
        mock,
        {("A", 4): NoteMapping("mouse_raw_up", ControlMode.TRIGGER)},
        mouse_sensitivity_raw=6,
        clock=lambda: clock[0],
    )
    control.activate()
    control.process(event("note_on"))
    control.process(event("continue"))
    assert mock.events == [("move_raw", "0,-6")]


def test_raw_mouse_aliases_resolve_correctly() -> None:
    assert PynputKeySink._resolve_raw_mouse_movement("mouse_raw_up") == (0, -1)
    assert PynputKeySink._resolve_raw_mouse_movement("mouse_raw_down") == (0, 1)
    assert PynputKeySink._resolve_raw_mouse_movement("mouse_raw_left") == (-1, 0)
    assert PynputKeySink._resolve_raw_mouse_movement("mouse_raw_right") == (1, 0)
    # Regular move keys must NOT match raw aliases
    assert PynputKeySink._resolve_raw_mouse_movement("mouse_move_up") is None
    assert PynputKeySink._resolve_raw_mouse_movement("mouse_left") is None


def test_standard_move_keys_still_use_move_not_move_raw() -> None:
    """Ensure old mouse_move_* keys still route through move(), not move_raw()."""
    mock, clock = MockKeyboard(), [0.0]
    control = KeyboardController(
        mock,
        {("A", 4): NoteMapping("mouse_move_down", ControlMode.SUSTAINED)},
        mouse_sensitivity=5,
        clock=lambda: clock[0],
    )
    control.activate()
    control.process(event("note_on"))
    assert mock.events == [("move", "0,5")]
    assert not any(e[0] == "move_raw" for e in mock.events)
