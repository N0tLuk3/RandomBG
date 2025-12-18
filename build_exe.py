"""Helper script to bundle RandomBG into a standalone executable."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import PyInstaller as PyInstallerModule  # type: ignore


def _require_pyinstaller() -> "PyInstallerModule":
    try:
        import PyInstaller  # type: ignore
        import PyInstaller.__main__  # type: ignore
    except ImportError as exc:  # pragma: no cover - runtime guard
        print("PyInstaller ist nicht installiert. Bitte zuerst `pip install pyinstaller` ausführen.")
        raise SystemExit(1) from exc
    return PyInstaller


def main() -> None:
    """Build a Windows-friendly, one-file executable via PyInstaller."""

    pyinstaller = _require_pyinstaller()
    project_root = Path(__file__).parent
    entry_point = project_root / "random_bg" / "app.py"

    if not entry_point.exists():  # pragma: no cover - defensive guard
        raise SystemExit(f"Einstiegsdatei nicht gefunden: {entry_point}")

    name = "RandomBG"
    args = [
        "--name",
        name,
        "--noconfirm",
        "--noconsole",
        "--onefile",
        "--clean",
        str(entry_point),
    ]

    pyinstaller.__main__.run(args)

    artifact = project_root / "dist" / (name + (".exe" if os.name == "nt" else ""))
    print(f"Fertige Datei: {artifact}")
    print("Hinweis: Die Erstellung des Windows-Exe-Pakets funktioniert nur auf Windows zuverlässig.")


if __name__ == "__main__":
    main()
