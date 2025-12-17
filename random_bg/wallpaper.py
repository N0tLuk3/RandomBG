"""Wallpaper utilities for cross-platform background changes."""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import json
from pathlib import Path
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


def set_wallpaper(image_path: str, *, sync_edge: bool = False) -> None:
    """Set the wallpaper for the current platform.

    Parameters
    ----------
    image_path: str
        Path to an image file to set as the desktop background.
    sync_edge: bool
        When True on Windows, also update the Microsoft Edge new tab background
        to the same image. Ignored on other platforms.
    """

    handler = _platform_handler()
    handler(image_path)
    if sync_edge:
        set_edge_background(image_path)


def set_edge_background(image_path: str) -> None:
    """Best-effort sync of the Microsoft Edge New Tab background with the wallpaper.

    Only has an effect on Windows installations with a default Edge profile. The
    function updates the `Preferences` JSON file so that Edge uses the provided
    image as custom New Tab background. Failures are silently ignored.
    """

    if platform.system().lower() != "windows":
        return

    local_app_data = os.getenv("LOCALAPPDATA")
    if not local_app_data:
        return

    prefs_path = Path(local_app_data) / "Microsoft" / "Edge" / "User Data" / "Default" / "Preferences"
    if not prefs_path.exists():
        return

    try:
        with prefs_path.open("r", encoding="utf-8") as handle:
            prefs = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return

    image_full_path = Path(image_path).resolve()
    background_dict = prefs.get("ntp_custom_background_dict", {})
    background_dict.update(
        {
            "background_url": "",
            "collection_id": "",
            "custom_background_local_to_drive": False,
            "local_background_image_file_url": image_full_path.as_uri(),
            "local_background_image_path": str(image_full_path),
        }
    )
    prefs["ntp_custom_background_dict"] = background_dict
    prefs["ntp_custom_background_enabled"] = True
    prefs["ntp_custom_background_set_by_admin"] = False

    try:
        with prefs_path.open("w", encoding="utf-8") as handle:
            json.dump(prefs, handle, indent=2)
    except OSError:
        return


def iter_images(folder: str) -> Iterable[str]:
    """Yield image file paths from a folder."""

    if not os.path.isdir(folder):
        return []

    supported_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
    for entry in sorted(os.listdir(folder)):
        path = os.path.join(folder, entry)
        if os.path.isfile(path) and os.path.splitext(entry)[1].lower() in supported_extensions:
            yield path


def _windows_screensaver_active() -> bool:
    import ctypes

    active = ctypes.c_int()
    # SPI_GETSCREENSAVERRUNNING = 114
    result = ctypes.windll.user32.SystemParametersInfoW(114, 0, ctypes.byref(active), 0)
    return bool(result and active.value)


def _macos_screensaver_active() -> bool:
    # ScreenSaverEngine runs while the macOS screensaver is active
    try:
        process = subprocess.run(
            ["pgrep", "-x", "ScreenSaverEngine"],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except FileNotFoundError:
        return False
    return process.returncode == 0


def _linux_screensaver_active() -> bool:
    command = shutil.which("gnome-screensaver-command")
    if not command:
        return False

    try:
        process = subprocess.run(
            [command, "--query"],
            check=False,
            capture_output=True,
            text=True,
        )
    except (FileNotFoundError, OSError):
        return False

    return "is active" in process.stdout.lower()


def screensaver_active() -> bool:
    """Best-effort detection of an active screensaver."""

    system = platform.system().lower()
    if system == "windows":
        return _windows_screensaver_active()
    if system == "darwin":
        return _macos_screensaver_active()
    return _linux_screensaver_active()
