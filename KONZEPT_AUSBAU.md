# Konzept: Klimamessung auf drei Stockwerken

Stand: November 2026 · Entwurf zur Abstimmung

## Ziel

Im Gebäude mit den alten Büchern sollen auf **drei Stockwerken** ein Jahr lang stündlich Temperatur und Luftfeuchte gemessen werden. Alle Werte sollen **an einem zugänglichen Ort** abrufbar sein, ohne in jedes Stockwerk gehen zu müssen.

## Aufbau

Das zugängliche Gerät **B** steht im **mittleren Stockwerk**. Die Geräte A (unten) und C (oben) funken ihre Werte zu B.

```
  oberes Stockwerk     [ C ]  Messgerät
                         │  Funk (ESP-NOW), durch 1 Decke
                         ▼
  mittleres Stockwerk  [ B ]  Messgerät + Zentrale
                         ▲    - sammelt die Werte von A, B und C
                         │    - Display mit allen drei Stockwerken
                         │    - WLAN-Hotspot fürs Handy
                         │    - Uhr mit Batterie (maßgebliche Zeit für die gemeinsame Datei)
                         │  Funk (ESP-NOW), durch 1 Decke
  unteres Stockwerk    [ A ]  Messgerät
```

Weil B in der Mitte steht, muss jedes Funksignal nur **eine Decke** überwinden. Eine Weiterleitung über ein anderes Gerät ist dann sehr wahrscheinlich nicht nötig.

## Wie es funktioniert

**Funk:** Die Geräte nutzen **ESP-NOW**. Damit tauschen ESP32-Boards direkt Daten aus, ohne Router, ohne Schul-WLAN und ohne Internet. Pro Messung werden nur wenige Bytes gesendet.

Funk und Hotspot von B laufen über dieselbe Antenne und damit auf demselben WLAN-Kanal. Der Kanal wird fest eingestellt (z. B. Kanal 1), und A und C senden auf genau diesem Kanal.

**Ablauf jede Stunde:**
1. A, B und C messen und speichern ihren Wert **lokal**, jeweils in der eigenen CSV-Datei.
2. A und C senden ihren Wert an B. Jede Meldung enthält den Standort (A oder C), eine **laufende Nummer** und das **Alter der Messung** in Sekunden.
3. B bestätigt den Empfang und schickt dabei die aktuelle Uhrzeit zurück. So bleiben alle Uhren richtig.
4. B schreibt alle Werte in eine gemeinsame Datei mit den zusätzlichen Spalten `standort` (A, B oder C) und `nr`. Den Zeitpunkt berechnet B aus seiner eigenen Uhr und dem Alter der Messung. Die gemeinsame Datei hängt damit nur von der Uhr von B ab.

**Abruf:** Das Handy verbindet sich mit dem Hotspot von B, wie heute schon mit `Organon-Metrikon-Alpha`. Die Webseite zeigt alle drei Stockwerke nebeneinander, den Verlauf und einen Download der gemeinsamen CSV.

**Ausfallsicherheit:**
- Fällt der Funk aus, speichern A und C weiter lokal. Die Daten lassen sich später per USB auslesen und nachtragen.
- Erreicht eine Meldung B nicht, schickt das Gerät sie bei der nächsten Gelegenheit nach. A und C merken sich dafür in einer kleinen Datei die Nummer der letzten bestätigten Messung, auch über einen Neustart hinweg. B erkennt an Standort und Nummer, wenn eine Meldung doppelt ankommt, und speichert sie nur einmal.
- Nachgeschickte Werte stehen in der gemeinsamen Datei nicht in zeitlicher Reihenfolge. Vor der Auswertung wird nach Zeit sortiert.
- B zeigt auf dem Display und der Webseite an, wann es von A und C zuletzt etwas gehört hat. Ein Ausfall fällt so schnell auf.
- Nach einem Stromausfall haben alle drei Geräte die Uhrzeit noch (Batterie-Uhr). Die lokalen Dateien von A und C bleiben damit auch dann datiert, wenn Strom und Funk gleichzeitig ausfallen.
- Ein unerwarteter Programmfehler führt zu einem Eintrag in der CSV und einem automatischen Neustart.

## Hardware

| Teil | Wofür | Anzahl | ca. Preis/Stück |
|---|---|---|---|
| ESP32-S3 DevKit N16R8 | Board, wie das jetzige | 3 (1 vorhanden) | 10 € |
| Sensirion **SHT45** auf Breakout-Platine (I²C) | Temperatur + Luftfeuchte | 3 | 8–15 € |
| DS3231 RTC-Modul mit Knopfzelle | Uhr mit Batterie | 3 | 3 € |
| Kabel 4-adrig, 20–30 cm | Sensor außerhalb des Gehäuses | 3 | 1 € |
| OLED-Display 1,3" (SH1106) oder 0,96" (SSD1306), I²C | Anzeige, nur B | 1 | 5 € |
| USB-Netzteil 5 V / 1 A + Kabel | Dauerbetrieb | 3 | 8 € |
| Gehäuse mit Lüftungsschlitzen | Schutz | 3 | 5 € |
| Steckbrett/Lochraster, Kabel | Aufbau | – | 10 € |

**Summe:** etwa **110–130 €** für alle drei Stockwerke.

Die Preise sind grobe Richtwerte aus dem Online-Versand.

### Warum ein besserer Sensor

Für alte Bücher kommt es bei der Luftfeuchte auf wenige Prozent an. Ein Zielbereich von etwa 45–55 % ist üblich, ab etwa 65 % droht Schimmel.

