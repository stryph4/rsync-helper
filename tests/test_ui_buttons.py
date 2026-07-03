import tkinter as tk
from tkinter.scrolledtext import ScrolledText

import pytest

from rsync_helper import ui, core


# Categorization markers: these tests exercise the UI and require GTK.
@pytest.mark.ui
@pytest.mark.integration
def _module_marker():
    # noop helper to attach module-level marks while still keeping the
    # existing skipif behavior intact for GTK availability.
    pass


def _is_gtk_available() -> bool:
    """Return True if PyGObject/GTK is importable on this system.

    Tests are only meaningful when the GTK file chooser is available.
    """
    try:
        import gi

        gi.require_version("Gtk", "3.0")
        from gi.repository import Gtk  # type: ignore # noqa: F401

        return True
    except Exception:
        return False


pytestmark = pytest.mark.skipif(not _is_gtk_available(), reason="GTK not available")


def _collect_widgets(root, cls):
    out = []

    def _rec(w):
        for child in w.winfo_children():
            if isinstance(child, cls):
                out.append(child)
            _rec(child)

    _rec(root)
    return out


def _collect_buttons(root, text=None):
    from tkinter import Button

    out = []

    def _rec(w):
        for child in w.winfo_children():
            if isinstance(child, Button) and (text is None or child.cget("text") == text):
                out.append(child)
            _rec(child)

    _rec(root)
    return out


@pytest.mark.gtk
def test_browse_buttons_update_entries(monkeypatch):
    # Prevent dialogs from actually appearing by stubbing chooser
    # Prevent the GTK-not-enabled prompt from opening the install dialog
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *a, **k: False)
    # First call returns source path
    monkeypatch.setattr(core, "choose_folder", lambda title=None: "/tmp/src")
    win = ui.build_ui()
    try:
        entries = _collect_widgets(win, tk.Entry)
        assert len(entries) >= 2

        browse_buttons = _collect_buttons(win, "Browse")
        assert len(browse_buttons) >= 2

        # Click first Browse -> should populate first entrypytho
        browse_buttons[0].invoke()
        assert entries[0].get() == "/tmp/src"

        # Next call returns destination path
        monkeypatch.setattr(core, "choose_folder", lambda title=None: "/tmp/dest")
        browse_buttons[1].invoke()
        assert entries[1].get() == "/tmp/dest"
    finally:
        win.destroy()


@pytest.mark.gtk
def test_browse_cancel_then_browse(monkeypatch):
    # Prevent the GTK-not-enabled prompt from opening the install dialog
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *a, **k: False)

    # First call simulates user cancelling (None), second call returns a path
    calls = {"n": 0}

    def chooser(title=None):
        calls["n"] += 1
        if calls["n"] == 1:
            return None
        return "/tmp/src"

    monkeypatch.setattr(core, "choose_folder", chooser)

    win = ui.build_ui()
    try:
        entries = _collect_widgets(win, tk.Entry)
        assert len(entries) >= 1

        browse_buttons = _collect_buttons(win, "Browse")
        assert browse_buttons, "No Browse buttons found"

        # First click -> simulate cancel, entry should remain empty
        browse_buttons[0].invoke()
        assert entries[0].get() == ""

        # Second click -> returns path and should populate entry
        browse_buttons[0].invoke()
        assert entries[0].get() == "/tmp/src"
    finally:
        win.destroy()


@pytest.mark.gtk
def test_save_log_calls_core_and_logs(monkeypatch):
    # Prevent the GTK-not-enabled prompt from opening the install dialog
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *a, **k: False)

    saved = {}

    def fake_save(text, title=None):
        # record that we received text and return a filename
        saved["text"] = text
        return "/tmp/rsync_helper_test.log"

    monkeypatch.setattr(core, "save_text_to_file", fake_save)

    win = ui.build_ui()
    try:
        save_buttons = _collect_buttons(win)
        # find the Save Log... button by its full text
        save_btn = None
        for b in save_buttons:
            if b.cget("text").startswith("Save"):
                save_btn = b
                break
        assert save_btn is not None

        # Invoke save and assert the logger appended the saved message
        save_btn.invoke()

        st = _collect_widgets(win, ScrolledText)
        assert st, "No ScrolledText found for log"
        content = st[0].get("1.0", tk.END)
        assert "Saved log to: /tmp/rsync_helper_test.log" in content
        assert "Application started" in content
    finally:
        win.destroy()
