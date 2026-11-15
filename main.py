# Thermo-Hygrograph: misst Temperatur und Luftfeuchtigkeit mit einem
# AM2302 (DHT22) an einem ESP32-S3.
#  - Jede Stunde: Mittelwert aus 3 Messungen -> /messdaten.csv (Zeit in UTC)
#  - Alle 5 Sekunden: aktueller Wert auf dem LCD (16x2, I2C), Ortszeit Berlin
#
#  - Optional: eigener WLAN-Hotspot mit Webseite (siehe web.py). Name und
#    Passwort stehen in secrets.py (AP_NAME, AP_PASSWORT). Beim Aufruf der
#    Seite stellt das Handy die Uhr des Boards.

import time
import dht
import machine
from machine import Pin, SoftI2C
from neopixel import NeoPixel

DATEI = "/messdaten.csv"
SENSOR_PIN = 4
LED_PIN = 48
LCD_SDA, LCD_SCL, LCD_ADRESSE = 8, 9, 0x27
INTERVALL_S = 3600          # Speichern: 1 Stunde
ANZEIGE_S = 5               # Display: alle 5 Sekunden
MESSUNGEN_PRO_WERT = 3      # Mittelwert aus 3 Einzelmessungen

sensor = dht.DHT22(Pin(SENSOR_PIN))
led = NeoPixel(Pin(LED_PIN, Pin.OUT), 1)
anzahl = 0                  # gespeicherte Messungen in der Datei


def lcd_starten():
    try:
        from lcd import LCD
        i2c = SoftI2C(sda=Pin(LCD_SDA), scl=Pin(LCD_SCL), freq=100000, timeout=2000)
        if LCD_ADRESSE in i2c.scan():
            return LCD(i2c, LCD_ADRESSE)
    except Exception as e:
        print("Kein Display:", e)
    return None


lcd = lcd_starten()


def anzeigen(zeile1, zeile2):
    global lcd
    if lcd is None:
        return
    try:
        lcd.zeile(0, zeile1)
        lcd.zeile(1, zeile2)
    except Exception as e:
        print("Display-Fehler:", e)   # Messung laeuft trotzdem weiter


def blink(farbe, dauer_ms=150):
    led[0] = farbe
    led.write()
    time.sleep_ms(dauer_ms)
    led[0] = (0, 0, 0)
    led.write()


def zeit_bekannt():
    return time.localtime()[0] >= 2024


def zeitstempel():
    if not zeit_bekannt():
        return "unbekannt"
    j, mo, t, h, mi, s = time.localtime()[:6]
    return "%04d-%02d-%02dT%02d:%02d:%02dZ" % (j, mo, t, h, mi, s)


def _letzter_sonntag(jahr, monat):
    # Sekunden (UTC) fuer 01:00 am letzten Sonntag des Monats (Maerz/Oktober)
    wt = time.localtime(time.mktime((jahr, monat, 31, 1, 0, 0, 0, 0)))[6]  # 0=Mo
    return time.mktime((jahr, monat, 31 - (wt + 1) % 7, 1, 0, 0, 0, 0))


def ortszeit():
    """Uhrzeit fuer Deutschland (MEZ/MESZ) als 'HH:MM', oder '--:--'."""
    if not zeit_bekannt():
        return "--:--"
    jetzt = time.time()
    jahr = time.localtime(jetzt)[0]
    sommer = _letzter_sonntag(jahr, 3) <= jetzt < _letzter_sonntag(jahr, 10)
    h, mi = time.localtime(jetzt + 3600 * (2 if sommer else 1))[3:5]
    return "%02d:%02d" % (h, mi)


# time.ticks_ms() springt nach 2^30 ms (12,4 Tage) auf 0 zurueck, und
# ticks_diff() stimmt nur fuer Abstaende bis 6,2 Tage. Die Laufzeit wird
# deshalb in kleinen Schritten aufsummiert statt gegen den Startwert gerechnet.
_lz_ms = 0
_lz_ticks = time.ticks_ms()


def laufzeit_min():
    """Minuten seit dem Start. Muss mindestens alle paar Tage aufgerufen werden."""
    global _lz_ms, _lz_ticks
    jetzt = time.ticks_ms()
    _lz_ms += time.ticks_diff(jetzt, _lz_ticks)
    _lz_ticks = jetzt
    return _lz_ms // 60000


def web_starten():
    """Startet Hotspot und Webserver, wenn secrets.py vorhanden ist."""
    try:
        import secrets
        import web
    except ImportError:
        print("Kein secrets.py: ohne Hotspot")
        return None
    try:
        ip = web.hotspot_starten(secrets.AP_NAME, secrets.AP_PASSWORT)
        print("Hotspot", secrets.AP_NAME, "unter http://%s" % ip)
        return web.Server(web_status, DATEI, uhr_gestellt)
    except Exception as e:
        print("Hotspot-Fehler:", e)
        return None


