"""Wallpaper utilities for cross-platform background changes."""
from __future__ import annotations

import os
import platform
import random
import shutil
import subprocess
from pathlib import Path
from typing import Callable, List

import configparser
import json

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


def set_wallpaper(
    image_path: str,
    *,
    apply_wallpaper: bool = True,
    sync_edge: bool = False,
    sync_chrome: bool = False,
    sync_firefox: bool = False,
) -> None:
    """Set the wallpaper for the current platform.

    Parameters
    ----------
    image_path: str
        Path to an image file to set as the desktop background.
    apply_wallpaper: bool
        When False, skip setting the system wallpaper but still sync browsers.
    sync_edge/chrome/firefox: bool
        When True on Windows, also update the respective browser new tab background
        to the same image. Ignored on other platforms.
    """

    shared = _write_shared_wallpaper(image_path)
    effective_wallpaper = image_path  # always use the original for the OS
    effective_browser = shared if shared else image_path

    if apply_wallpaper:
        handler = _platform_handler()
        handler(effective_wallpaper)
    if platform.system().lower() == "windows":
        if sync_edge:
            set_edge_background(effective_browser)
        if sync_chrome:
            set_chrome_background(effective_browser)
        if sync_firefox:
            set_firefox_background(effective_browser)


def set_edge_background(image_path: str) -> None:
    """Best-effort sync of the Microsoft Edge New Tab background with the wallpaper.

    Only has an effect on Windows installations with a default Edge profile. The
    function updates the `Preferences` JSON file so that Edge uses the provided
    image as custom New Tab background. Failures are silently ignored.
    """

    if platform.system().lower() != "windows":
        return

    local_app_data = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
    user_data_dir = Path(local_app_data) / "Microsoft" / "Edge" / "User Data"
    for prefs_path in _chromium_pref_files(user_data_dir):
        _write_chromium_background(prefs_path, image_path)


def set_chrome_background(image_path: str) -> None:
    """Best-effort sync of the Google Chrome New Tab background with the wallpaper."""

    if platform.system().lower() != "windows":
        return

    local_app_data = os.getenv("LOCALAPPDATA")
    if not local_app_data:
        return

    prefs_path = Path(local_app_data) / "Google" / "Chrome" / "User Data" / "Default" / "Preferences"
    _write_chromium_background(prefs_path, image_path)


def _write_chromium_background(prefs_path: Path, image_path: str) -> None:
    if not prefs_path.exists():
        return

    try:
        with prefs_path.open("r", encoding="utf-8") as handle:
            prefs = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return

    image_full_path = Path(image_path).resolve()
    # Copy into the profile to avoid permissions/cross-drive surprises.
    try:
        copied = prefs_path.parent / "randombg_wallpaper.png"
        shutil.copyfile(image_full_path, copied)
        image_full_path = copied.resolve()
    except OSError:
        pass

    image_uri = image_full_path.as_uri()
    background_dict = prefs.get("ntp_custom_background_dict", {})
    background_dict.update(
        {
            "background_url": "",
            "collection_id": "",
            "custom_background_local_to_drive": True,
            "local_background_image_file_url": image_uri,
            "local_background_image_path": str(image_full_path),
            "local_background_image_id": "",
        }
    )
    prefs["ntp_custom_background_dict"] = background_dict
    prefs["ntp_custom_background_enabled"] = True
    prefs["ntp_custom_background_set_by_admin"] = False
    prefs["ntp_custom_background_disabled_by_policy"] = False
    prefs["ntp_show_background_image"] = True
    prefs["ntp_background_source"] = 1  # 1 = custom background
    prefs["ntp_custom_background_local_to_device"] = True

    try:
        with prefs_path.open("w", encoding="utf-8") as handle:
            json.dump(prefs, handle, indent=2)
    except OSError:
        return


def _write_shared_wallpaper(image_path: str) -> Path | None:
    """Write a stable copy of the current image next to the user's folder as randombg_wallpaper.png."""

    source = Path(image_path)
    target = source.parent / "randombg_wallpaper.png"

    try:
        from PIL import Image  # type: ignore

        with Image.open(source) as img:
            img.save(target, format="PNG")
        return target
    except Exception:
        # Fallback to raw copy if Pillow is unavailable or conversion fails.
        try:
            shutil.copyfile(source, target)
            return target
        except OSError:
            return None


