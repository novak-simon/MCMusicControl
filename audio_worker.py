"""Background microphone capture for the Stage 1 interface."""

from __future__ import annotations

from collections.abc import Callable
import threading

from pitch_detector import AutocorrelationPitchDetector, PitchEstimate


class AudioWorker:
    def __init__(
        self,
        device: int | None,
        detector: AutocorrelationPitchDetector,
        block_size: int = 1024,
        on_estimate: Callable[[PitchEstimate], None] | None = None,
        on_status: Callable[[str], None] | None = None,
    ) -> None:
        self.device = device
        self.detector = detector
        self.block_size = block_size
        self.on_estimate = on_estimate
        self.on_status = on_status
        self._stop_event = threading.Event()
        self._thread: threading.Thread | None = None
        self._stream = None

    @staticmethod
    def list_devices() -> list[tuple[int, str]]:
        try:
            import sounddevice as sd
        except ImportError:
            return []
        return [
            (index, str(info["name"]))
            for index, info in enumerate(sd.query_devices())
            if int(info.get("max_input_channels", 0)) > 0
        ]

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, name="audio-capture", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._stream is not None:
            self._stream.stop()
            self._stream.close()
        if self._thread:
            self._thread.join(timeout=2)
        self._thread = None
        self._stream = None

    def _run(self) -> None:
        try:
            import sounddevice as sd
        except ImportError:
            self._report_status("sounddevice is not installed")
            return

        def callback(indata, frames, time_info, status) -> None:
            if status:
                self._report_status(str(status))
            samples = [float(frame[0]) for frame in indata]
            try:
                estimate = self.detector.estimate(samples)
            except Exception as error:
                self._report_status(f"Pitch detection error: {error}")
                return
            if self.on_estimate:
                self.on_estimate(estimate)

        try:
            self._stream = sd.InputStream(
                device=self.device,
                channels=1,
                samplerate=self.detector.sample_rate,
                blocksize=self.block_size,
                callback=callback,
            )
            self._stream.start()
            self._report_status("Microphone active")
            while not self._stop_event.wait(0.1):
                pass
        except Exception as error:
            self._report_status(f"Audio error: {error}")
        finally:
            if self._stream is not None:
                self._stream.stop()
                self._stream.close()
            self._stream = None

    def _report_status(self, message: str) -> None:
        if self.on_status:
            self.on_status(message)
