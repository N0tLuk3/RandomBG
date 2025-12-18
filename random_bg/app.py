"""Tray application that rotates wallpapers on a timer."""
from __future__ import annotations

import json
import os
import random
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

if __name__ == "__main__" and not __package__:
    # Allow running the module directly via `python random_bg/app.py` or from
    # a PyInstaller-bundled executable where ``__package__`` can be ``""``.
    # When executed this way, relative imports would fail because there is no
    # package context. Ensure the repository root is on sys.path and set the
    # package name so the subsequent relative imports resolve correctly.
    import sys

    if getattr(sys, "frozen", False):
        base_path = Path(getattr(sys, "_MEIPASS"))
    else:
        base_path = Path(__file__).resolve().parent.parent

    sys.path.insert(0, str(base_path))
    __package__ = "random_bg"

import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

from .autostart import AutostartError, AutostartManager
from .wallpaper import (
    iter_images,
    screensaver_active,
    set_wallpaper,
)

CONFIG_FILE = Path.home() / ".random_bg_config.json"
DEFAULT_INTERVAL = 300
DEFAULT_FOLDER = str(Path.home())
DEFAULT_RANDOM_MIN = 60
DEFAULT_RANDOM_MAX = 600


@dataclass
class Settings:
    folder: str = DEFAULT_FOLDER
    interval_seconds: int = DEFAULT_INTERVAL
    autostart_enabled: bool = False
    random_mode: bool = False
    random_min_seconds: int = DEFAULT_RANDOM_MIN
    random_max_seconds: int = DEFAULT_RANDOM_MAX
    edge_background_enabled: bool = False

    @classmethod
    def load(cls) -> "Settings":
        autostart_manager = AutostartManager()
        autostart_default = autostart_manager.is_enabled()

        if CONFIG_FILE.exists():
            try:
                with CONFIG_FILE.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                return cls(
                    folder=data.get("folder", DEFAULT_FOLDER),
                    interval_seconds=int(data.get("interval_seconds", DEFAULT_INTERVAL)),
                    autostart_enabled=bool(data.get("autostart_enabled", autostart_default)),
                    random_mode=bool(data.get("random_mode", False)),
                    random_min_seconds=int(data.get("random_min_seconds", DEFAULT_RANDOM_MIN)),
                    random_max_seconds=int(data.get("random_max_seconds", DEFAULT_RANDOM_MAX)),
                    edge_background_enabled=bool(data.get("edge_background_enabled", False)),
                )
            except (OSError, ValueError):
                pass
        return cls(autostart_enabled=autostart_default)

    def save(self) -> None:
        payload = {
            "folder": self.folder,
            "interval_seconds": self.interval_seconds,
            "autostart_enabled": self.autostart_enabled,
            "random_mode": self.random_mode,
            "random_min_seconds": self.random_min_seconds,
            "random_max_seconds": self.random_max_seconds,
            "edge_background_enabled": self.edge_background_enabled,
        }
        with CONFIG_FILE.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2)


class WallpaperService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._images: List[str] = []
        self._index = 0

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._thread:
            self._stop_event.set()
            self._thread.join(timeout=2)

    def refresh_images(self) -> None:
        with self._lock:
            self._images = list(iter_images(self.settings.folder))
            self._index = -1

    def next_wallpaper(self) -> None:
        with self._lock:
            if not self._images:
                self.refresh_images()
            if not self._images:
                return
            next_index = self._index + 1
            if next_index >= len(self._images):
                random.shuffle(self._images)
                self._index = 0
            else:
                self._index = next_index
            image_path = self._images[self._index]
        set_wallpaper(image_path, sync_edge=self.settings.edge_background_enabled)

    def _next_wait(self) -> int:
        min_wait = max(10, int(self.settings.random_min_seconds))
        max_wait = max(min_wait, int(self.settings.random_max_seconds))

        if self.settings.random_mode:
            return random.randint(min_wait, max_wait)
        return max(10, int(self.settings.interval_seconds))

    def _wait_for_screensaver(self) -> bool:
        while screensaver_active():
            if self._stop_event.wait(5):
                return True
        return False

    def _wait_with_pause(self, wait_time: int) -> bool:
        elapsed = 0.0
        step = 1.0

        while elapsed < wait_time:
            if screensaver_active():
                if self._wait_for_screensaver():
                    return True
                continue

            remaining = min(step, wait_time - elapsed)
            if self._stop_event.wait(remaining):
                return True
            elapsed += remaining
        return False

    def _run(self) -> None:
        while not self._stop_event.is_set():
            if self._wait_for_screensaver():
                break

            self.next_wallpaper()
            wait_time = self._next_wait()
            if self._wait_with_pause(wait_time):
                break


