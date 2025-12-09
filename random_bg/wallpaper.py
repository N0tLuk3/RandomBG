"""Wallpaper utilities for cross-platform background changes."""
from __future__ import annotations

import os
import platform
import subprocess
from typing import Callable, Iterable

SPI_SETDESKWALLPAPER = 20


def _apply_windows_wallpaper(image_path: str) -> None:
    image_abs_path = os.path.abspath(image_path)
    # SPI_SETDESKWALLPAPER = 20, update INI file + broadcast change (flag 3)
    import ctypes

    ctypes.windll.user32.SystemParametersInfoW(SPI_SETDESKWALLPAPER, 0, image_abs_path, 3)


def _apply_macos_wallpaper(image_path: str) -> None:
    script = f'tell application "Finder" to set desktop picture to POSIX file "{image_path}"'
    subprocess.run(["osascript", "-e", script], check=False)


def _apply_linux_wallpaper(image_path: str) -> None:
    # GNOME fallback using gsettings
    subprocess.run(
        [
            "gsettings",
            "set",
            "org.gnome.desktop.background",
            "picture-uri",
            f"file://{os.path.abspath(image_path)}",
        ],
        check=False,
    )


def _platform_handler() -> Callable[[str], None]:
    system = platform.system().lower()
    if system == "windows":
        return _apply_windows_wallpaper
    if system == "darwin":
        return _apply_macos_wallpaper
    return _apply_linux_wallpaper


def set_wallpaper(image_path: str) -> None:
    """Set the wallpaper for the current platform.

    Parameters
    ----------
    image_path: str
        Path to an image file to set as the desktop background.
    """

    handler = _platform_handler()
    handler(image_path)


def iter_images(folder: str) -> Iterable[str]:
    """Yield image file paths from a folder."""

    if not os.path.isdir(folder):
        return []

    supported_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
    for entry in sorted(os.listdir(folder)):
        path = os.path.join(folder, entry)
        if os.path.isfile(path) and os.path.splitext(entry)[1].lower() in supported_extensions:
            yield path
