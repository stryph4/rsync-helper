"""Core utility functions for rsync_helper.

This module exposes small helpers used by the UI code:
- `choose_folder()` — open a folder chooser (GNOME chooser when available,
  otherwise tkinter's `askdirectory`). The GNOME chooser is started at
  the special URI `computer:///` so removable devices and "Other Locations"
  are visible.
- `save_text_to_file()` — show a save dialog and write text to the chosen file.

The module tries to use PyGObject (GTK) if installed; otherwise it falls
back to tkinter dialogs so the application remains functional on systems
without GTK bindings.
"""

import os
from typing import Optional
from tkinter import filedialog
import traceback
import shutil
import subprocess

from . import logger

# By default we DO NOT load GTK/PyGObject at module import time. Loading
# the GTK libraries can trigger native symbol lookup errors on systems
# where incompatible C libraries (for example, snap's core20) are present.
#
# To enable the GNOME chooser explicitly set the environment variable
# `RSYNC_HELPER_USE_GTK=1` before running the program. When enabled we
# attempt a lazy import inside the chooser functions and fall back to
# tkinter if anything goes wrong.
USE_GTK = os.environ.get("RSYNC_HELPER_USE_GTK") == "1"
Gtk = None
Gio = None
LAST_GTK_ERROR: str | None = None


DEFAULT_DIR = os.path.expanduser("~")
DEFAULT_DIR = os.path.expanduser("~")


def choose_folder(title: str = "Select folder") -> Optional[str]:
    """Show a folder chooser and return the selected path or URI.

    Behavior:
    - If GTK is available, open a `Gtk.FileChooserDialog` and set the
      current folder URI to `computer:///` so GNOME Files shows devices and
      network locations.
    - If GTK is not available or the GTK dialog fails, fall back to
      `tkinter.filedialog.askdirectory()`.

    Returns a filesystem path or a GVFS URI (string), or `None` if the
    user cancelled.

    Only attempt GTK if the user explicitly opted in via env var. We do a
    lazy import here so the application can start safely on systems where
    GTK/PyGObject would otherwise cause a native crash when loaded.
    """

    if USE_GTK:
        # Prefer an external GTK-native dialog (zenity) to avoid loading
        # PyGObject into this process and mixing GTK/Tk main loops which
        # can cause the UI to freeze on some systems. Zenity runs as a
        # separate process and returns the chosen path on stdout.
        try:
            if shutil.which("zenity"):
                proc = subprocess.run([
                    "zenity", "--file-selection", "--directory", "--title", title
                ], check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
                out = proc.stdout.strip()
                if out:
                    return out
                return None
        except Exception:
            # If zenity invocation fails, fall back to in-process GTK below
            pass

        try:
            import gi  # type: ignore
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk as _Gtk, Gio as _Gio  # type: ignore
            # assign to module-level names for potential reuse
            global Gtk, Gio
            Gtk, Gio = _Gtk, _Gio

            dialog = Gtk.FileChooserDialog(title=title, action=Gtk.FileChooserAction.SELECT_FOLDER)
            # Make dialog modal so responses are delivered reliably
            try:
                dialog.set_modal(True)
            except Exception:
                pass
            # Explicitly add labeled buttons paired with response IDs
            try:
                dialog.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Open", Gtk.ResponseType.OK)
            except Exception:
                # Fallback to legacy stock constants if add_buttons isn't available
                try:
                    dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_OPEN, Gtk.ResponseType.OK)
                except Exception:
                    pass

            # Start at computer:/// to show "Other Locations" and devices
            dialog.set_current_folder_uri("computer:///")

            try:
                resp = dialog.run()
                if resp == Gtk.ResponseType.OK:
                    uri = dialog.get_uri()
                    # Try to obtain a local path for the URI; if not possible,
                    # return the original URI (useful for GVFS-mounted resources).
                    try:
                        path = Gio.File.new_for_uri(uri).get_path()
                    except Exception:
                        path = uri
                    dialog.destroy()
                    return path
                dialog.destroy()
                return None
            finally:
                try:
                    dialog.destroy()
                except Exception:
                    pass
        except Exception:
            # If GTK import or dialog creation fails, log the traceback
            # so the user can diagnose why the native chooser failed.
            tb = traceback.format_exc()
            try:
                logger.log("GTK chooser failed, falling back to tkinter:\n" + tb)
            except Exception:
                # If logging fails for any reason, ignore and fallback.
                pass
            # expose the traceback for UI code to show a helpful prompt
            global LAST_GTK_ERROR
            LAST_GTK_ERROR = tb
            # Fall back to tkinter below
            pass

    # Clear any previous GTK error when falling back successfully
    LAST_GTK_ERROR = None

    # Fallback: standard tkinter folder chooser
    folder = filedialog.askdirectory(initialdir=DEFAULT_DIR, title=title)
    return folder or None

    # Open a save dialog and write `text` to the selected file.

    # Uses GTK save dialog when available; otherwise uses tkinter's
    # `asksaveasfilename`. Returns the filename written, or `None` if the
    # user cancelled.
    # 
def save_text_to_file(text: str, title: str = "Save file") -> Optional[str]:

    if USE_GTK:
        try:
            import gi # type: ignore
            gi.require_version("Gtk", "3.0")
            from gi.repository import Gtk as _Gtk  # type: ignore
            global Gtk
            Gtk = _Gtk

            dialog = Gtk.FileChooserDialog(title=title, action=Gtk.FileChooserAction.SAVE)
            try:
                dialog.set_modal(True)
            except Exception:
                pass
            try:
                dialog.add_buttons("Cancel", Gtk.ResponseType.CANCEL, "Save", Gtk.ResponseType.OK)
            except Exception:
                try:
                    dialog.add_buttons(Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL, Gtk.STOCK_SAVE, Gtk.ResponseType.OK)
                except Exception:
                    pass

            dialog.set_do_overwrite_confirmation(True)
            dialog.set_current_name("rsync_helper.log")
            dialog.set_current_folder_uri(f"file://{DEFAULT_DIR}")

            try:
                resp = dialog.run()
                if resp == Gtk.ResponseType.OK:
                    filename = dialog.get_filename()
                    try:
                        with open(filename, "w", encoding="utf-8") as f:
                            f.write(text)
                    except Exception:
                        raise
                    return filename
                return None
            finally:
                try:
                    dialog.destroy()
                except Exception:
                    pass
        except Exception:
            # Fall back to tkinter below
            pass

    filename = filedialog.asksaveasfilename(
        defaultextension=".log",
        filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
        initialdir=DEFAULT_DIR,
        title=title,
    )
    if not filename:
        return None
    with open(filename, "w", encoding="utf-8") as f:
        f.write(text)
    return filename
