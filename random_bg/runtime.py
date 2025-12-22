"""Runtime helpers to make PyInstaller bundles behave like the source checkout."""
from __future__ import annotations

import sys
from pathlib import Path


def prepare_sys_path() -> Path:
    """Ensure the package root is importable when frozen or run from source.

    PyInstaller extracts one-file bundles into a temporary directory that lives in
    ``sys._MEIPASS``. The function mirrors that behaviour locally so that relative
    imports such as ``random_bg.wallpaper`` continue to work after freezing.
    """

    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    package_dir = base_dir / "random_bg" if (base_dir / "random_bg").exists() else base_dir

    # Insert the repo root (parent of the package) into ``sys.path`` so that
    # absolute imports keep working no matter where the executable was extracted.
    repo_root = package_dir.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))

    return package_dir


def freeze_support_if_needed() -> None:
    """Call ``multiprocessing.freeze_support`` when running a frozen build on Windows."""

    if getattr(sys, "frozen", False):
        try:
            from multiprocessing import freeze_support
        except ImportError:
            return
        freeze_support()
