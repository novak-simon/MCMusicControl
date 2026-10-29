# Saxophone-Controlled Minecraft

## Stage 1-4: pitch detection, note-state tracking, keyboard control, and mappings

Stage 1 provides a Tkinter window that captures mono microphone audio in a
background thread and estimates the fundamental frequency using aubio's
optimized `yin` detector. If aubio cannot be imported, the standard-library
normalized-autocorrelation detector remains available as a fallback. It
displays the nearest equal-temperament note, octave, frequency, and a
confidence indicator. Silence and signals below the confidence threshold are
shown as `Silence / unreliable`.

The detector accepts a configurable expected frequency range. This is a
frequency calibration range, not a claim that written saxophone note names
have the same concert-pitch frequency. The sensitivity field controls the
minimum confidence accepted as a valid note; `0.15` is a responsive default
for saxophone attacks. Audio blocks are 1024 samples
(about 23 ms at 44.1 kHz), improving responsiveness for short notes.

Stage 2 adds `NoteStateTracker`, which turns frame estimates into `note_on`,
`continue`, `change`, `uncertain`, and `note_off` events. A first valid frame
starts a note quickly, a pitch change requires two consistent frames, and two
uncertain frames end a note. These thresholds are deliberately isolated and
configurable for keyboard-control tuning.

Stage 3 adds `KeyboardController`. Keyboard control is never enabled at
startup: click **Activate controls**, focus the Minecraft window, and then
start playing. The current example mappings include sustained W/S/A/D
movement and a trigger-mode Space jump. **Deactivate** and **EMERGENCY STOP**
release every held key. Sustained mappings use a short configurable release
delay, and multiple notes mapped to the same physical key are reference
counted. Sustained mouse buttons use the same release-delay safety mechanism.
The controller also releases keys when the foreground window is not
Minecraft and is independently tested with a mock keyboard.

Special mappings use names such as `space`, `escape`, `enter`, `tab`, `shift`,
`ctrl`, and `alt`; mouse buttons use `mouse_left`, `mouse_right`, or
`mouse_middle`; ordinary single-character keys use their character. Mouse
buttons are sent through `pynput.mouse`, not as keyboard arrow keys.

Stage 4 stores the editable mappings in [`config.json`](./config.json).
The application validates this file when controls are activated and reports
invalid JSON, notes, modes, keys, or timing values before sending input.
Trigger mappings hold their key for `trigger_hold_seconds` (60 ms by default)
and release it from the controller timer, giving Minecraft time to observe
actions such as jump, inventory, hotbar selection, and Escape. Sustained
movement and jump defaults are intentionally conservative; the disabled C4
entry reserves the future attack mapping without sending mouse input yet.

## Installation

Use Python 3.13 on Windows:

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

`aubio` is used for lower CPU use and quicker response. Its `yin` method is
used because the installed Windows build reports a zero confidence value for
`yinfft` even on clean tones. It currently builds successfully on Python
3.13.5 on Windows. The standard-library fallback does
not require NumPy. `sounddevice` supplies microphone capture and `pynput` supplies keyboard
simulation. The application does not send keyboard input until controls are
explicitly activated.

## Run

```powershell
python app.py
```

Select an input microphone, adjust the expected pitch range if needed, and
press **Start**. The UI remains on the main Tkinter thread; capture and pitch
calculation run in a worker thread.

Edit `config.json` while the application is stopped, then activate controls
again to load the changes. A mapping has a note key such as `A4`, a keyboard
key, a mode (`sustained` or `trigger`), and an `enabled` flag. Do not use
mouse names yet; mouse control is a later stage.

## Tests

```powershell
python -m pytest -q
```

The automated tests use synthetic signals and do not access a microphone.
Manual hardware verification is still required: play several individual
saxophone notes, including short articulated notes, pause for silence, and
confirm that valid notes appear only while the signal is reliable. The state
tracker tests verify that sustained notes do not repeat `note_on`, brief gaps
do not end a note, and pitch changes stabilize before being reported.

## Troubleshooting

- If no microphone appears, verify Windows microphone permissions and the
  selected input device, then restart the application.
- If `sounddevice` reports a PortAudio error, install the current device
  driver and check that the sample rate is supported.
- The detector is intended for one note at a time. Breath noise, strong
  harmonics, and room noise can reduce confidence.
- If aubio cannot be installed on another machine, remove it from the
  environment and the application will use the slower fallback detector.
