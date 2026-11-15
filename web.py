# Eigener WLAN-Hotspot mit kleiner Webseite.
# Handy verbinden, Browser auf http://192.168.4.1 :
#   /                 Seite mit aktuellen Werten, Verlauf und Download
#   /messdaten.csv    alle gespeicherten Messungen
#   /aktuell          aktuelle Werte als JSON
#   /zeit?t=<unix>    stellt die Uhr des Boards (macht die Seite automatisch)

import time
import socket
import select
import machine
import network

UNIX_ZU_MP = 946684800      # MicroPython auf dem ESP32 zaehlt ab 2000-01-01


def hotspot_starten(name, passwort):
    ap = network.WLAN(network.AP_IF)
    ap.active(True)
    ap.config(essid=name, password=passwort, authmode=network.AUTH_WPA2_PSK)
    return ap.ifconfig()[0]


class Server:
    def __init__(self, status, datei, bei_zeit_gesetzt=None):
        """status: Funktion, die ein dict mit aktuellen Werten liefert."""
        self.status = status
        self.datei = datei
        self.bei_zeit_gesetzt = bei_zeit_gesetzt
        self.sock = socket.socket()
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind(("0.0.0.0", 80))
        self.sock.listen(2)
        self.poll = select.poll()
        self.poll.register(self.sock, select.POLLIN)

    def warten(self, ms):
        """Beantwortet Anfragen, bis ms Millisekunden vergangen sind."""
        ende = time.ticks_add(time.ticks_ms(), ms)
        while True:
            rest = time.ticks_diff(ende, time.ticks_ms())
            if rest <= 0:
                return
            if self.poll.poll(rest):
                try:
                    cl, adr = self.sock.accept()
                except OSError:
                    continue
                try:
                    cl.settimeout(1)
                    self._anfrage(cl)
                except Exception as e:
                    print("Web-Fehler:", e)
                finally:
                    cl.close()

    def _anfrage(self, cl):
        zeile = cl.readline()
        while True:                         # restliche Kopfzeilen ueberlesen
            h = cl.readline()
            if not h or h == b"\r\n":
                break
        try:
            pfad = zeile.split()[1].decode()
        except (IndexError, UnicodeError):
            return
        print("Web:", pfad)
        pfad, _, query = pfad.partition("?")
        if pfad == "/":
            self._senden(cl, "text/html; charset=utf-8", SEITE)
        elif pfad == "/messdaten.csv":
            self._datei(cl)
        elif pfad == "/aktuell":
            self._senden(cl, "application/json", self._json(self.status()))
        elif pfad == "/zeit":
            self._zeit(cl, query)
        else:
            cl.write(b"HTTP/1.0 404 Not Found\r\n\r\n")

    def _senden(self, cl, typ, text):
        cl.write(("HTTP/1.0 200 OK\r\nContent-Type: %s\r\n"
                  "Cache-Control: no-store\r\n\r\n" % typ).encode())
        cl.write(text)

    def _datei(self, cl):
        cl.write(b"HTTP/1.0 200 OK\r\nContent-Type: text/csv\r\n"
                 b"Content-Disposition: attachment; filename=messdaten.csv\r\n\r\n")
        puffer = bytearray(1024)
        with open(self.datei, "rb") as f:
            while True:
                n = f.readinto(puffer)
                if not n:
                    break
                cl.write(memoryview(puffer)[:n])

    def _zeit(self, cl, query):
        alt = time.time()
        try:
            unix = int(query.split("t=")[1].split("&")[0])
        except (IndexError, ValueError):
            self._senden(cl, "text/plain", "fehler")
            return
        neu = unix - UNIX_ZU_MP
        if abs(neu - alt) > 30:             # nur bei echter Abweichung stellen
            j, mo, t, h, mi, s, wt, _ = time.localtime(neu)
            machine.RTC().datetime((j, mo, t, wt, h, mi, s, 0))
            if self.bei_zeit_gesetzt:
                self.bei_zeit_gesetzt(alt)
            self._senden(cl, "text/plain", "gestellt")
        else:
            self._senden(cl, "text/plain", "ok")

    @staticmethod
    def _json(d):
        teile = []
        for k, v in d.items():
            if v is None:
                v = "null"
            elif isinstance(v, str):
                v = '"%s"' % v
            teile.append('"%s":%s' % (k, v))
        return "{" + ",".join(teile) + "}"


