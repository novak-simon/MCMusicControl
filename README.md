# 🎷 MCMusicControl — Saxophone Minecraft Controller

> [!WARNING]
> **Active Development / Experimental**
> This project is currently in active development. Features, defaults, and interfaces are continually being improved. Feedback and bug reports are welcome!

MCMusicControl is a standalone Windows application that allows you to play and control **Minecraft (Java Edition)** using an acoustic musical instrument (designed and tuned for an **Alto Saxophone in E♭**) via your microphone.

It detects notes in real time, filters out background noise, and translates musical pitches into keyboard inputs, mouse clicks, and camera POV look actions without needing any Minecraft mods.

---

## Features

- **Real-Time Pitch Detection**: Uses `aubio`'s low-latency `yin` pitch estimator with a built-in autocorrelation fallback.
- **Saxophone Transposition**: Frequencies are automatically matched to the written notes of an Alto Saxophone in E♭ (e.g., concert D♯/E♭ displays as written C).
- **In-Game Camera Look**: Uses Win32 low-level relative input injection (`mouse_raw_*`) so that moving your player's point of view works directly in Minecraft.
- **Interactive In-App Settings**: Change note-to-key mappings and mouse sensitivity on the fly with live saving to `config.json`.
- **Dual Control Modes**:
  - `sustained`: Holds down a key or continues moving the camera as long as you sustain the note (e.g., walking forward with W, looking around).
  - `trigger`: Presses a key once for a brief moment (e.g., jump with Space, open inventory with E, switch hotbar slots).
- **Safety First**:
  - **Focus Guard**: Automatically suppresses and releases all inputs if Minecraft is not the active window.
  - **Emergency Stop**: One-click button and window safety to release all held keys immediately.

---

## Requirements

- **Operating System**: Windows 10 or 11
- **Python**: Python 3.11 or newer (Python 3.13 recommended)
- **Hardware**: Working microphone and your instrument

---

## Installation

1. **Clone or download** this repository to your local machine.

2. **Open a terminal** (PowerShell) in the project directory:

   ```powershell
   cd path\to\MCMusicControl
   ```

3. **Create and activate a virtual environment**:

   ```powershell
   py -3.11 -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```
   *(Replace `-3.11` with your installed Python version, e.g., `-3.13`)*

4. **Install required dependencies**:

   ```powershell
   python -m pip install --upgrade pip
   python -m pip install -r requirements.txt
   ```

---

## How to Use

### 1. Launch the Application

Make sure your virtual environment is activated, then run:

```powershell
python app.py
```

### 2. Configure Your Microphone & Calibrate Audio

1. **Select Microphone**: Choose your input device from the drop-down menu at the top.
2. **Click "Start audio"**: The application begins analyzing microphone input.
3. **Play some test notes**:
   - Check the **Note**, **Frequency**, and **Confidence** indicators in the UI.
   - Silence or background room noise will show as `Silence / unreliable`.
4. **Tune Detection Parameters (optional)**:
   - **Expected pitch range (Hz)**: Defaults to `100` Hz – `1200` Hz (covers the standard saxophone playing range).
   - **Sensitivity (min confidence)**: Defaults to `0.90`. If your notes aren't registering reliably, you can lower this slightly (e.g., to `0.80`). If background noise causes accidental triggers, raise it.

### 3. Customize Note Mappings & Sensitivity

Click the **Settings…** button at the bottom of the window to open the configuration panel:

- **Mouse Sensitivity**: Set the sensitivity for in-game camera look (`mouse_raw_*`).
- **Key Mappings Table**:
  - View each mapped note, its assigned key, its mode (`sustained` or `trigger`), and whether it's enabled.
  - Edit keys and modes directly using the dropdowns or typing.
  - Remove unwanted notes with the **✕** button.
- **Add Mapping**: Pick a note name (e.g. `G#`), octave (`4`), choose an action key, and select the mode (`sustained` or `trigger`), then click **Add**.
- **Save & Apply**: Writes your changes straight to `config.json` and immediately applies them to the live controller.

#### Supported Keys & Actions

- **Movement / Letters**: `w`, `a`, `s`, `d`, or any single letter/number
- **Special Keys**: `space`, `escape`, `enter`, `tab`, `shift`, `ctrl`, `alt`, `backspace`, `delete`, arrow keys
- **Mouse Clicks**: `mouse_left` (attack/mine), `mouse_right` (use/place), `mouse_middle`
- **Camera Look (Raw)**: `mouse_raw_up`, `mouse_raw_down`, `mouse_raw_left`, `mouse_raw_right`

### 4. Activate Controls & Play Minecraft

1. Launch Minecraft and load into your world.
2. In MCMusicControl, click **Activate controls**.
3. Click into your Minecraft window to focus it.
4. Play your instrument to control the game!

> [!TIP]
> **Safety Protection**:
> - If you Alt-Tab away or open another window, MCMusicControl automatically releases all held keys.
> - Click **Deactivate** or **EMERGENCY STOP** at any time to immediately halt all game inputs.

---

## Default Note Scheme

The out-of-the-box layout provided in `config.json` uses the following mappings (written notes):

| Written Note | Mode | Action | In-Game Function |
|---|---|---|---|
| **E3** | `sustained` | `mouse_raw_down` | Look Down |
| **F3** | `sustained` | `mouse_raw_up` | Look Up |
| **G3** | `sustained` | `mouse_raw_right` | Look Right |
| **A3** | `sustained` | `mouse_raw_left` | Look Left |
| **B3** | `trigger` | `mouse_right` | Use / Place Block |
| **C4** | `sustained` | `mouse_left` | Attack / Mine |
| **D4** | `sustained` | `space` | Jump |
| **E4** | `sustained` | `d` | Strafe Right |
| **F4** | `sustained` | `a` | Strafe Left |
| **G4** | `sustained` | `s` | Walk Backward |
| **A4** | `sustained` | `w` | Walk Forward |
| **C5** | `trigger` | `1` | Hotbar Slot 1 |
| **C#5** | `trigger` | `2` | Hotbar Slot 2 |
| **D5** | `trigger` | `e` | Inventory |
| **D#5** | `trigger` | `4` | Hotbar Slot 4 |
| **E5** | `trigger` | `escape` | Pause / Menu |
| **F5 – G#5** | `trigger` | `6` – `9` | Hotbar Slots 6–9 |

You can customize all of these at any time via the **Settings…** dialog.

---

## Running Automated Tests

To run the automated test suite:

```powershell
py -m pytest tests/ -v
```

All 31 unit and integration tests run against synthetic audio signals without requiring physical microphone access.

---

## Troubleshooting

- **No microphone detected**: Ensure microphone permissions are granted in Windows Settings (*Privacy & Security > Microphone*) and reconnect your audio device before launching the app.
- **Camera does not turn in Minecraft**: Make sure camera movements are mapped to `mouse_raw_*` keys (e.g. `mouse_raw_left`) rather than legacy pointer keys.
- **Notes triggering accidentally**: Increase the **Sensitivity (min confidence)** threshold in the main window (e.g. `0.90` or higher). Ensure your microphone input volume is set to a moderate level to avoid clipping.
- **Keys remain held down**: Click **EMERGENCY STOP** or switch windows to immediately clear all active key states.
