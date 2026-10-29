# Project Specification: Saxophone-Controlled Minecraft

## Objective

Build a standalone Windows application that lets me control Minecraft Java Edition by playing notes on a saxophone into a microphone.

The application must detect musical pitches in real time and translate them into keyboard and, eventually, mouse inputs. It must work alongside an ordinary Minecraft installation without requiring a Minecraft mod.

I use Windows and VS Code. I want a reliable, configurable tool that I can actually play Minecraft with, not just a proof of concept.

## 1. Development approach

Work incrementally. First inspect the project directory, explain the proposed architecture briefly, and then implement the application in small, testable stages.

Do not attempt to implement everything in one large step. At the end of each stage:
- Run the available automated tests.
- Fix any failures before proceeding.
- Update the README with what works and how to test it.
- Report the files changed, commands executed, and any remaining limitations.

Make sensible implementation decisions independently. Ask me questions only when a decision genuinely blocks progress.

## 2. Technology

Use Python on Windows.

Preferred components:
- `sounddevice` for microphone capture.
- `aubio` for real-time pitch and onset detection, if it can be installed and used reliably in the current Windows/Python environment.
- `pynput` or another suitable library for simulating keyboard input.
- `tkinter` for a lightweight desktop interface.
- JSON for user-editable configuration.
- `pytest` for automated tests.

Before committing to dependencies, check their compatibility with the installed Python version and Windows. If aubio is impractical to install, evaluate an alternative real-time pitch-detection implementation. Do not silently replace a real-time algorithm with a slow offline transcription system.

Keep audio analysis, note mapping, keyboard control, configuration, and the user interface in separate modules.

## 3. Stage 1: Live pitch detector

Build a minimal application that:
- Lists available microphone devices and lets me select one.
- Captures audio continuously.
- Detects the fundamental frequency of a monophonic saxophone signal.
- Displays the detected frequency, nearest musical note, octave, and confidence or signal-quality indicator.
- Clearly distinguishes silence or an unreliable pitch from a valid note.
- Updates responsively without freezing the user interface.
- Provides adjustable input gain or sensitivity where appropriate.

Use a reasonable audio sample rate and buffer size. Avoid unnecessarily high CPU usage.

Provide a calibration or configuration option for the expected pitch range. Do not assume that written saxophone notes and concert-pitch frequencies are identical.

**Acceptance criteria:** I can play several individual notes on my saxophone and see their detected pitches update in real time. Silence should not be interpreted as a valid note.

## 4. Stage 2: Reliable note-state tracking

Implement a layer that converts noisy frame-by-frame pitch estimates into stable note states.

It must distinguish:
- A new note starting.
- A note continuing.
- A note changing to another pitch.
- A note ending.
- Silence or an uncertain signal.

Use configurable thresholds, temporal smoothing, and hysteresis to prevent rapid switching between adjacent pitches.

Repeated notes of the same pitch must be distinguishable when there is a sufficiently clear articulation or interruption. Investigate onset detection to support this.

A long sustained note must remain one continuous note, not generate repeated note-on events.

Do not assume that a microphone can perfectly distinguish every articulated repetition. Document the limitations and provide a way to adjust sensitivity.

Create automated tests using synthetic audio signals where practical, including sustained tones, pitch changes, silence, noisy signals, and repeated notes.

## 5. Stage 3: Keyboard control

Implement a keyboard controller that translates stable note states into key presses and releases.

Two operating modes are required:

### Sustained mode

A detected note holds its assigned key for as long as that note remains active.

Example:
- Play A4: press and hold `W`.
- Continue playing A4: keep `W` held.
- Change to G4: release `W` and apply the mapping for G4.
- Stop playing: release the key after a configurable release delay.

The release delay should suppress brief detection gaps without making controls feel sluggish.

### Trigger mode

A newly detected note triggers one discrete action. A sustained note must not repeatedly trigger the action.

Example: a note can trigger a jump or open the inventory once. A new trigger should require a new note onset or another explicitly configured activation condition.

Support a mapping in which each musical note can have:
- An assigned keyboard key.
- A control mode: sustained or trigger.
- An enabled/disabled state.

Prevent conflicting mappings from producing undefined behavior. For example, if multiple notes map to the same key, track which notes are holding it and release the physical key only when none remain active.

### Safety requirements

- Provide a configurable emergency-stop hotkey.
- Release every simulated key when stopping the application, shutting down, or encountering an unrecoverable error.
- Release held keys when the Minecraft window loses focus.
- Never leave keys held after microphone failure or an audio-processing exception.
- Do not send inputs to other applications accidentally. Only send gameplay inputs while the intended Minecraft window is focused.
- Do not activate keyboard control automatically at startup; require explicit user activation.
- Make the controller independently testable without sending real inputs.

