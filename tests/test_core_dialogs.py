import os

import pytest

from rsync_helper import core


class Proc:
    def __init__(self, out: str):
        self.stdout = out


def test_choose_folder_zenity_returns_path(monkeypatch, tmp_path):
    # Simulate zenity present and returning a selected folder
    monkeypatch.setattr(core, "USE_GTK", True)
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/zenity")

    def fake_run(cmd, check=False, stdout=None, stderr=None, text=None):
        return Proc(str(tmp_path))

    monkeypatch.setattr("subprocess.run", fake_run)

    res = core.choose_folder("Select folder")
    assert res == str(tmp_path)


def test_choose_folder_zenity_cancel_returns_none(monkeypatch):
    monkeypatch.setattr(core, "USE_GTK", True)
    monkeypatch.setattr("shutil.which", lambda name: "/usr/bin/zenity")

    def fake_run(cmd, check=False, stdout=None, stderr=None, text=None):
        return Proc("")

    monkeypatch.setattr("subprocess.run", fake_run)

    res = core.choose_folder("Select folder")
    assert res is None


def test_save_text_to_file_asksaveasfilename(monkeypatch, tmp_path):
    # Ensure fallback to tkinter asking for filename works
    monkeypatch.setattr(core, "USE_GTK", False)

    filename = tmp_path / "output.log"

    monkeypatch.setattr("tkinter.filedialog.asksaveasfilename", lambda **k: str(filename))

    res = core.save_text_to_file("hello world", title="Save test")
    assert res == str(filename)
    with open(res, "r", encoding="utf-8") as f:
        assert f.read() == "hello world"
