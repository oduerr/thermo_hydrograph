# Minimaler Treiber fuer ein HD44780-LCD (16x2) mit PCF8574-I2C-Adapter.
import time

_RS = 0x01
_EN = 0x04
_LICHT = 0x08


class LCD:
    def __init__(self, i2c, adresse=0x27, spalten=16, zeilen=2):
        self.i2c = i2c
        self.adr = adresse
        self.spalten = spalten
        self.zeilen = zeilen
        self.licht = _LICHT
        time.sleep_ms(50)
        # In den 4-Bit-Modus schalten (Ablauf laut HD44780-Datenblatt)
        for _ in range(3):
            self._nibble(0x30)
            time.sleep_ms(5)
        self._nibble(0x20)
        self._befehl(0x28)   # 4 Bit, 2 Zeilen, 5x8 Punkte
        self._befehl(0x0C)   # Anzeige an, kein Cursor
        self._befehl(0x06)   # Cursor nach rechts
        self.loeschen()

    def _schreiben(self, b):
        self.i2c.writeto(self.adr, bytes([b | self.licht]))

    def _nibble(self, b):
        self._schreiben(b)
        self._schreiben(b | _EN)
        self._schreiben(b)

    def _byte(self, b, rs):
        self._nibble((b & 0xF0) | rs)
        self._nibble(((b << 4) & 0xF0) | rs)

    def _befehl(self, b):
        self._byte(b, 0)
        if b <= 3:
            time.sleep_ms(2)   # Loeschen/Home brauchen laenger

    def loeschen(self):
        self._befehl(0x01)

    def zeile(self, nr, text):
        """Schreibt text in Zeile nr (0 oder 1), mit Leerzeichen aufgefuellt."""
        self._befehl(0x80 | (0x40 * nr))
        text = (text + " " * self.spalten)[: self.spalten]
        for c in text:
            self._byte(ord(c) if ord(c) < 256 else 0x3F, _RS)

    def hintergrund(self, an):
        self.licht = _LICHT if an else 0
        self._schreiben(0)
