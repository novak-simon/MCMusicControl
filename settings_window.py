"""Settings window — edit sensitivities and note-to-key mappings live."""

from __future__ import annotations

from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk
from typing import Callable

from configuration import AppConfig, load_config, save_config
from keyboard_controller import ControlMode, NoteMapping

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_NOTE_NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
_OCTAVES = [str(o) for o in range(0, 10)]
_MODES = ["sustained", "trigger"]

# Suggested key values shown in the combo-box drop-down.
_KEY_SUGGESTIONS = [
    # Letters
    *list("abcdefghijklmnopqrstuvwxyz"),
    # Digits
    *[str(d) for d in range(10)],
    # Special keyboard keys
    "space", "shift", "ctrl", "alt", "enter", "esc", "tab",
    "backspace", "delete",
    "up", "down", "left", "right",
    "home", "end", "page_up", "page_down",
    # Mouse buttons
    "mouse_left", "mouse_right", "mouse_middle",
    # Raw (SendInput) mouse movement — works in Minecraft in-game view
    "mouse_raw_up", "mouse_raw_down", "mouse_raw_left", "mouse_raw_right",
]


# ---------------------------------------------------------------------------
# Row data class
# ---------------------------------------------------------------------------

class _MappingRow:
    """Holds the live Tkinter variables for one mapping table row."""

    def __init__(
        self,
        parent: tk.Frame,
        row_index: int,
        note_text: str,
        key: str,
        mode: str,
        enabled: bool,
        on_delete: Callable[[_MappingRow], None],
    ) -> None:
        self.note_text = note_text

        self.key_var = tk.StringVar(value=key)
        self.mode_var = tk.StringVar(value=mode)
        self.enabled_var = tk.BooleanVar(value=enabled)

        # Note label
        self._note_lbl = ttk.Label(parent, text=note_text, width=5, anchor="center")
        self._note_lbl.grid(row=row_index, column=0, padx=(4, 2), pady=2)

        # Key combo-box (editable — user may type anything)
        self._key_cb = ttk.Combobox(
            parent, textvariable=self.key_var,
            values=_KEY_SUGGESTIONS, width=20,
        )
        self._key_cb.grid(row=row_index, column=1, padx=2, pady=2)

        # Mode combo-box
        self._mode_cb = ttk.Combobox(
            parent, textvariable=self.mode_var,
            values=_MODES, state="readonly", width=10,
        )
        self._mode_cb.grid(row=row_index, column=2, padx=2, pady=2)

        # Enabled checkbox
        self._enabled_cb = ttk.Checkbutton(parent, variable=self.enabled_var)
        self._enabled_cb.grid(row=row_index, column=3, padx=4, pady=2)

        # Delete button
        self._del_btn = ttk.Button(
            parent, text="✕", width=3,
            command=lambda: on_delete(self),
        )
        self._del_btn.grid(row=row_index, column=4, padx=(2, 4), pady=2)

    def destroy(self) -> None:
        for widget in (
            self._note_lbl, self._key_cb, self._mode_cb,
            self._enabled_cb, self._del_btn,
        ):
            widget.destroy()

    def as_mapping(self) -> tuple[tuple[str, int], NoteMapping] | str:
        """Return ``((name, octave), NoteMapping)`` or an error string."""
        key = self.key_var.get().strip().lower()
        if not key:
            return f"Note {self.note_text}: key must not be empty."
        try:
            mode = ControlMode(self.mode_var.get())
        except ValueError:
            return f"Note {self.note_text}: invalid mode '{self.mode_var.get()}'."
        note_name = self.note_text[:-1]
        try:
            octave = int(self.note_text[-1])
        except ValueError:
            return f"Cannot parse note '{self.note_text}'."
        return (note_name, octave), NoteMapping(key, mode, self.enabled_var.get())


# ---------------------------------------------------------------------------
# Settings window
# ---------------------------------------------------------------------------

