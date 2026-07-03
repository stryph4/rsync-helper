"""User interface module for rsync_helper.

This module constructs the Tkinter-based GUI and wires the UI controls
to the core utilities and logger. It intentionally keeps UI-only code
separate from the core dialog logic so the core functions can be
unit-tested or reused independently.
"""

import tkinter as tk
from tkinter.scrolledtext import ScrolledText
from tkinter import messagebox

from . import core
from . import logger
import os
import shutil
import subprocess
import shlex
import threading
import time
from tkinter import ttk
import traceback
import re


# A lightweight "rounded" button wrapper. True rounded corners require
# custom images or platform-specific theming; this class keeps the widget
# as a `tk.Button` (so tests that check isinstance(..., Button) still work)
# and applies flat styling with hover/active color changes to give a
# sleeker, softer appearance.
class RoundedButton(tk.Button):
    def __init__(self, master=None, **kw):
        self._normal_bg = kw.pop("bg", "#072f6b")
        self._active_bg = kw.pop("activebackground", "#0b69ff")
        fg = kw.pop("fg", "#ffffff")
        kw.setdefault("relief", "flat")
        kw.setdefault("bd", 0)
        kw.setdefault("highlightthickness", 0)
        kw.setdefault("padx", 10)
        kw.setdefault("pady", 6)
        kw.setdefault("fg", fg)
        kw.setdefault("bg", self._normal_bg)
        super().__init__(master, **kw)
        self.bind("<Enter>", self._on_enter)
        self.bind("<Leave>", self._on_leave)

    def _on_enter(self, _ev=None):
        try:
            self.configure(bg=self._active_bg)
        except Exception:
            pass

    def _on_leave(self, _ev=None):
        try:
            self.configure(bg=self._normal_bg)
        except Exception:
            pass


