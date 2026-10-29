"""Tkinter application for live Stage 1 pitch detection."""

from __future__ import annotations

import queue
import tkinter as tk
from tkinter import messagebox, ttk

from audio_worker import AudioWorker
from focus_guard import minecraft_is_focused
from keyboard_controller import ControlMode, KeyboardController, NoteMapping, PynputKeySink
from note_state import NoteStateTracker
from pitch_detector import PitchEstimate, create_pitch_detector


class PitchApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Saxophone Minecraft Controller - Pitch Detector")
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.worker: AudioWorker | None = None
        self.tracker = NoteStateTracker()
        self.controller: KeyboardController | None = None
        self.devices = AudioWorker.list_devices()
        self.device_var = tk.StringVar(value=self.devices[0][1] if self.devices else "No microphone found")
        self.status_var = tk.StringVar(value="Stopped")
        self.note_var = tk.StringVar(value="--")
        self.frequency_var = tk.StringVar(value="-- Hz")
        self.confidence_var = tk.StringVar(value="--")
        self.min_frequency_var = tk.StringVar(value="100")
        self.max_frequency_var = tk.StringVar(value="1200")
        self.confidence_threshold_var = tk.StringVar(value="0.15")
        self.control_var = tk.StringVar(value="Keyboard control inactive")
        self.held_keys_var = tk.StringVar(value="Held keys: none")
        self._build()
        self.root.after(50, self._drain_events)

    def _build(self) -> None:
        frame = ttk.Frame(self.root, padding=16)
        frame.grid(sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        ttk.Label(frame, text="Microphone").grid(row=0, column=0, sticky="w")
        ttk.Combobox(
            frame,
            textvariable=self.device_var,
            values=[name for _, name in self.devices],
            state="readonly",
            width=45,
        ).grid(row=0, column=1, columnspan=2, sticky="ew", padx=(8, 0))
        values = [("Note", self.note_var), ("Frequency", self.frequency_var), ("Confidence", self.confidence_var)]
        for row, (label, variable) in enumerate(values, start=1):
            ttk.Label(frame, text=f"{label}:").grid(row=row, column=0, sticky="w", pady=(12, 0))
            ttk.Label(frame, textvariable=variable, font=("Segoe UI", 16)).grid(
                row=row, column=1, sticky="w", padx=(8, 0), pady=(12, 0)
            )
        settings = ttk.LabelFrame(frame, text="Expected pitch range (Hz)", padding=8)
        settings.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(16, 0))
        ttk.Label(settings, text="Minimum").grid(row=0, column=0)
        ttk.Entry(settings, textvariable=self.min_frequency_var, width=8).grid(row=0, column=1, padx=6)
        ttk.Label(settings, text="Maximum").grid(row=0, column=2)
        ttk.Entry(settings, textvariable=self.max_frequency_var, width=8).grid(row=0, column=3, padx=6)
        ttk.Label(settings, text="Sensitivity (min confidence)").grid(row=1, column=0, pady=(8, 0))
        ttk.Entry(settings, textvariable=self.confidence_threshold_var, width=8).grid(
            row=1, column=1, padx=6, pady=(8, 0)
        )
        ttk.Label(frame, textvariable=self.status_var).grid(row=5, column=0, columnspan=3, sticky="w", pady=(12, 0))
        ttk.Label(frame, textvariable=self.control_var).grid(row=6, column=0, columnspan=3, sticky="w", pady=(8, 0))
        ttk.Label(frame, textvariable=self.held_keys_var).grid(row=7, column=0, columnspan=3, sticky="w")
        ttk.Button(frame, text="Start audio", command=self.start).grid(row=8, column=0, sticky="e", pady=(16, 0))
        ttk.Button(frame, text="Stop audio", command=self.stop).grid(row=8, column=1, sticky="w", padx=(8, 0), pady=(16, 0))
        ttk.Button(frame, text="Activate controls", command=self.activate_controls).grid(
            row=9, column=0, sticky="e", pady=(8, 0)
        )
        ttk.Button(frame, text="Deactivate", command=self.deactivate_controls).grid(
            row=9, column=1, sticky="w", padx=(8, 0), pady=(8, 0)
        )
        ttk.Button(frame, text="EMERGENCY STOP", command=self.emergency_stop).grid(
            row=9, column=2, sticky="w", padx=(8, 0), pady=(8, 0)
        )

    def start(self) -> None:
        if self.worker:
            return
        try:
            detector = create_pitch_detector(
                min_frequency_hz=float(self.min_frequency_var.get()),
                max_frequency_hz=float(self.max_frequency_var.get()),
                min_confidence=float(self.confidence_threshold_var.get()),
                buffer_size=2048,
                hop_size=1024,
            )
        except ValueError as error:
            messagebox.showerror("Invalid pitch range", str(error))
            return
        selected_name = self.device_var.get()
        device = next((index for index, name in self.devices if name == selected_name), None)
        self.worker = AudioWorker(device, detector, on_estimate=self._on_estimate, on_status=self._on_status)
        self.worker.start()
        self.status_var.set("Starting microphone...")

    def activate_controls(self) -> None:
        if self.controller is not None and self.controller.active:
            return
        try:
            self.controller = KeyboardController(
                PynputKeySink(),
                {
                    ("A", 4): NoteMapping("w", ControlMode.SUSTAINED),
                    ("G", 4): NoteMapping("s", ControlMode.SUSTAINED),
                    ("F", 4): NoteMapping("a", ControlMode.SUSTAINED),
                    ("E", 4): NoteMapping("d", ControlMode.SUSTAINED),
                    ("D", 4): NoteMapping("space", ControlMode.SUSTAINED),
                },
                focus_checker=minecraft_is_focused,
            )
            self.controller.activate()
            self.control_var.set("Keyboard control ACTIVE")
        except RuntimeError as error:
            messagebox.showerror("Keyboard control unavailable", str(error))

    def deactivate_controls(self) -> None:
        if self.controller:
            self.controller.deactivate()
        self.control_var.set("Keyboard control inactive")
        self.held_keys_var.set("Held keys: none")

    def emergency_stop(self) -> None:
        if self.controller:
            self.controller.emergency_stop()
        self.control_var.set("EMERGENCY STOP - controls inactive")
        self.held_keys_var.set("Held keys: none")

    def stop(self) -> None:
        if self.worker:
            self.worker.stop()
            self.worker = None
        self.deactivate_controls()
        self.tracker.reset()
        self.status_var.set("Stopped")
        self.note_var.set("--")
        self.frequency_var.set("-- Hz")
        self.confidence_var.set("--")

    def _on_estimate(self, estimate: PitchEstimate) -> None:
        self.events.put(("estimate", estimate))

    def _on_status(self, status: str) -> None:
        self.events.put(("status", status))

    def _drain_events(self) -> None:
        while not self.events.empty():
            kind, value = self.events.get()
            if kind == "status":
                self.status_var.set(str(value))
            else:
                estimate = value
                assert isinstance(estimate, PitchEstimate)
                if estimate.is_valid:
                    self.note_var.set(f"{estimate.note_name}{estimate.octave}")
                    self.frequency_var.set(f"{estimate.frequency_hz:.1f} Hz")
                    self.confidence_var.set(f"{estimate.confidence:.0%} (valid)")
                else:
                    self.note_var.set("Silence / unreliable")
                    self.frequency_var.set("-- Hz")
                    self.confidence_var.set(f"{estimate.confidence:.0%} (low)")
                event = self.tracker.update(estimate)
                if self.controller:
                    try:
                        self.controller.process(event)
                        self.controller.tick()
                        held = ", ".join(self.controller.held_keys) or "none"
                        self.held_keys_var.set(f"Held keys: {held}")
                    except (OSError, RuntimeError, ValueError) as error:
                        self.controller.emergency_stop()
                        self.control_var.set("EMERGENCY STOP - keyboard error")
                        self.status_var.set(f"Keyboard control error: {error}")
                        continue
                self.status_var.set(f"Microphone active - {event.kind}")
        self.root.after(50, self._drain_events)

    def close(self) -> None:
        self.stop()
        self.root.destroy()


def main() -> None:
    root = tk.Tk()
    PitchApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
