"""Temporal stabilization of frame-by-frame pitch estimates."""

from __future__ import annotations

from dataclasses import dataclass

from pitch_detector import PitchEstimate


@dataclass(frozen=True)
class NoteEvent:
    kind: str
    note_name: str | None
    octave: int | None
    frequency_hz: float | None
    confidence: float


class NoteStateTracker:
    """Convert noisy estimates into note_on, change, continue, and note_off."""

    def __init__(
        self,
        onset_frames: int = 1,
        change_frames: int = 2,
        release_frames: int = 2,
    ) -> None:
        if min(onset_frames, change_frames, release_frames) < 1:
            raise ValueError("state thresholds must be at least one frame")
        self.onset_frames = onset_frames
        self.change_frames = change_frames
        self.release_frames = release_frames
        self.active_note: tuple[str, int] | None = None
        self._candidate: tuple[str, int] | None = None
        self._candidate_frames = 0
        self._invalid_frames = 0

    def reset(self) -> None:
        self.active_note = None
        self._candidate = None
        self._candidate_frames = 0
        self._invalid_frames = 0

    def update(self, estimate: PitchEstimate) -> NoteEvent:
        if not estimate.is_valid or estimate.note_name is None or estimate.octave is None:
            self._candidate = None
            self._candidate_frames = 0
            self._invalid_frames += 1
            if self.active_note and self._invalid_frames >= self.release_frames:
                ended_note = self.active_note
                self.active_note = None
                return NoteEvent("note_off", ended_note[0], ended_note[1], None, estimate.confidence)
            return self._event("uncertain", estimate)

        self._invalid_frames = 0
        note = (estimate.note_name, estimate.octave)
        if note == self.active_note:
            self._candidate = None
            self._candidate_frames = 0
            return self._event("continue", estimate)

        if note != self._candidate:
            self._candidate = note
            self._candidate_frames = 1
        else:
            self._candidate_frames += 1

        threshold = self.onset_frames if self.active_note is None else self.change_frames
        if self._candidate_frames < threshold:
            return self._event("uncertain", estimate)

        kind = "note_on" if self.active_note is None else "change"
        self.active_note = note
        self._candidate = None
        self._candidate_frames = 0
        return self._event(kind, estimate)

    @staticmethod
    def _event(kind: str, estimate: PitchEstimate) -> NoteEvent:
        return NoteEvent(
            kind,
            estimate.note_name,
            estimate.octave,
            estimate.frequency_hz,
            estimate.confidence,
        )