**Acceptance criteria:** A sustained note produces one key-down event followed by one key-up event, with no repeated presses while the note continues. All held keys are released reliably on stop and focus loss.

## 6. Stage 4: Minecraft control mappings

Provide an initial, editable mapping for Minecraft Java Edition.

Use these as example defaults, not hard-coded assumptions:

| Musical note | Action | Mode |
|---|---|---|
| A4 | W / forward | Sustained |
| G4 | S / backward | Sustained |
| F4 | A / left | Sustained |
| E4 | D / right | Sustained |
| D4 | Space / jump | Trigger |
| C4 | Left mouse button / attack | Sustained |
| B3 | Right mouse button / use | Trigger |
| C5–A5 | Hotbar slots 1–9 | Trigger |
| D5 | E / inventory | Trigger |
| E5 | Escape | Trigger |

These are illustrative mappings. Make the entire mapping configurable, and validate conflicts.

Do not assume these pitches are the most comfortable or reliable notes for my particular saxophone. The final mapping should be easy to change.

For hotbar selection, a key press should select the corresponding slot once. Holding a hotbar key is not necessary.

Support a push-to-talk-like gameplay enable/disable control or an equivalent explicit activation mechanism so that playing outside Minecraft does not cause unintended inputs.

## 7. Stage 5: Desktop interface

Build a simple, practical interface showing:

- Selected microphone and audio status.
- Current detected note and frequency.
- Signal confidence or quality.
- Current control mode.
- Current gameplay activation state.
- The last recognized note and its assigned action.
- All currently held keys.
- A list of note-to-action mappings.
- Controls for starting and stopping audio processing.
- A prominent emergency stop.
- Access to sensitivity, release delay, and mapping settings.

Include a diagnostic mode that recognizes notes and displays their intended actions without sending any keyboard or mouse inputs.

The application must remain responsive during continuous audio capture. Use a separate audio-processing thread or another suitable concurrency approach, and do not manipulate Tkinter widgets directly from an audio callback.

## 8. Stage 6: Configuration and usability

Store settings in a human-readable JSON file.

Persist:
- Microphone selection where possible.
- Note mappings.
- Control modes.
- Sensitivity and confidence thresholds.
- Note-on and note-off timing parameters.
- Release delay.
- Gameplay activation settings.
- Emergency-stop configuration.

Validate configuration at startup and provide useful error messages for invalid mappings or missing devices.

Include a way to restore default settings. Do not overwrite user settings unexpectedly.

## 9. Stage 7: Testing and refinement

Add tests for:
- Pitch-to-note conversion.
- Pitch confidence thresholds.
- Note onset and offset detection.
- Sustained notes.
- Repeated notes.
- Transitions between pitches.
- Simultaneously held keyboard keys.
- Key-down and key-up event ordering.
- Focus loss and emergency stop.
- Configuration loading and validation.
- Microphone disconnection and recovery.

Use a mock keyboard controller in automated tests. Automated tests must never send real inputs to my computer.

Provide a manual test procedure for trying the application with Minecraft open. Verify movement, jumping, attack, interaction, and hotbar selection individually before attempting normal gameplay.

## 10. Future extensions (do not implement yet)

Keep the architecture extensible enough to add these later:
- Inventory command sequences.
- Multi-note command combinations.
- A command mode with source slot, destination slot, quantity, confirmation, and cancellation.
- Mouse movement and camera control.
- A second-monitor mapping reference.
- An optional Fabric mod for in-game labels and feedback.
- User-selectable mapping profiles.

Do not implement these extensions before the basic controls work reliably.

## 11. Deliverables

The finished project should include:
- Complete Python source code.
- A `requirements.txt` or equivalent dependency specification.
- A README with installation, setup, microphone configuration, usage, troubleshooting, and testing instructions.
- A default configuration file.
- Automated tests.
- A clear command for launching the application.
- A documented procedure for building a standalone Windows executable later, if desired.

Do not claim a stage is complete unless its acceptance criteria have been tested.

## First task

Start by inspecting the existing workspace and Python environment. Determine the Python version and check whether the proposed audio and input dependencies are practical to install.

Then implement Stage 1 only. Get real-time saxophone pitch detection working before proceeding to keyboard control. If you cannot verify detection using my physical microphone, clearly distinguish automated tests from tests that still require me to perform manually.
