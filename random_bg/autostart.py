"""Autostart helpers for RandomBG."""
from __future__ import annotations

import os
import platform
import shlex
import subprocess
import sys
import textwrap
from pathlib import Path
from typing import List


class AutostartError(RuntimeError):
    """Raised when enabling or disabling autostart fails."""


class AutostartManager:
    """Manage platform-specific autostart configuration."""

    APP_NAME = "RandomBG"

    def __init__(self) -> None:
        system = platform.system().lower()
        self._platform = system
        self._windows_shortcut = Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs/Startup/RandomBG.bat"
        self._linux_desktop = Path.home() / ".config" / "autostart" / "RandomBG.desktop"
        self._mac_plist = Path.home() / "Library" / "LaunchAgents" / "com.randombg.app.plist"

    def is_supported(self) -> bool:
        return self._platform in {"windows", "linux", "darwin"}

    def is_enabled(self) -> bool:
        path = self._target_path()
        return path is not None and path.exists()

    def enable(self) -> None:
        if not self.is_supported():
            raise AutostartError(f"Autostart wird auf {self._platform} nicht unterstützt.")

        command = self._launch_command()
        try:
            if self._platform == "windows":
                self._enable_windows(command)
            elif self._platform == "linux":
                self._enable_linux(command)
            elif self._platform == "darwin":
                self._enable_macos(command)
        except OSError as exc:
            raise AutostartError(f"Autostart konnte nicht aktiviert werden: {exc}") from exc

    def disable(self) -> None:
        target = self._target_path()
        if target and target.exists():
            try:
                target.unlink()
            except OSError as exc:
                raise AutostartError(f"Autostart konnte nicht deaktiviert werden: {exc}") from exc

    def _target_path(self) -> Path | None:
        if self._platform == "windows":
            return self._windows_shortcut
        if self._platform == "linux":
            return self._linux_desktop
        if self._platform == "darwin":
            return self._mac_plist
        return None

    def _launch_command(self) -> List[str]:
        if getattr(sys, "frozen", False):
            return [sys.executable]

        executable = sys.executable
        if os.name == "nt" and executable.lower().endswith("python.exe"):
            pythonw = Path(executable).with_name("pythonw.exe")
            if pythonw.exists():
                executable = str(pythonw)

        return [executable, "-m", "random_bg.app"]

    def _enable_windows(self, command: List[str]) -> None:
        if not self._windows_shortcut.parent.exists():
            self._windows_shortcut.parent.mkdir(parents=True, exist_ok=True)

        # Use Windows-native quoting to avoid the single quotes that ``shlex.quote``
        # would add on paths containing spaces (e.g. under ``Program Files``).
        quoted = subprocess.list2cmdline(command)
        content = f"@echo off\r\nstart \"\" {quoted}\r\n"
        self._windows_shortcut.write_text(content, encoding="utf-8")

    def _enable_linux(self, command: List[str]) -> None:
        desktop_dir = self._linux_desktop.parent
        desktop_dir.mkdir(parents=True, exist_ok=True)

        exec_cmd = " ".join(shlex.quote(part) for part in command)
        desktop_file = textwrap.dedent(
            f"""
            [Desktop Entry]
            Type=Application
            Name={self.APP_NAME}
            Exec={exec_cmd}
            X-GNOME-Autostart-enabled=true
            Terminal=false
            """
        ).strip()
        self._linux_desktop.write_text(desktop_file + "\n", encoding="utf-8")

    def _enable_macos(self, command: List[str]) -> None:
        launch_agents = self._mac_plist.parent
        launch_agents.mkdir(parents=True, exist_ok=True)

        program = command[0]
        arguments = "".join(f"\n        <string>{arg}</string>" for arg in command[1:])
        plist = textwrap.dedent(
            f"""
            <?xml version="1.0" encoding="UTF-8"?>
            <!DOCTYPE plist PUBLIC "-//Apple Computer//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
            <plist version="1.0">
            <dict>
                <key>Label</key>
                <string>com.randombg.app</string>
                <key>ProgramArguments</key>
                <array>
                    <string>{program}</string>{arguments}
                </array>
                <key>RunAtLoad</key>
                <true/>
            </dict>
            </plist>
            """
        ).strip()
        self._mac_plist.write_text(plist + "\n", encoding="utf-8")