def set_firefox_background(image_path: str) -> Path | None:
    """Best-effort sync of the Firefox new tab background with the wallpaper."""

    chosen_css: Path | None = None
    for profile_dir in _locate_firefox_profiles():
        chrome_dir = profile_dir / "chrome"
        chrome_dir.mkdir(parents=True, exist_ok=True)

        image_full_path = Path(image_path).resolve()

        file_url = image_full_path.as_uri()

        newtab_html = image_full_path.with_name("randombg_newtab.html")
        _write_firefox_newtab_html(newtab_html, file_url)
        _ensure_firefox_prefs(profile_dir, newtab_html)

        user_content = chrome_dir / "userContent.css"
        if not chosen_css:
            chosen_css = user_content

    return chosen_css


def _chromium_pref_files(user_data_dir: Path) -> list[Path]:
    """Return Preferences.json files for all user-facing Chromium profiles."""

    if not user_data_dir.exists():
        return []

    prefs: list[Path] = []
    for child in user_data_dir.iterdir():
        if not child.is_dir():
            continue
        if child.name.lower() == "system profile":
            continue
        pref = child / "Preferences"
        if pref.exists():
            prefs.append(pref)
    return prefs


def _locate_firefox_profiles() -> list[Path]:
    system = platform.system().lower()
    if system == "windows":
        base = os.getenv("APPDATA")
        if not base:
            return []
        base_dir = Path(base) / "Mozilla" / "Firefox"
    elif system == "darwin":
        base_dir = Path.home() / "Library" / "Application Support" / "Firefox"
    else:
        base_dir = Path.home() / ".mozilla" / "firefox"

    profiles_ini = base_dir / "profiles.ini"
    if not profiles_ini.exists():
        return []

    parser = configparser.RawConfigParser()
    try:
        parser.read(profiles_ini)
    except (OSError, configparser.Error):
        return []

    paths: list[Path] = []
    default_profile: Path | None = None

    for section in parser.sections():
        if not section.lower().startswith("profile"):
            continue
        path_value = parser.get(section, "Path", fallback=None)
        if not path_value:
            continue
        is_relative = parser.get(section, "IsRelative", fallback="1") == "1"
        profile_path = Path(path_value)
        profile_path = (base_dir / profile_path) if is_relative else profile_path
        if not profile_path.exists():
            continue
        if parser.get(section, "Default", fallback="0") == "1":
            default_profile = profile_path
        paths.append(profile_path)

    if default_profile and default_profile in paths:
        # Put default first for determinism.
        paths = [default_profile] + [p for p in paths if p != default_profile]
    return paths


def _ensure_firefox_prefs(profile_dir: Path, newtab_html: Path) -> None:
    prefs_path = profile_dir / "user.js"
    wanted = {
        "toolkit.legacyUserProfileCustomizations.stylesheets": True,
        "browser.newtabpage.activity-stream.newTabURL": newtab_html.resolve().as_uri(),
        "browser.newtabpage.enabled": True,
        "browser.newtabpage.activity-stream.enabled": True,
    }

    existing: dict[str, str] = {}
    if prefs_path.exists():
        try:
            for line in prefs_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line.startswith("user_pref("):
                    continue
                if "," not in line:
                    continue
                key_part = line.split(",", 1)[0]
                key = key_part.replace("user_pref(", "").strip().strip('"')
                existing[key] = line
        except OSError:
            return

    def _format_value(val: object) -> str:
        if isinstance(val, bool):
            return "true" if val else "false"
        if isinstance(val, (int, float)):
            return str(val)
        return f'"{val}"'

    new_lines = [line for key, line in existing.items() if key not in wanted]
    for key, val in wanted.items():
        new_lines.append(f'user_pref("{key}", {_format_value(val)});')

    try:
        prefs_path.write_text("\n".join(new_lines) + ("\n" if new_lines else ""), encoding="utf-8")
    except OSError:
        return


def _write_firefox_newtab_html(target: Path, image_url: str) -> None:
    """Write a minimal new-tab HTML that uses the provided image URL as background."""

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    html, body {{
      width: 100%;
      height: 100%;
      margin: 0;
      padding: 0;
      background: url('{image_url}') center center / cover no-repeat fixed;
    }}
  </style>
</head>
<body></body>
</html>
"""
    try:
        target.write_text(html, encoding="utf-8")
    except OSError:
        pass


def iter_images(folder: str) -> List[str]:
    """Return image file paths from a folder in randomized order."""

    if not os.path.isdir(folder):
        return []

    supported_extensions = {".png", ".jpg", ".jpeg", ".bmp", ".gif"}
    images = [
        os.path.join(folder, entry)
        for entry in os.listdir(folder)
        if os.path.isfile(os.path.join(folder, entry))
        and os.path.splitext(entry)[1].lower() in supported_extensions
    ]
    random.shuffle(images)
    return images


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