class SettingsWindow:
    """Modal-like Toplevel for editing sensitivities and key mappings.

    Call ``open()`` to show it; it is a singleton (only one at a time).
    ``on_save`` is called after a successful save so the caller can reload
    the controller immediately.
    """

    _instance: SettingsWindow | None = None

    def __init__(
        self,
        parent: tk.Tk,
        config_path: Path,
        on_save: Callable[[], None],
    ) -> None:
        self._parent = parent
        self._config_path = config_path
        self._on_save = on_save
        self._rows: list[_MappingRow] = []
        self._win: tk.Toplevel | None = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def open(self) -> None:
        """Open (or bring to front) the settings window."""
        if self._win is not None and self._win.winfo_exists():
            self._win.lift()
            self._win.focus_force()
            return
        try:
            config = load_config(self._config_path)
        except ValueError as err:
            messagebox.showerror("Cannot open settings", str(err), parent=self._parent)
            return
        self._build(config)

    # ------------------------------------------------------------------
    # Window construction
    # ------------------------------------------------------------------

    def _build(self, config: AppConfig) -> None:
        win = tk.Toplevel(self._parent)
        win.title("Settings — key mappings & sensitivity")
        win.resizable(True, True)
        win.protocol("WM_DELETE_WINDOW", self._on_close)
        self._win = win

        outer = ttk.Frame(win, padding=12)
        outer.grid(sticky="nsew")
        win.columnconfigure(0, weight=1)
        win.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)  # mapping table gets all extra height

        # ---- Sensitivities section ----------------------------------------
        sens_frame = ttk.LabelFrame(outer, text="Mouse sensitivity", padding=8)
        sens_frame.grid(row=0, column=0, sticky="ew", pady=(0, 12))

        ttk.Label(sens_frame, text="Raw:").grid(
            row=0, column=0, sticky="w", padx=(0, 6)
        )
        self._sens_raw_var = tk.StringVar(value=str(config.mouse_sensitivity_raw))
        ttk.Entry(sens_frame, textvariable=self._sens_raw_var, width=8).grid(
            row=0, column=1, sticky="w"
        )

        # ---- Mapping table -----------------------------------------------
        map_frame = ttk.LabelFrame(outer, text="Note → key mappings", padding=8)
        map_frame.grid(row=1, column=0, sticky="nsew")
        map_frame.columnconfigure(0, weight=1)
        map_frame.rowconfigure(1, weight=1)

        # Column headers
        hdr = ttk.Frame(map_frame)
        hdr.grid(row=0, column=0, sticky="ew")
        for col, (text, w) in enumerate([
            ("Note", 5), ("Key", 20), ("Mode", 10), ("On", 3), ("", 3)
        ]):
            ttk.Label(hdr, text=text, width=w, anchor="center",
                      font=("Segoe UI", 9, "bold")).grid(
                row=0, column=col, padx=(4 if col == 0 else 2, 2)
            )

        # Scrollable area
        canvas_frame = ttk.Frame(map_frame)
        canvas_frame.grid(row=1, column=0, sticky="nsew")
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)

        canvas = tk.Canvas(canvas_frame, borderwidth=0, highlightthickness=0)
        scrollbar = ttk.Scrollbar(canvas_frame, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")

        self._rows_frame = ttk.Frame(canvas)
        canvas_window = canvas.create_window((0, 0), window=self._rows_frame, anchor="nw")

        def _on_frame_configure(event: tk.Event) -> None:
            canvas.configure(scrollregion=canvas.bbox("all"))

        def _on_canvas_configure(event: tk.Event) -> None:
            canvas.itemconfig(canvas_window, width=event.width)

        self._rows_frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", _on_canvas_configure)

        # Mouse-wheel scrolling
        def _on_mousewheel(event: tk.Event) -> None:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        win.bind("<Destroy>", lambda e: canvas.unbind_all("<MouseWheel>"))

        self._canvas = canvas
        self._rows = []

        # Populate rows from config (sorted by note order)
        _note_order = {n: i for i, n in enumerate(_NOTE_NAMES)}

        def _sort_key(item: tuple[tuple[str, int], NoteMapping]) -> tuple[int, int]:
            (name, octave), _ = item
            return (octave, _note_order.get(name, 99))

        for (name, octave), mapping in sorted(config.mappings.items(), key=_sort_key):
            self._add_row(f"{name}{octave}", mapping.key, mapping.mode.value, mapping.enabled)

        canvas.configure(height=min(400, max(200, len(self._rows) * 30 + 10)))

        # ---- Add new mapping row -----------------------------------------
        add_frame = ttk.LabelFrame(outer, text="Add mapping", padding=8)
        add_frame.grid(row=2, column=0, sticky="ew", pady=(12, 0))

        ttk.Label(add_frame, text="Note:").grid(row=0, column=0, padx=(0, 4))
        self._new_note_var = tk.StringVar(value="C")
        ttk.Combobox(
            add_frame, textvariable=self._new_note_var,
            values=_NOTE_NAMES, state="readonly", width=5,
        ).grid(row=0, column=1, padx=(0, 2))

        self._new_octave_var = tk.StringVar(value="4")
        ttk.Combobox(
            add_frame, textvariable=self._new_octave_var,
            values=_OCTAVES, state="readonly", width=3,
        ).grid(row=0, column=2, padx=(0, 8))

        ttk.Label(add_frame, text="Key:").grid(row=0, column=3, padx=(0, 4))
        self._new_key_var = tk.StringVar()
        ttk.Combobox(
            add_frame, textvariable=self._new_key_var,
            values=_KEY_SUGGESTIONS, width=18,
        ).grid(row=0, column=4, padx=(0, 8))

        ttk.Label(add_frame, text="Mode:").grid(row=0, column=5, padx=(0, 4))
        self._new_mode_var = tk.StringVar(value="sustained")
        ttk.Combobox(
            add_frame, textvariable=self._new_mode_var,
            values=_MODES, state="readonly", width=10,
        ).grid(row=0, column=6, padx=(0, 8))

        ttk.Button(add_frame, text="Add", command=self._add_mapping).grid(
            row=0, column=7
        )

        # ---- Save / Cancel buttons ----------------------------------------
        btn_frame = ttk.Frame(outer)
        btn_frame.grid(row=3, column=0, sticky="e", pady=(12, 0))
        ttk.Button(btn_frame, text="Save & Apply", command=self._save).grid(
            row=0, column=0, padx=(0, 8)
        )
        ttk.Button(btn_frame, text="Cancel", command=self._on_close).grid(
            row=0, column=1
        )

        # Set a comfortable initial size and center it
        win.update_idletasks()
        win.minsize(600, 350)

    # ------------------------------------------------------------------
    # Row management
    # ------------------------------------------------------------------

    def _add_row(
        self,
        note_text: str,
        key: str,
        mode: str,
        enabled: bool,
    ) -> None:
        row_index = len(self._rows)
        row = _MappingRow(
            self._rows_frame,
            row_index,
            note_text,
            key,
            mode,
            enabled,
            on_delete=self._delete_row,
        )
        self._rows.append(row)

    def _delete_row(self, row: _MappingRow) -> None:
        row.destroy()
        self._rows.remove(row)
        # Re-grid remaining rows so there are no gaps
        for i, r in enumerate(self._rows):
            for widget in (
                r._note_lbl, r._key_cb, r._mode_cb,
                r._enabled_cb, r._del_btn,
            ):
                info = widget.grid_info()
                widget.grid(row=i, column=int(info["column"]))

    def _add_mapping(self) -> None:
        note_text = self._new_note_var.get() + self._new_octave_var.get()
        # Check for duplicate
        existing = {r.note_text for r in self._rows}
        if note_text in existing:
            messagebox.showwarning(
                "Duplicate mapping",
                f"{note_text} is already in the table. "
                "Edit or delete the existing row instead.",
                parent=self._win,
            )
            return
        key = self._new_key_var.get().strip()
        if not key:
            messagebox.showwarning("Missing key", "Please enter a key name.", parent=self._win)
            return
        self._add_row(note_text, key, self._new_mode_var.get(), True)
        # Scroll to bottom so the new row is visible
        self._canvas.after(50, lambda: self._canvas.yview_moveto(1.0))

    # ------------------------------------------------------------------
    # Save
    # ------------------------------------------------------------------

    def _save(self) -> None:
        # Validate sensitivity
        try:
            sens_raw = float(self._sens_raw_var.get())
            if sens_raw <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror(
                "Invalid sensitivity",
                "Raw mouse sensitivity must be a positive number.",
                parent=self._win,
            )
            return

        # Validate mappings
        mappings: dict[tuple[str, int], NoteMapping] = {}
        for row in self._rows:
            result = row.as_mapping()
            if isinstance(result, str):
                messagebox.showerror("Invalid mapping", result, parent=self._win)
                return
            note_key, note_mapping = result
            if note_key in mappings:
                name, octave = note_key
                messagebox.showerror(
                    "Duplicate mapping",
                    f"{name}{octave} appears more than once.",
                    parent=self._win,
                )
                return
            mappings[note_key] = note_mapping

        # Load current config just to read the timing fields we don't expose here
        try:
            current = load_config(self._config_path)
        except ValueError as err:
            messagebox.showerror("Cannot read config", str(err), parent=self._win)
            return

        new_config = AppConfig(
            mappings=mappings,
            release_delay_seconds=current.release_delay_seconds,
            trigger_hold_seconds=current.trigger_hold_seconds,
            mouse_sensitivity=current.mouse_sensitivity,
            mouse_sensitivity_raw=sens_raw,
        )

        try:
            save_config(self._config_path, new_config)
        except OSError as err:
            messagebox.showerror("Save failed", str(err), parent=self._win)
            return

        self._on_save()
        messagebox.showinfo(
            "Saved",
            "Settings saved and applied successfully.",
            parent=self._win,
        )

    # ------------------------------------------------------------------
    # Close
    # ------------------------------------------------------------------

    def _on_close(self) -> None:
        if self._win is not None:
            self._win.destroy()
            self._win = None
        self._rows = []

