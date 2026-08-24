"""Resolves where this app's local data files (login, audit log, exclusions,
manifest, scan results) live - next to the source files in dev mode, or next
to the .exe when packaged with PyInstaller. Never inside PyInstaller's
temporary onefile extraction folder, which is wiped after every run."""

import sys
from pathlib import Path


def _compute_data_dir():
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


DATA_DIR = _compute_data_dir()