def show_gtk_install_instructions_dialog(window: tk.Tk | tk.Toplevel):
    """Show the GNOME file chooser install instructions dialog attached to `window`.

    This is extracted so tests or the CLI can open the dialog directly.
    """
    cmds = "sudo apt update\nsudo apt install python3-gi gir1.2-gtk-3.0"
    top = tk.Toplevel(window)
    top.title("Enable GNOME file chooser (optional)")
    top.geometry("520x160")
    top.resizable(False, False)

    label = tk.Label(top, text="The GNOME file chooser (recommended) is not available on this system.")
    label.pack(anchor="w", padx=12, pady=(12, 4))

    sub = tk.Label(top, text="Install these packages to enable the native GNOME file chooser:")
    sub.pack(anchor="w", padx=12)

    text = tk.Text(top, height=4, width=60)
    text.insert("1.0", cmds)
    text.configure(state="disabled")
    text.pack(padx=12, pady=8)

    def copy_commands():
        window.clipboard_clear()
        window.clipboard_append(cmds)
        logger.log("Copied GTK install commands to clipboard")
        messagebox.showinfo("Copied", "Install commands copied to clipboard")

    def install_commands():
        # Ask for confirmation before attempting an install
        if not messagebox.askyesno(
            "Install packages",
            "Attempt to install the required GTK packages now? This may require your password.",
        ):
            return

        # Prefer pkexec, then sudo. If neither is available, instruct the user.
        if shutil.which("pkexec"):
            cmd = ["pkexec", "bash", "-c", "apt update && apt install -y python3-gi gir1.2-gtk-3.0"]
        elif shutil.which("sudo"):
            cmd = ["sudo", "bash", "-c", "apt update && apt install -y python3-gi gir1.2-gtk-3.0"]
        else:
            logger.log("No privilege escalation tool found for automatic install")
            messagebox.showinfo(
                "Manual install required",
                f"Could not find sudo or pkexec. Please run:\n\n{cmds}",
            )
            return

        try:
            logger.log("Starting GTK package installer (may prompt for password)")
            proc = subprocess.run(cmd, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            logger.log(f"Installer finished: {proc.stdout}")
            messagebox.showinfo(
                "Install complete",
                "GTK packages installed — please restart the application to enable the native chooser.",
            )
        except subprocess.CalledProcessError as e:
            out = e.stdout or str(e)
            logger.log(f"Installer failed: {out}")
            messagebox.showerror("Install failed", "Installation failed. See log for details.")
        except Exception as e:
            logger.log(f"Installer error: {e}")
            messagebox.showerror("Install error", "Could not start installer. See log for details.")

    btn_frame = tk.Frame(top)
    btn_frame.pack(fill="x", padx=12, pady=(0, 12))
    install_btn = RoundedButton(btn_frame, text="Install now", command=install_commands)
    install_btn.pack(side="left")

    copy_btn = RoundedButton(btn_frame, text="Copy commands", command=copy_commands)
    copy_btn.pack(side="left")
    close_btn = RoundedButton(btn_frame, text="Close", command=top.destroy)
    close_btn.pack(side="right")

    top.transient(window)
    top.grab_set()


def build_ui() -> tk.Tk:
    """Create and return the main application window.

    The returned `tk.Tk` is not started here; call `mainloop()` on it
    or use `run_app()` which wraps that call.
    """
    window = tk.Tk()
    window.title("Rsync Folder Copier")
    window.geometry("800x420")

    # Dark theme colors
    BG = "#0f1116"
    FG = "#e6eef6"
    ENTRY_BG = "#17181d"
    ENTRY_FG = "#e6eef6"
    BTN_BG = "#072f6b"
    BTN_FG = "#ffffff"
    ACCENT = "#27ae60"  # changed to green for progress/active accents

    # Configure ttk style for progress bar and general theme
    style = ttk.Style(window)
    try:
        style.theme_use("clam")
    except Exception:
        pass
    style.configure("Blue.Horizontal.TProgressbar", troughcolor=BG, background=ACCENT)
    window.configure(bg=BG)

    # Top frame contains two panels side-by-side
    top_frame = tk.Frame(window, bg=BG)
    top_frame.pack(fill="both", expand=True, padx=10, pady=10)
    top_frame.grid_columnconfigure(0, weight=1)
    top_frame.grid_columnconfigure(1, weight=1)

    # Left panel: Source
    left_panel = tk.Frame(top_frame, bg=BG)
    left_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

    source_label = tk.Label(left_panel, text="Source folder:", bg=BG, fg=FG)
    source_label.grid(row=0, column=0, columnspan=2, sticky="w")

    source_entry = tk.Entry(left_panel, width=60, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=ENTRY_FG)
    source_entry.grid(row=1, column=0, sticky="ew")
    left_panel.grid_columnconfigure(0, weight=1)

    def on_browse_source():
        """Handler for the source Browse button.

        Uses `core.choose_folder()` which prefers the GNOME chooser when
        available. The returned path (or URI) is written to the entry and
        also logged.
        """
        path = core.choose_folder("Select source folder")
        # If GTK was attempted but failed, prompt the user to view install instructions
        if path is None and core.USE_GTK and getattr(core, "LAST_GTK_ERROR", None):
            if messagebox.askyesno(
                "GTK chooser failed",
                "The native GTK file chooser could not be opened.\n\n" \
                "Would you like to view install instructions to enable it?",
            ):
                show_gtk_install_instructions_dialog(window)
            return
        if path:
            source_entry.delete(0, tk.END)
            source_entry.insert(0, path)
            logger.log(f"Selected source: {path}")

    source_button = RoundedButton(left_panel, text="Browse", command=on_browse_source, bg=BTN_BG, fg=BTN_FG, activebackground=ACCENT, activeforeground=BTN_FG)
    source_button.grid(row=1, column=1, padx=(8, 0))

    # Right panel: Destination
    right_panel = tk.Frame(top_frame, bg=BG)
    right_panel.grid(row=0, column=1, sticky="nsew")

    dest_label = tk.Label(right_panel, text="Destination folder:", bg=BG, fg=FG)
    dest_label.grid(row=0, column=0, columnspan=2, sticky="w")

    dest_entry = tk.Entry(right_panel, width=60, bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=ENTRY_FG)
    dest_entry.grid(row=1, column=0, sticky="ew")
    right_panel.grid_columnconfigure(0, weight=1)

    def on_browse_dest():
        """Handler for the destination Browse button.

        Mirrors `on_browse_source()` for the destination entry.
        """
        path = core.choose_folder("Select destination folder")
        if path is None and core.USE_GTK and getattr(core, "LAST_GTK_ERROR", None):
            if messagebox.askyesno(
                "GTK chooser failed",
                "The native GTK file chooser could not be opened.\n\n" \
                "Would you like to view install instructions to enable it?",
            ):
                show_gtk_install_instructions_dialog(window)
            return
        if path:
            dest_entry.delete(0, tk.END)
            dest_entry.insert(0, path)
            logger.log(f"Selected destination: {path}")

    dest_button = RoundedButton(right_panel, text="Browse", command=on_browse_dest, bg=BTN_BG, fg=BTN_FG, activebackground=ACCENT, activeforeground=BTN_FG)
    dest_button.grid(row=1, column=1, padx=(8, 0))

    # Log area
    log_label = tk.Label(window, text="Log:", bg=BG, fg=FG)
    log_label.pack(anchor="w", padx=10)

    log_text = ScrolledText(window, height=10, state="disabled", bg=ENTRY_BG, fg=ENTRY_FG, insertbackground=ENTRY_FG)
    log_text.pack(fill="both", expand=True, padx=10, pady=(0, 6))
    logger.init(log_text)

    # Controls under the browse buttons: resume, start and progress
    controls_frame = tk.Frame(window, bg=BG)
    controls_frame.pack(fill="x", padx=10, pady=(0, 6))

    resume_var = tk.BooleanVar(value=True)
    resume_check = tk.Checkbutton(controls_frame, text="Resume (keep partials)", variable=resume_var, bg=BG, fg=FG, selectcolor=BG)
    resume_check.pack(side="left", padx=(0, 8))

    progress_bar = ttk.Progressbar(controls_frame, orient="horizontal", mode="determinate", style="Blue.Horizontal.TProgressbar")
    progress_bar.pack(fill="x", expand=True, side="left")
    progress_label = tk.Label(controls_frame, text="", bg=BG, fg=FG)
    progress_label.pack(side="right")

    def _start_cmd():
        run_rsync_from_ui(source_entry, dest_entry, log_text, resume=resume_var.get(), progress_bar=progress_bar, progress_label=progress_label)

    start_button = RoundedButton(controls_frame, text="Start Rsync", command=_start_cmd, bg=BTN_BG, fg=BTN_FG, activebackground=ACCENT, activeforeground=BTN_FG)
    start_button.pack(side="left", padx=(0, 8))

    # Bottom actions frame (save log remains at bottom)
    actions_frame = tk.Frame(window, bg=BG)
    actions_frame.pack(fill="x", padx=10, pady=(6, 10))

    def on_save_log():
        """Save the current log contents to a file using the core helper.

        The core helper will use a GTK save dialog when available and
        fall back to tkinter otherwise.
        """
        content = log_text.get("1.0", tk.END)
        filename = core.save_text_to_file(content, title="Save log to file")
        if filename:
            logger.log(f"Saved log to: {filename}")

    save_log_button = RoundedButton(actions_frame, text="Save Log...", command=on_save_log, bg=BTN_BG, fg=BTN_FG, activebackground=ACCENT, activeforeground=BTN_FG)
    save_log_button.pack(side="right")

    logger.log("Application started")

    # If GTK is not available, show a small popup with copyable install
    # commands so the user can enable the native GNOME file chooser.
    if not core.USE_GTK:
        show_gtk_install_instructions_dialog(window)

    return window


def run_app():
    win = build_ui()
    win.mainloop()


def _schedule(widget, fn):
    """Schedule *fn* on the Tkinter main-loop thread via after(0, ...)."""
    try:
        widget.after(0, fn)
    except Exception:
        pass


def _run_rsync_thread(cmd, log_widget, progress_bar=None, progress_label=None, total_files=None, total_bytes=None):
    """Run rsync in a thread, parsing progress2 output for a smooth progress bar.

    Reads stdout in bytes mode, splitting on both \\r and \\n so that
    rsync's carriage-return-based progress lines are handled correctly.
    All Tkinter widget updates are scheduled on the main thread via after().
    """
    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=0,  # unbuffered for low-latency progress updates
        )
    except FileNotFoundError:
        _schedule(log_widget, lambda: messagebox.showerror(
            "rsync not found", "rsync is not installed on this system."
        ))
        return

    buf = b""

    def _handle_line(raw: bytes) -> None:
        line = raw.decode("utf-8", errors="replace").strip()
        if not line:
            return

        # Log to stdout (safe from any thread) and schedule widget append.
        print(line)

        def _append(l=line):
            try:
                log_widget.configure(state="normal")
                log_widget.insert(tk.END, l + "\n")
                log_widget.see(tk.END)
                log_widget.configure(state="disabled")
            except Exception:
                pass
        _schedule(log_widget, _append)

        # ---- Progress parsing ------------------------------------------------
        # --info=progress2 lines look like:
        #   "   102,400  10%  1.23MB/s    0:00:00 (xfr#1, to-chk=3/5)"
        # The % is the *current file's* byte progress; to-chk=M/N tells us
        # how many files are left out of the total.  We blend both for a
        # hybrid bar that advances smoothly within a file AND across files.
        if progress_bar is None:
            return
        m = re.search(r"(\d+)%.*?to-chk=(\d+)/(\d+)", line)
        if not m:
            return
        try:
            file_byte_pct = int(m.group(1))          # % of *current* file
            files_remaining = int(m.group(2))
            files_total = int(m.group(3))
            if files_total <= 0:
                return
            # Files fully completed so far (the current one is in-progress)
            files_done = files_total - files_remaining - 1
            # Fraction: completed files + partial credit for current file
            file_frac = (files_done + file_byte_pct / 100.0) / files_total
            hybrid_pct = min(99.0, file_frac * 100)  # cap at 99 until rsync exits cleanly
            label = f"{max(0, files_done + 1)}/{files_total} files — {file_byte_pct}%"

            def _upd(pct=hybrid_pct, txt=label):
                try:
                    progress_bar.configure(value=pct)
                    if progress_label:
                        progress_label.config(text=txt)
                except Exception:
                    pass
            _schedule(log_widget, _upd)
        except Exception:
            pass

    # Read output splitting on both \r and \n so progress2 carriage-return
    # lines are treated as separate events.
    while True:
        chunk = proc.stdout.read(4096)  # type: ignore[union-attr]
        if not chunk:
            break
        buf += chunk
        while True:
            nl = buf.find(b"\n")
            cr = buf.find(b"\r")
            if nl == -1 and cr == -1:
                break
            if nl == -1:
                idx = cr
            elif cr == -1:
                idx = nl
            else:
                idx = min(nl, cr)
            _handle_line(buf[:idx])
            buf = buf[idx + 1:]
    if buf:
        _handle_line(buf)

    proc.wait()

    if proc.returncode != 0:
        _schedule(log_widget, lambda: messagebox.showerror(
            "rsync failed", f"rsync exited with code {proc.returncode}"
        ))
    else:
        # Fill to 100 % on clean exit
        def _done():
            try:
                if progress_bar:
                    progress_bar.configure(value=100)
                if progress_label:
                    progress_label.config(text="Done")
            except Exception:
                pass
        _schedule(log_widget, _done)

        # Flush OS write caches — safe to do on this thread.
        try:
            logger.log("Flushing OS write cache (sync)...")
            subprocess.run(["sync"], check=True)
            logger.log("Write cache flushed to disk.")
        except subprocess.CalledProcessError:
            logger.log("Failed to flush write cache (CalledProcessError):")
            logger.log(traceback.format_exc())
        except Exception:
            logger.log("Error flushing write cache:")
            logger.log(traceback.format_exc())

        _schedule(log_widget, lambda: messagebox.showinfo(
            "rsync finished", "rsync completed successfully."
        ))


