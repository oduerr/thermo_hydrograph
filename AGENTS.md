# AGENTS.md

Hinweise für KI-Agenten, die an diesem Projekt arbeiten. Was das Projekt tut und wie es verkabelt ist, steht im `README.md`. Hier steht nur das, was man nicht aus dem Code ablesen kann.

## Kontext

- Ein Messgerät für eine Schule (Bibliothek, feuchtes Gebäude): ein Jahr lang stündlich Temperatur und Luftfeuchte messen.
- Die Nutzer sind Lehrkräfte, keine Elektronik-Profis. Erklärungen auf Deutsch, Schritt für Schritt, mit konkreten Pin-Namen.
- Code-Kommentare und Bezeichner sind deutsch und in `.py`-Dateien ohne Umlaute geschrieben (`ue` statt `ü`). Ausnahme: das HTML in `web.py`.
- Das Repository ist öffentlich (github.com/oduerr/thermo_hydrograph). `secrets.py` enthält das Hotspot-Passwort und darf nie eingecheckt werden. Es steht in `.gitignore`.

## Hardware

- **Board:** ESP32-S3-N16R8, Typ „YD-ESP32-S3“, mit nativem USB. Am Mac erscheint es als `/dev/cu.usbmodem1234561` (VID 0x303A).
- **Firmware:** MicroPython 1.19.1 (2022). Neuere APIs fehlen eventuell.
- **Pins:**
  - Sensor DHT22/AM2302 an GPIO 4.
  - LCD (I²C-Adresse 0x27) an GPIO 8 (SDA) und GPIO 9 (SCL).
  - RGB-LED an GPIO 48.
  - Ungeeignet sind 0, 3, 45 und 46 (Boot-Pins), 19 und 20 (USB) sowie 35 bis 37 (PSRAM).
- **5Vin ist nur ein Eingang.** Der Pin gibt erst Spannung aus, wenn die Lötbrücke „IN-OUT“ geschlossen ist. Das LCD läuft deshalb an 3V3, mit blasser Schrift.

## Mit dem Board arbeiten

- Werkzeug ist `mpremote`. Es liegt in keiner globalen Installation, also bei Bedarf eine venv anlegen und `MPREMOTE=<pfad>` für `board.sh` setzen.
- **Jedes `mpremote exec`/`fs` unterbricht `main.py`.** Danach `mpremote reset` ausführen, nicht `soft-reset`: Nach `soft-reset` bleibt das Board im Raw-REPL, und `main.py` läuft nicht. `board.sh` erledigt das.
- **Kein `import main` in `exec`.** Das startet die Endlosschleife ein zweites Mal und schreibt falsche Neustart-Zeilen in die CSV.
- Eine Unterbrechung hinterlässt eine Zeile `# Neustart` in `messdaten.csv`. Das ist harmlos, aber unnötige Unterbrechungen vermeiden, sobald das Gerät im Einsatz ist.
- **I²C nur mit `SoftI2C(..., timeout=2000)` scannen.** Ein Hardware-I²C-Scan bei falscher Verkabelung hat das Board komplett aufgehängt. Dann hilft nur der RST-Knopf, und dafür muss der Nutzer gefragt werden.
- Die Ausgabe des Boards lässt sich passiv mit pyserial mitlesen. Das unterbricht `main.py` nicht.
- Die Uhr (RTC) übersteht `mpremote reset` und den RST-Knopf, aber keinen Stromausfall. MicroPython zählt die Zeit ab 2000-01-01, nicht ab 1970 (Differenz: 946684800 s).
- Das LCD wird nur beim Start gesucht. Wird es später eingesteckt oder neu mit Strom versorgt, muss das Board neu gestartet werden.
- Der DHT22 darf höchstens alle 2 s abgefragt werden. Einzelne Lesefehler (`OSError 116`) sind normal.

## Hotspot und Webseite

- Den Webserver kann man vom Mac aus nicht testen: Dafür müsste der Mac ins Board-WLAN wechseln, und die Verbindung zum Agenten würde abbrechen. Stattdessen den Nutzer bitten, mit dem Handy zu testen, und dabei die Ausgabe des Boards passiv mitlesen. `web.py` gibt jede Anfrage als `Web: <pfad>` aus.
- Chrome auf Android erreicht die Seite nicht. Die Anfrage kommt gar nicht am Board an (https-Upgrade oder mobile Daten). Mit Opera funktioniert sie. Das ist kein Fehler im Server.
- Der Server läuft im selben Thread wie die Messung, in `Server.warten()` zwischen den Display-Aktualisierungen. Jede Anfrage muss schnell erledigt sein, große Dateien werden in Blöcken gestreamt.

## Daten

- `messdaten.csv` auf dem Board. Zeit in UTC, Spalte `laufzeit_min` zur Rekonstruktion, wenn die Zeit unbekannt ist. Zeilen mit `#` sind Ereignisse: Neustart, Uhr gestellt.
- Ausgelesene Daten landen lokal in `daten/`. Das ist keine Testablage. Testdaten nicht committen.
