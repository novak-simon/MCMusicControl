# Saxophone-Controlled Minecraft

## Stage 1: live pitch detector

Stage 1 provides a Tkinter window that captures mono microphone audio in a
background thread and estimates the fundamental frequency using normalized
autocorrelation. It displays the nearest equal-temperament note, octave,
frequency, and a confidence indicator. Silence and signals below the
confidence threshold are shown as `Silence / unreliable`.

The detector accepts a configurable expected frequency range. This is a
frequency calibration range, not a claim that written saxophone note names
have the same concert-pitch frequency. The sensitivity field controls the
minimum normalized autocorrelation confidence accepted as a valid note.

## Installation

Use Python 3.13 on Windows:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

`aubio` and NumPy are intentionally not required for Stage 1. The detector
uses the Python standard library, while `sounddevice` supplies microphone
capture.

## Run

```powershell
python app.py
```

Select an input microphone, adjust the expected pitch range if needed, and
press **Start**. The UI remains on the main Tkinter thread; capture and pitch
calculation run in a worker thread.

## Tests

```powershell
python -m pytest -q
```

The automated tests use synthetic sine waves and do not access a microphone.
Manual hardware verification is still required: play several individual
saxophone notes, pause for silence, and confirm that valid notes appear only
while the signal is reliable.

## Troubleshooting

- If no microphone appears, verify Windows microphone permissions and the
  selected input device, then restart the application.
- If `sounddevice` reports a PortAudio error, install the current device
  driver and check that the sample rate is supported.
- The Stage 1 autocorrelation detector is intended for one note at a time.
  Breath noise, strong harmonics, and room noise can reduce confidence.
