# Thermo-Hygrograph: misst stuendlich Temperatur und Luftfeuchtigkeit
# mit einem AM2302 (DHT22) an einem ESP32-S3 und speichert die Werte
# in /messdaten.csv auf dem Board.
#
# Optional: Wenn eine Datei secrets.py mit WLAN_SSID und WLAN_PASSWORT
# auf dem Board liegt, holt sich das Board die Uhrzeit per NTP.

import time
import dht
import machine
from machine import Pin
from neopixel import NeoPixel

DATEI = "/messdaten.csv"
SENSOR_PIN = 4
LED_PIN = 48
INTERVALL_S = 3600          # 1 Stunde
MESSUNGEN_PRO_WERT = 3      # Mittelwert aus 3 Einzelmessungen

sensor = dht.DHT22(Pin(SENSOR_PIN))
led = NeoPixel(Pin(LED_PIN, Pin.OUT), 1)
rtc = machine.RTC()


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


def wlan_zeit_holen():
    """Versucht, per WLAN die Uhrzeit (UTC) zu holen. Ohne secrets.py: nichts tun."""
    try:
        import secrets
    except ImportError:
        return False
    try:
        import network
        import ntptime
        wlan = network.WLAN(network.STA_IF)
        wlan.active(True)
        if not wlan.isconnected():
            wlan.connect(secrets.WLAN_SSID, secrets.WLAN_PASSWORT)
            for _ in range(30):
                if wlan.isconnected():
                    break
                time.sleep(1)
        if wlan.isconnected():
            ntptime.settime()
            return True
    except Exception as e:
        print("WLAN/NTP Fehler:", e)
    return False


def messen():
    """Mittelwert aus mehreren Messungen. Gibt (temp, feuchte) oder None zurueck."""
    temps, feuchten = [], []
    for _ in range(MESSUNGEN_PRO_WERT * 2):   # bis zu doppelt so viele Versuche
        try:
            sensor.measure()
            temps.append(sensor.temperature())
            feuchten.append(sensor.humidity())
        except OSError:
            pass
        if len(temps) >= MESSUNGEN_PRO_WERT:
            break
        time.sleep(2.5)                      # DHT22: max. 1 Messung alle 2 s
    if not temps:
        return None
    return sum(temps) / len(temps), sum(feuchten) / len(feuchten)


def datei_vorbereiten():
    try:
        open(DATEI).close()
    except OSError:
        with open(DATEI, "w") as f:
            f.write("zeit_utc,laufzeit_min,temperatur_c,luftfeuchte_pct\n")


def zeile_schreiben(text):
    with open(DATEI, "a") as f:
        f.write(text + "\n")


def main():
    datei_vorbereiten()
    blink((0, 0, 40), 500)                   # blau: Start
    wlan_zeit_holen()
    zeile_schreiben("# Neustart %s" % zeitstempel())
    start = time.ticks_ms()
    naechste = start
    while True:
        laufzeit_min = time.ticks_diff(time.ticks_ms(), start) // 60000
        wert = messen()
        if wert is None:
            zeile_schreiben("%s,%d,," % (zeitstempel(), laufzeit_min))
            print(zeitstempel(), "Messfehler")
            blink((40, 0, 0))                # rot: Messfehler
        else:
            t, rh = wert
            zeile_schreiben("%s,%d,%.1f,%.1f" % (zeitstempel(), laufzeit_min, t, rh))
            print(zeitstempel(), "T=%.1f C  RH=%.1f %%" % (t, rh))
            blink((0, 40, 0))                # gruen: Messung ok
        # Einmal am Tag die Uhrzeit nachstellen (falls WLAN vorhanden)
        if laufzeit_min // 60 % 24 == 23:
            wlan_zeit_holen()
        # Takt ueber die interne Laufzeit, damit ein Uhr-Nachstellen nicht stoert
        naechste = time.ticks_add(naechste, INTERVALL_S * 1000)
        while time.ticks_diff(naechste, time.ticks_ms()) > 0:
            time.sleep(1)


main()
