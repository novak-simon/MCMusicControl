"""Real-time monophonic pitch estimation using autocorrelation."""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Sequence


@dataclass(frozen=True)
class PitchEstimate:
    frequency_hz: float | None
    note_name: str | None
    octave: int | None
    confidence: float
    is_valid: bool


def frequency_to_note(frequency_hz: float) -> tuple[str, int] | None:
    """Return the nearest equal-temperament note, or None for invalid input."""
    if frequency_hz <= 0 or not math.isfinite(frequency_hz):
        return None
    midi = round(69 + 12 * math.log2(frequency_hz / 440.0))
    octave = midi // 12 - 1
    return ("C C# D D# E F F# G G# A A# B".split()[midi % 12], octave)


def _parabolic_peak(left: float, center: float, right: float) -> float:
    denominator = left - 2 * center + right
    if denominator == 0:
        return 0.0
    return 0.5 * (left - right) / denominator


class AutocorrelationPitchDetector:
    """Estimate a fundamental from one mono PCM frame."""

    def __init__(
        self,
        sample_rate: int = 44100,
        min_frequency_hz: float = 100.0,
        max_frequency_hz: float = 1200.0,
        min_confidence: float = 0.35,
        rms_threshold: float = 0.01,
    ) -> None:
        if not 0 < min_frequency_hz < max_frequency_hz:
            raise ValueError("min_frequency_hz must be below max_frequency_hz")
        if not 0 <= min_confidence <= 1:
            raise ValueError("min_confidence must be between 0 and 1")
        self.sample_rate = sample_rate
        self.min_frequency_hz = min_frequency_hz
        self.max_frequency_hz = max_frequency_hz
        self.min_confidence = min_confidence
        self.rms_threshold = rms_threshold

    def estimate(self, samples: Sequence[float]) -> PitchEstimate:
        if len(samples) < 4:
            return PitchEstimate(None, None, None, 0.0, False)
        centered = [float(value) for value in samples]
        mean = sum(centered) / len(centered)
        centered = [value - mean for value in centered]
        rms = math.sqrt(sum(value * value for value in centered) / len(centered))
        if rms < self.rms_threshold:
            return PitchEstimate(None, None, None, 0.0, False)

        min_lag = max(1, int(self.sample_rate / self.max_frequency_hz))
        max_lag = min(len(centered) - 2, int(self.sample_rate / self.min_frequency_hz))
        if min_lag >= max_lag:
            return PitchEstimate(None, None, None, 0.0, False)

        energy = sum(value * value for value in centered)
        correlations = []
        for lag in range(min_lag, max_lag + 1):
            correlation = sum(
                centered[index] * centered[index + lag]
                for index in range(len(centered) - lag)
            ) / energy
            correlations.append(correlation)
        peak_index = max(range(len(correlations)), key=correlations.__getitem__)
        peak_lag = min_lag + peak_index
        confidence = max(0.0, min(1.0, correlations[peak_index]))
        if 0 < peak_index < len(correlations) - 1:
            peak_lag += _parabolic_peak(
                correlations[peak_index - 1],
                correlations[peak_index],
                correlations[peak_index + 1],
            )
        if confidence < self.min_confidence or peak_lag <= 0:
            return PitchEstimate(None, None, None, confidence, False)

        frequency = self.sample_rate / peak_lag
        note = frequency_to_note(frequency)
        if note is None:
            return PitchEstimate(None, None, None, confidence, False)
        return PitchEstimate(frequency, note[0], note[1], confidence, True)


class AubioPitchDetector:
    """Fast pitch estimator backed by aubio's YIN implementation."""

    def __init__(
        self,
        sample_rate: int = 44100,
        buffer_size: int = 2048,
        hop_size: int = 1024,
        min_frequency_hz: float = 100.0,
        max_frequency_hz: float = 1200.0,
        min_confidence: float = 0.15,
    ) -> None:
        try:
            import aubio
        except ImportError as error:
            raise RuntimeError("aubio is not installed") from error
        if not 0 <= min_confidence <= 1:
            raise ValueError("min_confidence must be between 0 and 1")
        self.sample_rate = sample_rate
        self.min_frequency_hz = min_frequency_hz
        self.max_frequency_hz = max_frequency_hz
        self.min_confidence = min_confidence
        # yin exposes a meaningful confidence score in aubio 0.4.9 on Windows.
        # yinfft reports zero confidence even for clean, sustained tones.
        self._pitch = aubio.pitch("yin", buffer_size, hop_size, sample_rate)
        self._pitch.set_unit("Hz")
        self._pitch.set_silence(-70)
        self._vector = aubio.fvec(hop_size)

    def estimate(self, samples: Sequence[float]) -> PitchEstimate:
        if len(samples) != len(self._vector):
            return PitchEstimate(None, None, None, 0.0, False)
        for index, sample in enumerate(samples):
            self._vector[index] = float(sample)
        frequency = float(self._pitch(self._vector)[0])
        confidence = max(0.0, min(1.0, float(self._pitch.get_confidence())))
        if (
            frequency < self.min_frequency_hz
            or frequency > self.max_frequency_hz
            or confidence < self.min_confidence
        ):
            return PitchEstimate(None, None, None, confidence, False)
        note = frequency_to_note(frequency)
        if note is None:
            return PitchEstimate(None, None, None, confidence, False)
        return PitchEstimate(frequency, note[0], note[1], confidence, True)


def create_pitch_detector(**kwargs: float | int) -> AutocorrelationPitchDetector | AubioPitchDetector:
    """Prefer aubio for real-time use and fall back when it is unavailable."""
    try:
        return AubioPitchDetector(**kwargs)
    except (ImportError, RuntimeError):
        fallback_kwargs = {
            key: value
            for key, value in kwargs.items()
            if key not in {"buffer_size", "hop_size"}
        }
        return AutocorrelationPitchDetector(**fallback_kwargs)
