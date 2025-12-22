"""Helper script to bundle RandomBG into a standalone executable."""
from __future__ import annotations

import os
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

def _resolve_icon(project_root: Path) -> Path | None:
    """Return the icon path for PyInstaller or None if unavailable.

    Preference order:
    1. Existing ICO in the project root (logo.ico).
    2. Existing ICO in a local build/ folder.
    3. Convert the bundled logo.png into build/logo.ico on the fly.
    """

    candidates = [
        project_root / "logo.ico",
        project_root / "build" / "logo.ico",
    ]

    for candidate in candidates:
        if candidate.exists():
            return candidate

    png_source = project_root / "logo.png"
    if not png_source.exists():
        return None

    try:
        from PIL import Image
    except ImportError:  # pragma: no cover - runtime guard
        print("Pillow nicht gefunden – Icon wird nicht eingebettet.")
        return None

    target = project_root / "build" / "logo.ico"
    target.parent.mkdir(parents=True, exist_ok=True)

    try:
        with Image.open(png_source) as img:
            img.save(target)
    except Exception as exc:  # pragma: no cover - runtime guard
        print(f"Icon konnte nicht aus PNG erzeugt werden: {exc}")
        return None

    return target


def _prepare_icon(project_root: Path) -> tuple[Path | None, Path | None]:
    """Return paths to the PNG icon and a converted ICO version (if available)."""

    logo_png = project_root / "logo.png"
    logo_ico: Path | None = None

    if not logo_png.exists():
        return None, None

    logo_ico = project_root / "build" / "logo.ico"
    logo_ico.parent.mkdir(parents=True, exist_ok=True)

    try:
        from PIL import Image  # type: ignore

        with Image.open(logo_png) as img:
            img.save(logo_ico, format="ICO")
    except Exception as exc:  # pragma: no cover - runtime guard
        print(f"Warnung: Icon konnte nicht konvertiert werden ({exc}).")
        logo_ico = None

    return logo_png, logo_ico


def main() -> None:
    """Build a Windows-friendly, one-file executable via PyInstaller."""

    pyinstaller = _require_pyinstaller()
    project_root = Path(__file__).parent
    entry_point = project_root / "random_bg" / "app.py"
    logo_png, logo_ico = _prepare_icon(project_root)

    if not entry_point.exists():  # pragma: no cover - defensive guard
        raise SystemExit(f"Einstiegsdatei nicht gefunden: {entry_point}")

    name = "RandomBG"
    icon = _resolve_icon(project_root)
    hidden_imports = [
        # pystray selects a backend dynamically; ensure all candidates are bundled.
        "pystray._win32",
        "pystray._gtk",
        "pystray._xorg",
        # Pillow locates tkinter at runtime; keep the helper module in the bundle.
        "PIL._tkinter_finder",
        # Bundle our own modules explicitly because the entry point lives inside the package.
        "random_bg",
        "random_bg.app",
        "random_bg.autostart",
        "random_bg.runtime",
        "random_bg.wallpaper",
    ]

    args = [
        "--name",
        name,
        "--noconfirm",
        "--noconsole",
        "--onefile",
        "--clean",
        # Make sure the project root is on the search path during analysis.
        "--paths",
        str(project_root),
    ]

    if logo_png:
        # Bundle the PNG so the tray icon can load it at runtime.
        data_sep = ";" if os.name == "nt" else ":"
        args.extend(["--add-data", f"{logo_png}{data_sep}."])

    if logo_ico:
        args.extend(["--icon", str(logo_ico)])

    for hidden in hidden_imports:
        args.extend(["--hidden-import", hidden])

    args.append(str(entry_point))

    pyinstaller.__main__.run(args)

    artifact = project_root / "dist" / (name + (".exe" if os.name == "nt" else ""))
    print(f"Fertige Datei: {artifact}")
    print("Hinweis: Die Erstellung des Windows-Exe-Pakets funktioniert nur auf Windows zuverlässig.")


if __name__ == "__main__":
    main()
