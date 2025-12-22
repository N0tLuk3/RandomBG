# RandomBG

[Deutsche Version](README/README.de.md)

Python tray app that automatically changes your desktop background on a fixed or random schedule.

## Installation

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

## Usage

```bash
python -m random_bg.app
```

* The tray icon appears and rotates backgrounds automatically.
* Under "Settings" you can choose folders, set the interval (seconds), and toggle autostart.
* On Windows you can optionally set the current image as the Microsoft Edge start page background.
* "Next background" immediately switches to the next image from the selected folder.
* Configuration is stored in `~/.random_bg_config.json`.

## Build a Windows executable

Use the included build script to create a portable Windows executable that runs without a separate Python runtime:

1. Install PyInstaller in your active Python environment:

   ```bash
   pip install pyinstaller
   ```

2. Build the executable package (run on Windows):

   ```bash
   python build_exe.py
   ```

   The final file is written to `dist/RandomBG.exe` and bundles all dependencies.

## Run in the background without a terminal

* **Windows:** Use `pythonw.exe -m random_bg.app` so no console window opens; the tray icon stays visible.
* **Linux/macOS:** Start the app with `nohup` or a process manager so it keeps running after you close the terminal:

  ```bash
  nohup python -m random_bg.app >/tmp/randombg.log 2>&1 &
  ```

  The `nohup` command detaches the process from the terminal and writes output to `/tmp/randombg.log`.

## Set up autostart (systemd, Linux)

1. Adjust `WorkingDirectory` and, if you use a virtual environment, the `Environment` line in `autostart/randombg.service`.
2. Copy the file into your user systemd directory and reload the configuration:

   ```bash
   mkdir -p ~/.config/systemd/user
   cp autostart/randombg.service ~/.config/systemd/user/
   systemctl --user daemon-reload
   systemctl --user enable --now randombg.service
   ```

3. After a reboot, the tray starts automatically; stop it with `systemctl --user stop randombg.service`.

## Autostart on Windows

1. Run the PowerShell script `autostart/install-randombg-startup.ps1` on the target system. It creates a shortcut in the Startup folder that launches the bundled `start-randombg-windows.bat` (default path: `C:\\RandomBG`).
2. Alternatively, manually create a shortcut that runs `pythonw.exe -m random_bg.app` (adjust the path to `pythonw.exe`/your virtual environment if needed) and place it in the Startup folder (`shell:startup` in the Run dialog). At the next login, the app will start without showing a terminal.
