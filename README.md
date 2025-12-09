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
