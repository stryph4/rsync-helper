"""Simple logging helper for the GUI.

This module centralizes logging so the rest of the code can write
timestamped messages without depending on a specific widget. Call
`init(widget)` early with a `tk.Text` or `ScrolledText` widget to have
messages appended to the UI. If no widget is initialized, logs are
written to stdout.
"""

from datetime import datetime
import tkinter as tk

# Internal widget where log lines are written. If None, fallback to stdout.
_widget: tk.Text | None = None


def init(widget: tk.Text) -> None:
    """Configure the logger to write to the provided text widget."""
    global _widget
    _widget = widget


def timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def log(message: str) -> None:
    """Append a timestamped message to the configured widget or stdout.

    The log widget is temporarily switched to normal state to allow
    inserting text and then returned to disabled to prevent user edits.
    """
    global _widget
    line = f"[{timestamp()}] {message}\n"
    if _widget is None:
        # Useful during early startup or when running without a GUI.
        print(line, end="")
        return
    _widget.configure(state="normal")
    _widget.insert(tk.END, line)
    _widget.see(tk.END)
    _widget.configure(state="disabled")
