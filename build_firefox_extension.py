"""Copy the Firefox new-tab extension next to the packaged executable.

This helper replicates the contents of the local ``firefox_extension`` folder
into the directory that contains ``sys.executable`` (e.g., alongside a built
RandomBG.exe). Existing files are overwritten; other files are left untouched.

It also writes a signed-install-ready XPI archive (unsigned) in the same
target folder so the extension can be installed persistently if you sign it
or deploy it via Firefox policies.
"""

from __future__ import annotations

import shutil
import sys
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED


def copy_extension(source_dir: Path, target_dir: Path) -> None:
    target_dir.mkdir(parents=True, exist_ok=True)
    for entry in source_dir.iterdir():
        if entry.is_dir():
            dest = target_dir / entry.name
            dest.mkdir(parents=True, exist_ok=True)
            for sub in entry.rglob("*"):
                if sub.is_dir():
                    continue
                rel = sub.relative_to(entry)
                dest_file = dest / rel
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(sub, dest_file)
        else:
            dest = target_dir / entry.name
            shutil.copy2(entry, dest)


def build_xpi(source_dir: Path, target_dir: Path, name: str = "randombg_newtab.xpi") -> Path:
    """Package the extension folder as an unsigned XPI archive."""

    xpi_path = target_dir / name
    with ZipFile(xpi_path, "w", ZIP_DEFLATED) as zf:
        for item in source_dir.rglob("*"):
            if item.is_dir():
                continue
            rel = item.relative_to(source_dir)
            zf.write(item, rel.as_posix())
    return xpi_path


def main() -> None:
    project_root = Path(__file__).resolve().parent
    source = project_root / "firefox_extension"

    if not source.exists():
        raise SystemExit(f"Quellordner fehlt: {source}")

    if not getattr(sys, "executable", ""):
        raise SystemExit("sys.executable ist leer; Pfad zum Zielordner unklar.")

    target = Path(sys.executable).resolve().parent / "firefox_extension"
    copy_extension(source, target)
    xpi = build_xpi(source, target)
    print(f"Firefox-Extension kopiert nach: {target}")
    print(f"XPI erzeugt: {xpi} (zum Signieren/Deploy via Policy)")


if __name__ == "__main__":
    main()
