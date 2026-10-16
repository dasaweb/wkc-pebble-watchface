# WKC – Würzburger Kneipenchor Watchface

Ein Pebble-Watchface aus dem Logo des Würzburger Kneipenchors. Der runde Teil des Logos
(„CHOR“ mit Flasche) ist das Zifferblatt, die beiden Ringe sind die Zeiger:
**außen = Minuten, innen = Stunden** (beide starten bei 12 Uhr, im Uhrzeigersinn).

| Pegel | Lücke | Prost |
|:---:|:---:|:---:|
| ![Pegel](docs/round2_0.png) | ![Lücke](docs/round2_1.png) | ![Prost](docs/round2_2.png) |
| Die Original-Ringe füllen sich, der Rest ist als Punktreihe angedeutet | Ringe komplett wie im Logo, eine Lücke mit Kronkorken zeigt die Zeit | Glatte Bögen, Stunden in Biergelb, die Flasche zeigt den Akkustand |

**Design wechseln:** kurz das Handgelenk schütteln. Die Wahl bleibt gespeichert.

Läuft auf allen Pebbles: Pebble Classic/Steel, Time, Time Round, Pebble 2, 2 Duo, Time 2 und Round 2.
(Screenshots aus dem Emulator, alle bei 10:08 Uhr.)

![Alle Modelle](docs/alle_modelle.png)

## Installieren (ohne Programmierkenntnisse)

1. Unter [Releases](../../releases/latest) die Datei `WKC-Kneipenchor.pbw` aufs Handy laden.
2. Die Datei mit der Pebble-App öffnen ([repebble.com/app](https://repebble.com/app)). Die App installiert das Watchface auf der gekoppelten Uhr.

## Selbst bauen

Das SDK läuft unter Linux, macOS oder Windows mit WSL.

```sh
uv tool install pebble-tool --python 3.13
pebble sdk install latest
pebble build                       # -> build/wkc-watchface.pbw
pebble install --emulator gabbro   # im Emulator testen (Round 2)
pebble emu-tap --emulator gabbro   # Design wechseln
```

Auf die eigene Uhr: in der Pebble-App unter *Devices* → ⋮ die *Dev Connection* einschalten, dann

```sh
pebble login
pebble install --cloudpebble
```

## Logo-Grafiken neu erzeugen

`tools/make_assets.py` rendert das SVG (braucht Inkscape, numpy, scipy und Pillow) und trennt
„CHOR“ und die Flasche von den Ringen. Es richtet die handgezeichneten Ringe exakt kreisrund aus,
die Textur bleibt dabei erhalten. Pro Plattform schreibt es `resources/images/logo~<platform>.png`
und `beer~<platform>.png`.

```sh
python3 tools/make_assets.py logo/Kneipenchor_logo_fertig.svg
```

Für Screenshots mit fester Uhrzeit (10:08) oben in `src/c/main.c` `#define WKC_DEMO` setzen.

## Logo

Das Logo gehört dem Würzburger Kneipenchor und ist nicht Teil einer freien Lizenz.
