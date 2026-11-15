#!/usr/bin/env bash
# Hilfsskript fuer den Thermo-Hygrographen.
# Voraussetzung: pip install mpremote
#
#   ./board.sh aufspielen   main.py (und ggf. secrets.py) aufs Board kopieren
#   ./board.sh zeit         Uhr des Boards auf die aktuelle UTC-Zeit des PCs stellen
#   ./board.sh auslesen     messdaten.csv vom Board holen (in den Ordner daten/)
#   ./board.sh live         laufende Ausgabe des Boards anzeigen (Ende: Ctrl-X)
#   ./board.sh loeschen     messdaten.csv auf dem Board loeschen (fragt nach)
#
# Achtung: Jeder Befehl unterbricht kurz das Messprogramm. Das Skript startet
# es danach automatisch neu (Zeile "# Neustart" in der CSV).

set -euo pipefail
cd "$(dirname "$0")"
MP="${MPREMOTE:-mpremote}"

# Echter Reset: main.py startet neu, die Uhr des Boards bleibt erhalten
# (nur bei Stromausfall geht sie verloren).
neustart() { $MP reset >/dev/null 2>&1 || true; echo "Messprogramm neu gestartet."; }

uhr_setzen() {
  read -r J M T H MI S <<<"$(date -u '+%Y %-m %-d %-H %-M %-S')"
  $MP exec "import machine; machine.RTC().datetime(($J,$M,$T,0,$H,$MI,$S,0)); import time; print('Board-Zeit (UTC):', time.localtime()[:6])"
}

case "${1:-}" in
  aufspielen)
    $MP fs cp main.py :main.py
    [ -f secrets.py ] && $MP fs cp secrets.py :secrets.py
    uhr_setzen
    neustart ;;
  zeit)
    uhr_setzen
    neustart ;;
  auslesen)
    mkdir -p daten
    ZIEL="daten/messdaten_$(date '+%Y-%m-%d_%H%M').csv"
    $MP fs cp :messdaten.csv "$ZIEL"
    echo "Gespeichert: $ZIEL ($(grep -c '^[0-9u]' "$ZIEL" || true) Messungen)"
    neustart ;;
  live)
    $MP repl ;;
  loeschen)
    read -r -p "Wirklich alle Messdaten auf dem Board loeschen? (ja/nein) " A
    [ "$A" = "ja" ] && $MP fs rm :messdaten.csv && echo "Geloescht."
    neustart ;;
  *)
    sed -n '2,13p' "$0" ;;
esac
