# Thermo-Hygrograph

Misst ein Jahr lang jede Stunde Temperatur und Luftfeuchtigkeit, zum Beispiel in einem feuchten Schulhaus oder einer Bibliothek. Die Werte landen als CSV-Datei auf dem Mikrocontroller.

## Hardware

- ESP32-S3-N16R8 Dev-Board (16 MB Flash) mit MicroPython 1.19.1
- Sensor AOSONG AM2302 (= DHT22)
- Widerstand 4,7 kΩ bis 10 kΩ (Pull-up)
- USB-Netzteil für den Dauerbetrieb

## Verkabelung

Sensor mit dem Gitter nach vorne, Beine nach unten, Beine von links nach rechts:

| Sensor-Bein | Funktion | ESP32-S3 |
|---|---|---|
| 1 | VCC  | 3V3 |
| 2 | DATA | GPIO 4 |
| 3 | –    | frei |
| 4 | GND  | GND |

Der Widerstand kommt zwischen Bein 1 (VCC) und Bein 2 (DATA).

Pin 4 ist frei. Diese Pins sind auf dem Board ungeeignet: 0, 3, 45, 46 (Boot-Pins), 19, 20 (USB), 35 bis 37 (PSRAM) und 48 (RGB-LED).

## Software

`main.py` läuft automatisch, sobald das Board Strom hat:

- Beim Start und danach jede Stunde misst es dreimal und speichert den Mittelwert.
- Jede Messung ist eine Zeile in `/messdaten.csv`:
  `zeit_utc,laufzeit_min,temperatur_c,luftfeuchte_pct`
- Jeder Neustart erzeugt eine Zeile `# Neustart …`.
- Die LED blinkt kurz blau beim Start, grün nach jeder Messung und rot bei einem Messfehler.

Speicherbedarf: etwa 45 Byte pro Messung, also rund 400 KB pro Jahr. Frei sind etwa 6 MB.

### Uhrzeit

Das Board hat keine Uhr mit Batterie. Die Zeit (UTC) kommt aus einer dieser Quellen:

1. **Vom PC:** `./board.sh zeit` oder `./board.sh aufspielen`. Die Zeit übersteht einen Reset, aber keinen Stromausfall.
2. **Per WLAN (NTP):** Wenn `secrets.py` auf dem Board liegt. Die Uhr wird beim Start und einmal am Tag nachgestellt.

Ist die Zeit unbekannt, steht in der CSV `unbekannt`. Die Spalte `laufzeit_min` (Minuten seit dem letzten Neustart) erlaubt es, die Zeit nachträglich zu rekonstruieren.

## Bedienung vom PC

Voraussetzung: `pip install mpremote`. Das Board ist per USB angeschlossen.

```bash
./board.sh aufspielen   # main.py (und ggf. secrets.py) aufs Board, Uhr stellen
./board.sh zeit         # nur Uhr stellen
./board.sh auslesen     # CSV nach daten/messdaten_<datum>.csv kopieren
./board.sh live         # Ausgabe des Boards live ansehen (Ende: Ctrl-X)
./board.sh loeschen     # Messdaten auf dem Board löschen
```

Jeder Befehl unterbricht das Messprogramm kurz und startet es danach neu.

## WLAN (optional)

`secrets.example.py` nach `secrets.py` kopieren, die WLAN-Daten eintragen und dann `./board.sh aufspielen` ausführen. Das funktioniert nur mit WPA2-Personal, also einem normalen WLAN mit Passwort. Mit eduroam oder WPA2-Enterprise und mit Anmeldeseiten im Browser klappt es nicht.

Ein Upload der Messwerte (zum Beispiel in ein Google Sheet oder zu ThingSpeak) ist noch nicht eingebaut.