class SettingsWindow:
    def __init__(self, root: tk.Tk, settings: Settings, service: WallpaperService):
        self.root = root
        self.settings = settings
        self.service = service
        self.window: Optional[tk.Toplevel] = None
        self.autostart_manager = AutostartManager()

    def open(self) -> None:
        if self.window and tk.Toplevel.winfo_exists(self.window):
            self.window.lift()
            return

        self.window = tk.Toplevel(self.root)
        self.window.title("RandomBG Einstellungen")
        self.window.resizable(False, False)

        folder_label = ttk.Label(self.window, text="Bilder-Ordner:")
        folder_label.grid(column=0, row=0, padx=8, pady=8, sticky="w")
        self.folder_var = tk.StringVar(value=self.settings.folder)
        folder_entry = ttk.Entry(self.window, textvariable=self.folder_var, width=40)
        folder_entry.grid(column=1, row=0, padx=8, pady=8)
        folder_button = ttk.Button(self.window, text="Auswählen", command=self._select_folder)
        folder_button.grid(column=2, row=0, padx=8, pady=8)

        self.interval_label = ttk.Label(self.window, text="Intervall (Sekunden):")
        self.interval_label.grid(column=0, row=1, padx=8, pady=8, sticky="w")
        self.interval_var = tk.StringVar(value=str(self.settings.interval_seconds))
        self.interval_entry = ttk.Entry(self.window, textvariable=self.interval_var, width=10)
        self.interval_entry.grid(column=1, row=1, padx=8, pady=8, sticky="w")

        random_mode_label = ttk.Label(self.window, text="Random-Modus:")
        random_mode_label.grid(column=0, row=2, padx=8, pady=8, sticky="w")
        self.random_mode_var = tk.BooleanVar(value=self.settings.random_mode)
        random_mode_checkbox = ttk.Checkbutton(
            self.window, variable=self.random_mode_var, command=self._update_interval_mode
        )
        random_mode_checkbox.grid(column=1, row=2, padx=8, pady=8, sticky="w")

        self.random_min_label = ttk.Label(self.window, text="Minimum (Sekunden):")
        self.random_min_label.grid(column=0, row=3, padx=8, pady=8, sticky="w")
        self.random_min_var = tk.StringVar(value=str(self.settings.random_min_seconds))
        self.random_min_entry = ttk.Entry(self.window, textvariable=self.random_min_var, width=10)
        self.random_min_entry.grid(column=1, row=3, padx=8, pady=8, sticky="w")

        self.random_max_label = ttk.Label(self.window, text="Maximum (Sekunden):")
        self.random_max_label.grid(column=0, row=4, padx=8, pady=8, sticky="w")
        self.random_max_var = tk.StringVar(value=str(self.settings.random_max_seconds))
        self.random_max_entry = ttk.Entry(self.window, textvariable=self.random_max_var, width=10)
        self.random_max_entry.grid(column=1, row=4, padx=8, pady=8, sticky="w")

        autostart_label = ttk.Label(self.window, text="Autostart aktivieren:")
        autostart_label.grid(column=0, row=5, padx=8, pady=(0, 8), sticky="w")
        self.autostart_var = tk.BooleanVar(value=self.settings.autostart_enabled)
        autostart_checkbox = ttk.Checkbutton(self.window, variable=self.autostart_var)
        autostart_checkbox.grid(column=1, row=5, padx=8, pady=(0, 8), sticky="w")

        edge_label = ttk.Label(self.window, text="Edge-Hintergrund setzen:")
        edge_label.grid(column=0, row=6, padx=8, pady=(0, 8), sticky="w")
        self.edge_background_var = tk.BooleanVar(value=self.settings.edge_background_enabled)
        edge_checkbox = ttk.Checkbutton(self.window, variable=self.edge_background_var)
        edge_checkbox.grid(column=1, row=6, padx=8, pady=(0, 8), sticky="w")

        save_button = ttk.Button(self.window, text="Speichern", command=self._save)
        save_button.grid(column=0, row=7, padx=8, pady=12, columnspan=3)

    def _select_folder(self) -> None:
        folder = filedialog.askdirectory(initialdir=self.settings.folder)
        if folder:
            self.folder_var.set(folder)

    def _update_interval_mode(self) -> None:
        random_on = self.random_mode_var.get()
        if random_on:
            self.interval_label.grid_remove()
            self.interval_entry.grid_remove()
            self.random_min_label.grid()
            self.random_min_entry.grid()
            self.random_max_label.grid()
            self.random_max_entry.grid()
        else:
            self.interval_label.grid()
            self.interval_entry.grid()
            self.random_min_label.grid_remove()
            self.random_min_entry.grid_remove()
            self.random_max_label.grid_remove()
            self.random_max_entry.grid_remove()

    def _save(self) -> None:
        random_mode = self.random_mode_var.get()
        try:
            random_min = int(self.random_min_var.get())
            random_max = int(self.random_max_var.get())
        except ValueError:
            messagebox.showerror("Ungültiges Intervall", "Bitte ganze Zahlen für Minimum/Maximum eingeben.")
            return

        if random_min < 10 or random_max < 10:
            messagebox.showerror("Ungültiges Intervall", "Bitte Werte >= 10 angeben.")
            return
        if random_max < random_min:
            messagebox.showerror("Ungültiges Intervall", "Maximum muss größer oder gleich dem Minimum sein.")
            return

        interval = self.settings.interval_seconds
        if not random_mode:
            try:
                interval = int(self.interval_var.get())
                if interval < 10:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Ungültiges Intervall", "Bitte eine Zahl >= 10 eingeben.")
                return

        folder = self.folder_var.get()
        if not folder or not os.path.isdir(folder):
            messagebox.showerror("Ordner nicht gefunden", "Bitte einen gültigen Ordner wählen.")
            return

        self.settings.interval_seconds = interval
        self.settings.random_mode = random_mode
        self.settings.random_min_seconds = random_min
        self.settings.random_max_seconds = random_max
        self.settings.folder = folder
        autostart_requested = self.autostart_var.get()
        edge_background_enabled = self.edge_background_var.get()

        try:
            if autostart_requested:
                self.autostart_manager.enable()
            else:
                self.autostart_manager.disable()
            self.settings.autostart_enabled = autostart_requested
        except AutostartError as exc:
            messagebox.showerror("Autostart", str(exc))
            return

        self.settings.edge_background_enabled = edge_background_enabled
        self.settings.save()
        self.service.refresh_images()
        messagebox.showinfo("Gespeichert", "Einstellungen übernommen.")
        if self.window:
            self.window.destroy()