def run_rsync_from_ui(src_entry, dst_entry, log_widget, extra_opts="-ah --fsync --info=progress2", resume=False, progress_bar=None, progress_label=None):
    src = src_entry.get().strip()
    dst = dst_entry.get().strip()
    if not src or not dst:
        messagebox.showwarning("Missing paths", "Please select both source and destination.")
        return

    # Build rsync options based on resume preference
    opts = shlex.split(extra_opts)
    if resume:
        # keep partial files and use append-verify for safer resumes
        if "--partial" not in opts:
            opts += ["--partial"]
        if "--append-verify" not in opts:
            opts += ["--append-verify"]

    # Determine total files with a dry-run (runs quickly in most cases)
    total_files = None
    total_bytes = None

    def count_and_run():
        nonlocal total_files, total_bytes
        try:
            # Dry-run to get statistics
            dry_cmd = ["rsync", "-a", "--dry-run", "--stats", src + ("/" if os.path.isdir(src) else ""), dst]
            proc = subprocess.run(dry_cmd, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
            out = proc.stdout or ""
            # look for a line like: "Number of files: 123"
            for line in out.splitlines():
                    if "Number of files:" in line:
                        try:
                            total_files = int(line.split(":", 1)[1].strip())
                        except Exception:
                            total_files = None
                    # rsync --stats prints total file size as: "Total file size: 12345"
                    if "Total file size:" in line:
                        try:
                            val = line.split(":", 1)[1].strip()
                            # remove commas
                            val = val.replace(",", "")
                            total_bytes = int(val)
                        except Exception:
                            total_bytes = None
        except Exception:
            total_files = None

        # --info=progress2 already provides per-file byte % and to-chk=M/N
        # for file-count progress; --out-format is not needed.
        cmd = ["rsync"] + opts + [src, dst]
        # run in background thread so UI stays responsive
        t = threading.Thread(target=_run_rsync_thread, args=(cmd, log_widget, progress_bar, progress_label, total_files, total_bytes), daemon=True)
        t.start()

    # start counting and running in a thread so the UI doesn't lock
    threading.Thread(target=count_and_run, daemon=True).start()
