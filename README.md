# Thermo-Hygrograph

Misst ein Jahr lang jede Stunde Temperatur und Luftfeuchtigkeit, zum Beispiel in einem feuchten Schulhaus oder einer Bibliothek. Die Werte landen als CSV-Datei auf dem Mikrocontroller.

## Hardware

- ESP32-S3-N16R8 Dev-Board (16 MB Flash) mit MicroPython 1.19.1
- Sensor AOSONG AM2302 (= DHT22)
- Widerstand 4,7 kΩ bis 10 kΩ (Pull-up)
- optional: LCD 16 × 2 mit I²C-Adapter (PCF8574T, Adresse 0x27)
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

Display (optional):

| Display | ESP32-S3 |
|---|---|
| GND | GND |
| VCC | 3V3 |
| SDA | GPIO 8 |
| SCL | GPIO 9 |

Ist die Schrift nicht zu sehen, den Kontrast am blauen Drehregler des Adapters einstellen. Den Regler langsam über den ganzen Bereich drehen, die richtige Stellung ist schmal.

Das Display ist eigentlich für 5 V gebaut. Mit 3,3 V funktioniert es, aber die Schrift ist blass und am besten schräg von der Seite lesbar. Für 5 V reicht es nicht, das Kabel an den Pin **5Vin** zu stecken: Dieser Pin ist auf dem Board nur ein Eingang. Er gibt erst Spannung aus, wenn die Lötbrücke **IN-OUT** auf der Platine geschlossen ist. Dann liegen auch SDA und SCL über die Widerstände des Adapters auf 5 V. Für den Dauerbetrieb ist deshalb ein Pegelwandler oder ein OLED-Display für 3,3 V die sauberere Lösung.

Nach dem Anstecken des Displays muss das Board neu gestartet werden. Das Programm sucht das Display nur beim Start.

Pin 4 ist frei. Diese Pins sind auf dem Board ungeeignet: 0, 3, 45, 46 (Boot-Pins), 19, 20 (USB), 35 bis 37 (PSRAM) und 48 (RGB-LED).

## Software

`main.py` läuft automatisch, sobald das Board Strom hat:

- Beim Start und danach jede Stunde misst es dreimal und speichert den Mittelwert.
- Jede Messung ist eine Zeile in `/messdaten.csv`:
  `zeit_utc,laufzeit_min,temperatur_c,luftfeuchte_pct`
- Jeder Neustart erzeugt eine Zeile `# Neustart …`.
- Alle 5 Sekunden zeigt das Display den aktuellen Wert, die Ortszeit (MEZ/MESZ) und die Zahl der gespeicherten Messungen. Ohne Display läuft das Programm genauso.
- Die LED blinkt kurz blau beim Start, grün nach jeder Messung und rot bei einem Messfehler.

Speicherbedarf: etwa 45 Byte pro Messung, also rund 400 KB pro Jahr. Frei sind etwa 6 MB.

### Uhrzeit

Das Board hat keine Uhr mit Batterie. Die Zeit (UTC) kommt aus einer dieser Quellen:

1. **Vom PC:** `./board.sh zeit` oder `./board.sh aufspielen`. Die Zeit übersteht einen Reset, aber keinen Stromausfall.
2. **Vom Handy:** beim Aufruf der Webseite (siehe unten).

Ist die Zeit unbekannt, steht in der CSV `unbekannt`. Die Spalte `laufzeit_min` (Minuten seit dem letzten Neustart) erlaubt es, die Zeit nachträglich zu rekonstruieren.

## Bedienung vom PC

Voraussetzung: `pip install mpremote`. Das Board ist per USB angeschlossen.

```bash
./board.sh aufspielen   # Programm (und ggf. secrets.py) aufs Board, Uhr stellen
./board.sh zeit         # nur Uhr stellen
./board.sh auslesen     # CSV nach daten/messdaten_<datum>.csv kopieren
./board.sh live         # Ausgabe des Boards live ansehen (Ende: Ctrl-X)
./board.sh loeschen     # Messdaten auf dem Board löschen
```

Jeder Befehl unterbricht das Messprogramm kurz und startet es danach neu.

## WLAN-Hotspot und Webseite

Das Board öffnet ein eigenes WLAN. Über das Handy kann man damit die Daten abrufen, ohne Laptop und ohne Schul-WLAN.

1. `secrets.example.py` nach `secrets.py` kopieren, Netzname und Passwort (mindestens 8 Zeichen) eintragen und `./board.sh aufspielen` ausführen. `secrets.py` wird nicht eingecheckt.
2. Das Handy mit dem WLAN verbinden. Die Meldung „Kein Internet“ mit „Verbunden bleiben“ bestätigen.
3. Im Browser `http://192.168.4.1` öffnen.

Die Seite zeigt die aktuellen Werte und den Verlauf und bietet die CSV zum Herunterladen an. Beim Öffnen schickt das Handy seine Uhrzeit mit. Weicht die Uhr des Boards um mehr als 30 Sekunden ab, wird sie gestellt. In der CSV steht dann die Zeile `# Uhr vom Handy gestellt …`. Nach einem Stromausfall reicht deshalb ein Besuch mit dem Handy, und die Uhr stimmt wieder.

Die Reichweite im Gebäude liegt bei etwa 10 bis 30 m.

**Chrome auf Android** erreicht die Seite oft nicht. Es versucht https oder schickt die Anfrage über die mobilen Daten. Abhilfe: Opera oder Firefox verwenden, oder in Chrome „Immer sichere Verbindungen verwenden“ ausschalten und die mobilen Daten deaktivieren.
