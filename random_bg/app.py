"""Tray application that rotates wallpapers on a timer."""
from __future__ import annotations

import json
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, List, Optional

import pystray
from PIL import Image, ImageDraw
from pystray import MenuItem
from tkinter import filedialog, messagebox, ttk
import tkinter as tk

from .wallpaper import iter_images, set_wallpaper

CONFIG_FILE = Path.home() / ".random_bg_config.json"
DEFAULT_INTERVAL = 300
DEFAULT_FOLDER = str(Path.home())


@dataclass
class Settings:
    folder: str = DEFAULT_FOLDER
    interval_seconds: int = DEFAULT_INTERVAL

    @classmethod
    def load(cls) -> "Settings":
        if CONFIG_FILE.exists():
            try:
                with CONFIG_FILE.open("r", encoding="utf-8") as handle:
                    data = json.load(handle)
                return cls(
                    folder=data.get("folder", DEFAULT_FOLDER),
                    interval_seconds=int(data.get("interval_seconds", DEFAULT_INTERVAL)),
                )
            except (OSError, ValueError):
                pass
        return cls()

    def save(self) -> None:
        payload = {"folder": self.folder, "interval_seconds": self.interval_seconds}
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
            self._index = 0

    def next_wallpaper(self) -> None:
        with self._lock:
            if not self._images:
                self.refresh_images()
            if not self._images:
                return
            self._index = (self._index + 1) % len(self._images)
            image_path = self._images[self._index]
        set_wallpaper(image_path)

    def _run(self) -> None:
        while not self._stop_event.is_set():
            self.next_wallpaper()
            wait_time = max(10, self.settings.interval_seconds)
            self._stop_event.wait(wait_time)


class SettingsWindow:
    def __init__(self, root: tk.Tk, settings: Settings, service: WallpaperService):
        self.root = root
        self.settings = settings
        self.service = service
        self.window: Optional[tk.Toplevel] = None

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

        interval_label = ttk.Label(self.window, text="Intervall (Sekunden):")
        interval_label.grid(column=0, row=1, padx=8, pady=8, sticky="w")
        self.interval_var = tk.StringVar(value=str(self.settings.interval_seconds))
        interval_entry = ttk.Entry(self.window, textvariable=self.interval_var, width=10)
        interval_entry.grid(column=1, row=1, padx=8, pady=8, sticky="w")

        save_button = ttk.Button(self.window, text="Speichern", command=self._save)
        save_button.grid(column=0, row=2, padx=8, pady=12, columnspan=3)

    def _select_folder(self) -> None:
        folder = filedialog.askdirectory(initialdir=self.settings.folder)
        if folder:
            self.folder_var.set(folder)

    def _save(self) -> None:
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
        self.settings.folder = folder
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