def uhr_gestellt(alt):
    vorher = "unbekannt"
    if alt >= 757382400:                    # 2024-01-01 in MicroPython-Zeit
        vorher = "%04d-%02d-%02dT%02d:%02d:%02dZ" % time.localtime(alt)[:6]
    # Mit Laufzeit: so ist die Zeile ein Anker, um Zeilen mit "unbekannt"
    # nachtraeglich zu datieren.
    zeile_schreiben("# Uhr vom Handy gestellt %s (vorher %s) laufzeit_min %d"
                    % (zeitstempel(), vorher, laufzeit_min()))


def web_status():
    w = _letzter
    return {"t": w[0] if w else None, "f": w[1] if w else None,
            "anzahl": anzahl, "zeit": zeitstempel(),
            "laufzeit_min": laufzeit_min()}


def einzelmessung():
    try:
        sensor.measure()
        return sensor.temperature(), sensor.humidity()
    except OSError:
        return None


def messen():
    """Mittelwert aus mehreren Messungen. Gibt (temp, feuchte) oder None zurueck."""
    temps, feuchten = [], []
    for _ in range(MESSUNGEN_PRO_WERT * 2):   # bis zu doppelt so viele Versuche
        w = einzelmessung()
        if w:
            temps.append(w[0])
            feuchten.append(w[1])
        if len(temps) >= MESSUNGEN_PRO_WERT:
            break
        time.sleep(2.5)                      # DHT22: max. 1 Messung alle 2 s
    if not temps:
        return None
    return sum(temps) / len(temps), sum(feuchten) / len(feuchten)


def datei_vorbereiten():
    global anzahl
    try:
        with open(DATEI) as f:
            for z in f:
                if z[0] in "0123456789u":
                    anzahl += 1
    except OSError:
        with open(DATEI, "w") as f:
            f.write("zeit_utc,laufzeit_min,temperatur_c,luftfeuchte_pct\n")


def zeile_schreiben(text):
    with open(DATEI, "a") as f:
        f.write(text + "\n")


def speichern():
    global anzahl
    lz = laufzeit_min()
    wert = messen()
    if wert is None:
        zeile_schreiben("%s,%d,," % (zeitstempel(), lz))
        print(zeitstempel(), "Messfehler")
        blink((40, 0, 0))                    # rot: Messfehler
    else:
        t, rh = wert
        zeile_schreiben("%s,%d,%.1f,%.1f" % (zeitstempel(), lz, t, rh))
        print(zeitstempel(), "T=%.1f C  RH=%.1f %%" % (t, rh))
        blink((0, 40, 0))                    # gruen: Messung ok
    anzahl += 1
    return wert


_letzter = None
_fehler = 0


def anzeige_aktualisieren(wert):
    global _letzter, _fehler
    if wert is None:
        _fehler += 1
        wert = _letzter if _fehler < 4 else None   # einzelne Lesefehler ignorieren
    else:
        _letzter, _fehler = wert, 0
    if wert is None:
        zeile1 = "Sensorfehler!"
    else:
        # \xdf ist das Grad-Zeichen im LCD-Zeichensatz
        zeile1 = "%5.1f\xdfC %5.1f%%rF" % wert
    anzeigen(zeile1, "%s   Nr.%5d" % (ortszeit(), anzahl))


def main():
    anzeigen("Thermo-Hygro", "startet ...")
    datei_vorbereiten()
    blink((0, 0, 40), 500)                   # blau: Start
    server = web_starten()
    zeile_schreiben("# Neustart %s" % zeitstempel())
    naechste = time.ticks_ms()
    while True:
        # Takt ueber die interne Laufzeit, damit ein Uhr-Nachstellen nicht stoert
        if time.ticks_diff(naechste, time.ticks_ms()) <= 0:
            anzeige_aktualisieren(speichern())
            naechste = time.ticks_add(naechste, INTERVALL_S * 1000)
        else:
            anzeige_aktualisieren(einzelmessung())
        if server:
            server.warten(ANZEIGE_S * 1000)  # Webseite bedienen, bis Display dran ist
        else:
            time.sleep(ANZEIGE_S)


# Auffangnetz fuer den Dauerbetrieb: Ein unerwarteter Fehler wuerde das
# Programm beenden, und das Geraet wuerde unbemerkt nicht mehr messen.
# Stattdessen Fehler in die CSV schreiben und neu starten. Die Pause begrenzt
# die Zahl der Zeilen, falls der Fehler bei jedem Start wieder auftritt.
# Ctrl-C (mpremote) ist keine Exception und beendet das Programm wie bisher.
try:
    main()
except Exception as e:
    print("Fehler:", repr(e))
    try:
        zeile_schreiben("# Fehler %s %s" % (zeitstempel(), repr(e)))
    except Exception:
        pass
    anzeigen("Fehler!", "Neustart in 60s")
    time.sleep(60)
    machine.reset()
