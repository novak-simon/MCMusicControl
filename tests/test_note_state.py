from note_state import NoteStateTracker
from pitch_detector import PitchEstimate


def estimate(note: str | None, octave: int | None, valid: bool = True) -> PitchEstimate:
    return PitchEstimate(440.0 if valid else None, note, octave, 0.9 if valid else 0.0, valid)


def test_onset_is_immediate_for_quick_notes() -> None:
    tracker = NoteStateTracker()
    assert tracker.update(estimate("A", 4)).kind == "note_on"


def test_sustained_note_does_not_repeat_note_on() -> None:
    tracker = NoteStateTracker()
    assert tracker.update(estimate("A", 4)).kind == "note_on"
    assert tracker.update(estimate("A", 4)).kind == "continue"
    assert tracker.update(estimate("A", 4)).kind == "continue"


def test_pitch_change_requires_two_frames() -> None:
    tracker = NoteStateTracker()
    tracker.update(estimate("A", 4))
    assert tracker.update(estimate("G", 4)).kind == "uncertain"
    assert tracker.update(estimate("G", 4)).kind == "change"


def test_brief_gap_is_not_note_off() -> None:
    tracker = NoteStateTracker()
    tracker.update(estimate("A", 4))
    assert tracker.update(estimate(None, None, False)).kind == "uncertain"
    assert tracker.active_note == ("A", 4)


def test_silence_ends_note_after_release_threshold() -> None:
    tracker = NoteStateTracker()
    tracker.update(estimate("A", 4))
    tracker.update(estimate(None, None, False))
    assert tracker.update(estimate(None, None, False)).kind == "note_off"
    assert tracker.active_note is None


def test_reset_clears_active_note() -> None:
    tracker = NoteStateTracker()
    tracker.update(estimate("A", 4))
    tracker.reset()
    assert tracker.active_note is None
