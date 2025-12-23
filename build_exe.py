"""Helper script to bundle RandomBG into a standalone executable."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Protocol, cast


class PyInstallerMain(Protocol):
    @staticmethod
    def run(args: list[str]) -> None:
        ...


class PyInstallerModule(Protocol):
    __main__: PyInstallerMain


def _require_pyinstaller() -> PyInstallerModule:
    try:
        import PyInstaller  # type: ignore
        import PyInstaller.__main__  # type: ignore
    except ImportError as exc:  # pragma: no cover - runtime guard
        print("PyInstaller ist nicht installiert. Bitte zuerst `pip install pyinstaller` ausfuehren.")
        raise SystemExit(1) from exc
    return cast(PyInstallerModule, PyInstaller)


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

        sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (24, 24), (16, 16)]
        with Image.open(logo_png) as img:
            icon_source = img.convert("RGBA")
            icon_source.save(logo_ico, format="ICO", sizes=sizes)
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

    if not logo_png:
        raise SystemExit("logo.png nicht gefunden - Icon kann nicht eingebettet werden.")
    if not logo_ico:
        raise SystemExit("Icon konnte nicht aus logo.png erzeugt werden (siehe Meldung oben).")

    if not entry_point.exists():  # pragma: no cover - defensive guard
        raise SystemExit(f"Einstiegsdatei nicht gefunden: {entry_point}")

    name = "RandomBG"
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

    # Bundle the Firefox extension assets so we can deploy them at runtime.
    ext_dir = project_root / "firefox_extension"
    if ext_dir.exists():
        data_sep = ";" if os.name == "nt" else ":"
        args.extend(["--add-data", f"{ext_dir}{data_sep}firefox_extension"])

    args.extend(["--icon", str(logo_ico)])

    for hidden in hidden_imports:
        args.extend(["--hidden-import", hidden])

    args.append(str(entry_point))

    pyinstaller.__main__.run(args)

    artifact = project_root / "dist" / (name + (".exe" if os.name == "nt" else ""))
    print(f"Fertige Datei: {artifact}")
    print("Hinweis: Die Erstellung des Windows-Exe-Pakets funktioniert nur auf Windows zuverlaessig.")


if __name__ == "__main__":
    main()