SEITE = """<!doctype html>
<html lang="de"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Organon Metrikon Alpha</title>
<style>
body{font-family:system-ui,sans-serif;margin:0;padding:16px;background:#f6f4ef;color:#222}
h1{font-size:1.2em;margin:0 0 2px}
.sub{color:#666;font-size:.85em;margin-bottom:16px}
.werte{display:flex;gap:12px;margin-bottom:16px}
.kachel{flex:1;background:#fff;border-radius:10px;padding:12px;box-shadow:0 1px 3px #0002}
.zahl{font-size:2em;font-weight:600}
.t{color:#c2410c}.f{color:#1d4ed8}
.klein{color:#666;font-size:.85em}
svg{width:100%;height:160px;background:#fff;border-radius:10px;box-shadow:0 1px 3px #0002;margin-bottom:12px}
a.knopf{display:block;text-align:center;background:#222;color:#fff;padding:14px;border-radius:10px;text-decoration:none;margin:12px 0}
</style></head><body>
<h1>ὄργανον μετρικὸν α′</h1>
<div class="sub">Organon Metrikon Alpha &middot; Thermo-Hygrograph</div>
<div class="werte">
 <div class="kachel"><div class="klein">Temperatur</div><div class="zahl t" id="t">&ndash;</div></div>
 <div class="kachel"><div class="klein">Luftfeuchte</div><div class="zahl f" id="f">&ndash;</div></div>
</div>
<div class="klein" id="info">lade &hellip;</div>
<a class="knopf" href="/messdaten.csv" download="messdaten.csv">Messdaten herunterladen (CSV)</a>
<div class="klein">Verlauf (gespeicherte Stundenwerte)</div>
<svg id="gt" viewBox="0 0 400 160" preserveAspectRatio="none"></svg>
<svg id="gf" viewBox="0 0 400 160" preserveAspectRatio="none"></svg>
<div class="klein" id="zeit"></div>
<script>
function $(i){return document.getElementById(i)}
fetch('/zeit?t='+Math.floor(Date.now()/1000)).then(r=>r.text()).then(x=>{
 $('zeit').textContent = x=='gestellt' ? 'Uhr des Messgeraets wurde nach diesem Handy gestellt.' : 'Uhr des Messgeraets stimmt.'});
function aktuell(){fetch('/aktuell').then(r=>r.json()).then(d=>{
 $('t').textContent = d.t==null?'–':d.t.toFixed(1)+' °C';
 $('f').textContent = d.f==null?'–':d.f.toFixed(1)+' %';
 $('info').textContent = d.anzahl+' gespeicherte Messungen · laeuft seit '+Math.round(d.laufzeit_min/60)+' h';
})}
aktuell(); setInterval(aktuell,5000);
function kurve(id,werte,farbe,einheit){
 var s=$(id), v=werte.filter(x=>!isNaN(x));
 if(v.length<2){s.innerHTML='<text x="10" y="85" font-size="12" fill="#888">noch zu wenige Werte</text>';return}
 var mn=Math.min(...v), mx=Math.max(...v); if(mx-mn<1){mn-=.5;mx+=.5}
 var n=werte.length, p=[], i;
 for(i=0;i<n;i++) if(!isNaN(werte[i])) p.push((i/(n-1)*390+5).toFixed(1)+','+(150-(werte[i]-mn)/(mx-mn)*130).toFixed(1));
 s.innerHTML='<polyline fill="none" stroke="'+farbe+'" stroke-width="1.5" vector-effect="non-scaling-stroke" points="'+p.join(' ')+'"/>'+
  '<text x="6" y="14" font-size="11" fill="#666">'+mx.toFixed(1)+einheit+'</text>'+
  '<text x="6" y="156" font-size="11" fill="#666">'+mn.toFixed(1)+einheit+'</text>';
}
fetch('/messdaten.csv').then(r=>r.text()).then(txt=>{
 var t=[],f=[];
 txt.split('\\n').forEach(z=>{if(/^[0-9u]/.test(z)){var c=z.split(',');t.push(parseFloat(c[2]));f.push(parseFloat(c[3]))}});
 kurve('gt',t,'#c2410c',' °C'); kurve('gf',f,'#1d4ed8',' %');
});
</script></body></html>
"""