def _create_icon() -> Image.Image:
    img = Image.new("RGB", (64, 64), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle([(8, 8), (56, 56)], outline="black", width=2)
    draw.line([(8, 40), (56, 24)], fill="blue", width=4)
    draw.rectangle([(18, 24), (30, 36)], fill="green")
    draw.ellipse([(36, 16), (48, 28)], fill="yellow")
    return img


def run_tray() -> None:
    settings = Settings.load()
    service = WallpaperService(settings)
    service.refresh_images()
    service.start()

    root = tk.Tk()
    root.withdraw()
    settings_window = SettingsWindow(root, settings, service)

    def on_settings() -> None:
        root.after(0, settings_window.open)

    def on_next() -> None:
        service.next_wallpaper()

    def on_quit(icon: Any, _item: object) -> None:
        service.stop()
        icon.stop()
        root.quit()

    menu = (
        MenuItem("Einstellungen", lambda icon, item: on_settings()),
        MenuItem("Nächstes Hintergrundbild", lambda icon, item: on_next()),
        MenuItem("Beenden", on_quit),
    )
    icon = pystray.Icon("RandomBG", _create_icon(), "RandomBG", menu)

    tray_thread = threading.Thread(target=icon.run, daemon=True)
    tray_thread.start()

    try:
        root.mainloop()
    finally:
        service.stop()
        if icon:
            icon.stop()


if __name__ == "__main__":
    run_tray()
