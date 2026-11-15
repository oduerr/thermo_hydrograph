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
                         │    - Uhr mit Batterie (gibt die Zeit an A und C weiter)
                         │  Funk (ESP-NOW), durch 1 Decke
  unteres Stockwerk    [ A ]  Messgerät
```

Weil B in der Mitte steht, muss jedes Funksignal nur **eine Decke** überwinden. Eine Weiterleitung über ein anderes Gerät ist dann sehr wahrscheinlich nicht nötig.

## Wie es funktioniert

**Funk:** Die Geräte nutzen **ESP-NOW**. Damit tauschen ESP32-Boards direkt Daten aus, ohne Router, ohne Schul-WLAN und ohne Internet. Pro Messung werden nur wenige Bytes gesendet.

**Ablauf jede Stunde:**
1. A, B und C messen und speichern ihren Wert **lokal**, jeweils in der eigenen CSV-Datei.
2. A und C senden ihren Wert an B.
3. B bestätigt den Empfang und schickt dabei die aktuelle Uhrzeit zurück. So bleiben alle Uhren richtig.
4. B schreibt alle Werte in eine gemeinsame Datei mit einer zusätzlichen Spalte `standort` (A, B oder C).

**Abruf:** Das Handy verbindet sich mit dem Hotspot von B, wie heute schon mit `Organon-Metrikon-Alpha`. Die Webseite zeigt alle drei Stockwerke nebeneinander, den Verlauf und einen Download der gemeinsamen CSV.

**Ausfallsicherheit:**
- Fällt der Funk aus, speichern A und C weiter lokal. Die Daten lassen sich später per USB auslesen und nachtragen.
- Erreicht eine Meldung B nicht, schickt das Gerät sie bei der nächsten Gelegenheit nach.
- B zeigt auf dem Display und der Webseite an, wann es von A und C zuletzt etwas gehört hat. Ein Ausfall fällt so schnell auf.
- Nach einem Stromausfall hat B die Uhrzeit noch (Batterie-Uhr) und verteilt sie wieder.

## Hardware

| Teil | Wofür | Anzahl | ca. Preis/Stück |
|---|---|---|---|
| ESP32-S3 DevKit N16R8 | Board, wie das jetzige | 3 (1 vorhanden) | 10 € |
| Sensirion **SHT45** auf Breakout-Platine (I²C) | Temperatur + Luftfeuchte | 3 | 8–15 € |
| DS3231 RTC-Modul mit Knopfzelle | Uhr mit Batterie, nur B | 1 | 3 € |
| OLED-Display 1,3" (SH1106) oder 0,96" (SSD1306), I²C | Anzeige, nur B | 1 | 5 € |
| USB-Netzteil 5 V / 1 A + Kabel | Dauerbetrieb | 3 | 8 € |
| Gehäuse mit Lüftungsschlitzen | Schutz | 3 | 5 € |
| Steckbrett/Lochraster, Kabel | Aufbau | – | 10 € |

**Summe:** etwa **100–120 €** für alle drei Stockwerke.

Die Preise sind grobe Richtwerte aus dem Online-Versand.

### Warum ein besserer Sensor

Für alte Bücher kommt es bei der Luftfeuchte auf wenige Prozent an. Ein Zielbereich von etwa 45–55 % ist üblich, ab etwa 65 % droht Schimmel.

| Sensor | Genauigkeit Luftfeuchte | Bemerkung |
|---|---|---|
| DHT22 / AM2302 (jetzt im Einsatz) | ±2–5 % | wird über die Jahre und bei hoher Feuchte ungenauer |
| **SHT45** | **±1 %** | verbreitet in der Klimaüberwachung, geringe Drift |

Der SHT45 hängt am selben I²C-Bus wie Display und Uhr. Dafür ist kein zusätzlicher Pin nötig.

### Warum OLED statt des jetzigen LCDs

Das jetzige 16×2-LCD ist für 5 V gebaut und an 3,3 V nur blass lesbar. Ein OLED-Display läuft direkt an 3,3 V, ist kontrastreich und hat Platz für drei Stockwerke.

## Ausbaustufen

| Stufe | Inhalt | Stand |
|---|---|---|
| 1 | Ein Gerät: Messung, CSV, LCD, Hotspot mit Webseite | **fertig** |
| 2 | **Funktest durch die Decken** mit einem zweiten Board | als Nächstes |
| 3 | Hardware für alle drei Geräte beschaffen (SHT45, RTC, OLED) | nach Stufe 2 |
| 4 | Software: ESP-NOW-Übertragung A/C → B, gemeinsame CSV, Webseite für drei Stockwerke | |
| 5 | Aufstellen, eine Woche Probebetrieb, dann Messjahr starten | |

### Stufe 2: Funktest

Mit dem Kauf der restlichen Teile warten, bis klar ist, dass der Funk durch die Decken reicht:

1. Ein zweites ESP32-Board beschaffen.
2. Ein Board an den geplanten Platz von **B** stellen, das andere nacheinander an die Plätze von **A** und **C**.
3. Ein Testprogramm sendet alle paar Sekunden ein Paket. Die Signalstärke und der Anteil angekommener Pakete werden angezeigt.
4. Ergebnis:
   - **Kommt fast alles an:** Aufbau wie oben.
   - **Kommt nur zeitweise etwas an:** Long-Range-Modus von ESP-NOW nutzen oder ein Board mit externer Antenne (ESP32-S3-DevKitC-**1U**).
   - **Kommt nichts an:** Standorte verschieben, z. B. näher ans Treppenhaus, oder über LoRa-Funk nachdenken.

## Offene Fragen

- Wo genau stehen A, B und C? Gibt es dort Steckdosen?
- Aus welchem Material sind die Decken (Holzbalken, Beton, Gewölbe)?
- Wer liest die Daten wie oft aus, und wer schaut nach den Geräten?
- Sollen die Werte zusätzlich ins Internet, z. B. über das Schul-WLAN, falls B dort Empfang hat?
- Gibt es Grenzwerte, bei denen jemand gewarnt werden soll (z. B. Luftfeuchte über 65 %)?
