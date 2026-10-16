#!/usr/bin/env python3
"""Bettet die Screenshots aus docs/ als data-URIs in die Einstellungsseite ein.

Die Clay-Seite läuft auf dem Handy als lokale Seite, deshalb kommen die Bilder
direkt in src/pkjs/screenshots.js statt als Link.

Aufruf: python3 tools/make_config_images.py
"""
import base64
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")

lines = ["// Generiert von tools/make_config_images.py", "module.exports = ["]
for i in range(3):
    with open(os.path.join(ROOT, "docs", f"round2_{i}.png"), "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    lines.append(f"  'data:image/png;base64,{b64}',")
lines.append("];")
with open(os.path.join(ROOT, "src", "pkjs", "screenshots.js"), "w") as f:
    f.write("\n".join(lines) + "\n")
