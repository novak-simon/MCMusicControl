from keyboard_controller import ControlMode, KeyboardController, NoteMapping, PynputKeySink
from note_state import NoteEvent


class MockKeyboard:
    def __init__(self) -> None:
        self.events: list[tuple[str, str]] = []

    def press(self, key: str) -> None:
        self.events.append(("press", key))

    def release(self, key: str) -> None:
        self.events.append(("release", key))


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

    assert PynputKeySink._resolve_key("space") is Key.space
    assert PynputKeySink._resolve_key("escape") is Key.esc
    assert PynputKeySink._resolve_key("w") == "w"
