# RandomBG

Python-Tray-App, die den Desktop-Hintergrund in einem festen Zeitintervall wechselt.

## Installation

```bash
python -m venv .venv
.venv\\Scripts\\activate
pip install -r requirements.txt
```

## Nutzung

```bash
python -m random_bg.app
```

* Das Tray-Icon erscheint und wechselt die Hintergründe automatisch.
* Über "Einstellungen" können Ordner und Intervall (Sekunden) angepasst werden.
* "Nächstes Hintergrundbild" setzt sofort das nächste Bild aus dem ausgewählten Ordner.
* Konfiguration wird in `~/.random_bg_config.json` gespeichert.

## Im Hintergrund ohne Terminal laufen lassen

* **Windows:** Verwende `pythonw.exe -m random_bg.app`, damit kein Konsolenfenster geöffnet wird. Das Tray-Icon bleibt trotzdem sichtbar.
* **Linux/macOS:** Starte die App mit `nohup` oder über einen Prozess-Manager, damit sie weiterläuft, wenn das Terminal geschlossen wird:

  ```bash
  nohup python -m random_bg.app >/tmp/randombg.log 2>&1 &
  ```

  Das `nohup`-Kommando trennt den Prozess vom Terminal, die Ausgabe landet in `/tmp/randombg.log`.

## Autostart einrichten (systemd, Linux)

1. Passe den `WorkingDirectory` und (falls du ein virtuelles Environment nutzt) die `Environment`-Zeile in `autostart/randombg.service` an.
2. Kopiere die Datei in dein Benutzer-Systemd-Verzeichnis und lade die Konfiguration neu:

   ```bash
   mkdir -p ~/.config/systemd/user
   cp autostart/randombg.service ~/.config/systemd/user/
   systemctl --user daemon-reload
   systemctl --user enable --now randombg.service
   ```

3. Nach einem Reboot startet der Tray automatisch; stoppen kannst du ihn mit `systemctl --user stop randombg.service`.

## Autostart unter Windows

### Variante 1: Verknüpfung

1. Erstelle eine Verknüpfung, die `pythonw.exe -m random_bg.app` ausführt (ggf. den Pfad zu `pythonw.exe`/dem virtuellen Environment anpassen).
2. Lege die Verknüpfung im Autostart-Ordner ab (`shell:startup` im Ausführen-Dialog). Beim nächsten Login startet die App ohne sichtbares Terminal.

### Variante 2: Startup-Script (Beispiel für `C:\RandomBG`)

1. Passe bei Bedarf `autostart/start-randombg-windows.bat` an (Wurzelpfad ist bereits `C:\RandomBG`).
2. Lege eine Verknüpfung zu dieser `.bat`-Datei im Autostart-Ordner ab (`shell:startup`).
3. Beim Login startet Windows das Batch-Script, wechselt in `C:\RandomBG` und ruft `pythonw.exe -m random_bg.app` auf (bevorzugt aus `.venv\Scripts\pythonw.exe`, falls vorhanden).