| Sensor | Genauigkeit Luftfeuchte | Bemerkung |
|---|---|---|
| DHT22 / AM2302 (jetzt im Einsatz) | ±2–5 % | wird über die Jahre und bei hoher Feuchte ungenauer |
| **SHT45** | **±1 %** | verbreitet in der Klimaüberwachung, geringe Drift |

Der SHT45 hängt am selben I²C-Bus wie Display und Uhr. Dafür ist kein zusätzlicher Pin nötig. Die Adressen kommen sich nicht in die Quere: SHT45 0x44, Uhr 0x68, OLED 0x3C.

### Sensor außerhalb des Gehäuses

Ein ESP32 mit eingeschaltetem WLAN wird warm. Sitzt der Sensor im selben Gehäuse, misst er die Wärme des Boards mit. Schon 1 °C zu viel am Sensor senkt die angezeigte Luftfeuchte um etwa 3 Prozentpunkte. Das ist mehr als der Unterschied zwischen DHT22 und SHT45.

Der Sensor hängt deshalb an einem **20–30 cm langen Kabel außerhalb des Gehäuses**, und zwar **unterhalb** des Boards, weil warme Luft nach oben steigt. Er soll frei in der Raumluft hängen, nicht an einer Außenwand, nicht über einer Heizung und nicht in der Sonne.

### Abgleich der drei Sensoren

Vor dem Aufstellen laufen alle drei Geräte **einige Tage nebeneinander** im selben Raum. Die Abweichungen zwischen den Sensoren werden notiert. Ohne diesen Abgleich lässt sich später nicht sagen, ob ein Unterschied zwischen den Stockwerken echt ist oder vom Sensor kommt.

### Warum OLED statt des jetzigen LCDs

Das jetzige 16×2-LCD ist für 5 V gebaut und an 3,3 V nur blass lesbar. Ein OLED-Display läuft direkt an 3,3 V, ist kontrastreich und hat Platz für drei Stockwerke.

Ein OLED, das ein Jahr lang ständig leuchtet, brennt ein und wird dunkler. Die Anzeige bleibt deshalb normalerweise **aus** und geht auf Knopfdruck für eine Minute an. Dafür reicht der Knopf **BOOT** auf dem Board (GPIO 0). Er darf nur nicht beim Einstecken des Stroms gedrückt sein.

## Ausbaustufen

| Stufe | Inhalt | Stand |
|---|---|---|
| 1 | Ein Gerät: Messung, CSV, LCD, Hotspot mit Webseite | **fertig** |
| 2 | **Firmware aktualisieren**, dann **Funktest durch die Decken** mit einem zweiten Board | als Nächstes |
| 3 | Hardware für alle drei Geräte beschaffen (SHT45, RTC, OLED) | nach Stufe 2 |
| 4 | Software: ESP-NOW-Übertragung A/C → B, gemeinsame CSV, Webseite für drei Stockwerke | |
| 5 | Abgleich der drei Sensoren nebeneinander, Aufstellen, eine Woche Probebetrieb, dann Messjahr starten | |

### Stufe 2: Firmware aktualisieren

Auf dem Board läuft MicroPython 1.19.1. Diese Version kennt **kein ESP-NOW**. Das Modul `espnow` gibt es erst ab Version 1.21.

1. Zuerst die Messdaten sichern: `./board.sh auslesen`. Das Aufspielen der Firmware kann die Dateien auf dem Board löschen.
2. Aktuelle MicroPython-Firmware für den ESP32-S3 aufspielen, auf beiden Boards dieselbe Version.
3. `./board.sh aufspielen` ausführen und prüfen, dass Messung, Display und Hotspot wie vorher laufen.

### Stufe 2: Funktest

Mit dem Kauf der restlichen Teile warten, bis klar ist, dass der Funk durch die Decken reicht:

1. Ein zweites ESP32-Board beschaffen.
2. Ein Board an den geplanten Platz von **B** stellen, das andere nacheinander an die Plätze von **A** und **C**.
3. Ein Testprogramm sendet alle paar Sekunden ein Paket. Die Signalstärke und der Anteil angekommener Pakete werden angezeigt.
4. Der Test läuft unter den Bedingungen des späteren Betriebs: Hotspot von B eingeschaltet, Boards im Gehäuse, über **mehrere Stunden** an einem normalen Schultag. Ein kurzer Test bei leerem Haus sagt wenig.
5. Ergebnis:
   - **Kommt fast alles an:** Aufbau wie oben.
   - **Kommt nur zeitweise etwas an:** ein Board mit externer Antenne (ESP32-S3-DevKitC-**1U**) verwenden. Der Long-Range-Modus von ESP-NOW ist nur die zweite Wahl: Handys können sich mit einem Hotspot im Long-Range-Modus nicht verbinden. Er dürfte bei B also nur für den Funk gelten, nicht für den Hotspot. Ob MicroPython das erlaubt, ist noch zu prüfen.
   - **Kommt nichts an:** Standorte verschieben, z. B. näher ans Treppenhaus, oder über LoRa-Funk nachdenken.

## Offene Fragen

- Wo genau stehen A, B und C? Gibt es dort Steckdosen?
- Aus welchem Material sind die Decken (Holzbalken, Beton, Gewölbe)?
- Wer liest die Daten wie oft aus, und wer schaut nach den Geräten?
- Sollen die Werte zusätzlich ins Internet, z. B. über das Schul-WLAN, falls B dort Empfang hat?
- Gibt es Grenzwerte, bei denen jemand gewarnt werden soll (z. B. Luftfeuchte über 65 %)?
