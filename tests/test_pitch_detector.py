import math

from pitch_detector import AubioPitchDetector, AutocorrelationPitchDetector, frequency_to_note


def tone(frequency: float, sample_rate: int = 44100, count: int = 4096) -> list[float]:
    return [math.sin(2 * math.pi * frequency * index / sample_rate) for index in range(count)]


def test_frequency_to_note() -> None:
    assert frequency_to_note(440) == ("A", 4)
    assert frequency_to_note(261.63) == ("C", 4)
    assert frequency_to_note(0) is None


def test_detects_saxophone_range_tone() -> None:
    result = AutocorrelationPitchDetector().estimate(tone(440))
    assert result.is_valid
    assert result.note_name == "A"
    assert result.octave == 4
    assert abs(result.frequency_hz - 440) < 2
    assert result.confidence > 0.7


def test_silence_is_not_a_note() -> None:
    result = AutocorrelationPitchDetector().estimate([0.0] * 4096)
    assert not result.is_valid
    assert result.frequency_hz is None


def test_expected_range_filters_signal() -> None:
    result = AutocorrelationPitchDetector(min_frequency_hz=300, max_frequency_hz=500).estimate(tone(100))
    assert not result.is_valid


def test_aubio_detects_sustained_tone_with_confidence() -> None:
    detector = AubioPitchDetector()
    results = [detector.estimate(tone(440, count=1024)) for _ in range(4)]
    result = results[-1]
    assert result.is_valid
    assert result.note_name == "A"
    assert result.confidence > 0.5
