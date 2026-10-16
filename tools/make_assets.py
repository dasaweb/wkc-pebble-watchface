#!/usr/bin/env python3
"""Erzeugt die Watchface-Bitmaps aus dem WKC-Logo (SVG).

- Rendert das SVG gross (via Inkscape)
- trennt "CHOR"+Flasche von den beiden Ringen
- begradigt die handgezeichneten Ringe auf exakt konzentrische Kreise
  (die Grunge-Textur bleibt erhalten), damit sie sich im Code als
  Zeiger ausschneiden lassen
- schreibt pro Plattform logo.png, beer.png (Akku-Fuellung) und auf
  Farbuhren ring.png (eingefaerbter Stundenring)
- schreibt die Fuellstaende der Flasche nach src/c/bottle.h

Aufruf: python3 tools/make_assets.py logo/Kneipenchor_logo_fertig.svg
"""
import json
import os
import subprocess
import sys
import tempfile
import warnings

import numpy as np
from PIL import Image
from scipy import ndimage

warnings.filterwarnings("ignore")

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "..", "resources", "images")
SRC_PX = 2363

# Zielgeometrie im Quell-Pixelraum (2363er Rendering)
R_INNER = 735     # Mittellinie innerer Ring (Stunden)
R_OUTER = 822     # Mittellinie aeusserer Ring (Minuten)
R_CROP = 850      # Radius des ausgeschnittenen Kreises

# Plattform -> (Durchmesser der Logo-Bitmap, Farbe?)
PLATFORMS = {
    "aplite": (142, False),
    "basalt": (142, True),
    "chalk": (176, True),
    "diorite": (142, False),
    "flint": (142, False),
    "emery": (196, True),
    "gabbro": (256, True),
}
BEER = (255, 255, 0)  # GColorYellow (ChromeYellow wirkt auf der Uhr lachsfarben)


def render(svg):
    png = os.path.join(tempfile.mkdtemp(), "logo.png")
    subprocess.run(["inkscape", os.path.abspath(svg), "--export-type=png",
                    f"--export-filename={png}", "-w", str(SRC_PX)],
                   check=True, capture_output=True)
    return np.array(Image.open(png).convert("L")) > 128


def ring_components(im, lab, n):
    """Die zwei groessten Komponenten mit Ringform (bbox ~ quadratisch, gross)."""
    sizes = ndimage.sum(im, lab, range(1, n + 1))
    objs = ndimage.find_objects(lab)
    rings = []
    for i in np.argsort(-sizes):
        sl = objs[i]
        h, w = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        if 1200 < w < 1800 and abs(w - h) < 120:
            rings.append(i + 1)
        if len(rings) == 2:
            break
    # aussen zuerst
    rings.sort(key=lambda L: -(objs[L - 1][1].stop - objs[L - 1][1].start))
    return rings


def straighten(mask, cx, cy, r_target, out_shape):
    """Bildet einen welligen Ring auf einen exakten Kreis mit Radius r_target ab."""
    yy, xx = np.indices(mask.shape)
    rr = np.hypot(xx - cx, yy - cy)
    th = np.arctan2(xx - cx, cy - yy)
    nb = 720
    bins = ((th % (2 * np.pi)) / (2 * np.pi) * nb).astype(int) % nb
    m = mask
    rsum = np.bincount(bins[m], rr[m], nb)
    cnt = np.bincount(bins[m], None, nb)
    rc = np.where(cnt > 0, rsum / np.maximum(cnt, 1), np.nan)
    # Luecken interpolieren, zirkulaer glaetten
    idx = np.arange(nb)
    ok = ~np.isnan(rc)
    rc = np.interp(idx, idx[ok], rc[ok], period=nb)
    k = 9
    rc = np.convolve(np.r_[rc[-k:], rc, rc[:k]], np.ones(2 * k + 1) / (2 * k + 1), "valid")

    H, W = out_shape
    oy, ox = np.indices(out_shape).astype(float)
    ox -= W / 2
    oy -= H / 2
    rho = np.hypot(ox, oy)
    oth = np.arctan2(ox, -oy)
    ob = ((oth % (2 * np.pi)) / (2 * np.pi) * nb).astype(int) % nb
    src_r = rc[ob] + (rho - r_target)
    sx = np.round(cx + src_r * np.sin(oth)).astype(int)
    sy = np.round(cy - src_r * np.cos(oth)).astype(int)
    valid = (sx >= 0) & (sx < mask.shape[1]) & (sy >= 0) & (sy < mask.shape[0])
    valid &= np.abs(rho - r_target) < 60
    out = np.zeros(out_shape, bool)
    out[valid] = mask[sy[valid], sx[valid]]
    return out


def main(svg):
    im = render(svg)
    lab, n = ndimage.label(im)
    outer_L, inner_L = ring_components(im, lab, n)
    inner = lab == inner_L
    outer = lab == outer_L
    iy, ix = np.where(inner)
    cx, cy = ix.mean(), iy.mean()

    # Inhalt: alles, was komplett innerhalb des inneren Rings liegt
    yy, xx = np.indices(im.shape)
    rr = np.hypot(xx - cx, yy - cy)
    maxr = ndimage.maximum(rr, lab, range(1, n + 1))
    keep_ids = np.where(maxr < R_INNER - 30)[0] + 1
    content = np.isin(lab, keep_ids)

    # Bierfuellung = schwarzer Innenraum der Flasche
    bys, bxs = np.where(content)
    holes = ndimage.label(~content)[0]
    # die Flasche ist der hohe, schmale schwarze Bereich nahe der Mitte
    beer = np.zeros_like(content)
    best = None
    for L in np.unique(holes[np.abs(rr) < 500]):
        if L == 0:
            continue
        m = holes == L
        s = m.sum()
        if s > 400000 or s < 20000:
            continue
        ys, xs = np.where(m)
        h, w = ys.ptp(), xs.ptp()
        if h > 2.5 * w and (best is None or s > best[0]):
            best = (s, L)
    if best:
        beer = holes == best[1]

    S = 2 * R_CROP
    def crop(mask):
        x0, y0 = int(round(cx - R_CROP)), int(round(cy - R_CROP))
        pad = np.zeros((S, S), bool)
        sx0, sy0 = max(0, x0), max(0, y0)
        sx1, sy1 = min(mask.shape[1], x0 + S), min(mask.shape[0], y0 + S)
        pad[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = mask[sy0:sy1, sx0:sx1]
        return pad

    ring_in = straighten(inner, cx, cy, R_INNER, (S, S))
    ring_out = straighten(outer, cx, cy, R_OUTER, (S, S))
    full = crop(content) | ring_in | ring_out
    beer = crop(beer)
    write_bottle_header(beer)

    os.makedirs(OUT, exist_ok=True)
    meta = {}
    for plat, (d, color) in PLATFORMS.items():
        img = downscale(full, d)
        if color:
            a = np.round(img / 255 * 3) / 3 * 255  # 4 Graustufen
            Image.fromarray(a.astype(np.uint8)).convert("RGB").save(
                os.path.join(OUT, f"logo~{plat}.png"))
            # Stundenring einzeln, damit er sich einfaerben laesst
            save_tinted(downscale(ring_in, d) > 110, f"ring~{plat}.png")
        else:
            save_bw(img > 110, f"logo~{plat}.png")

        # Bierfuellung, 1px eingerueckt, damit der Flaschenrand sichtbar bleibt
        b = ndimage.binary_erosion(downscale(beer, d) > 100, iterations=1)
        save_tinted(b, f"beer~{plat}.png", BEER if color else (255, 255, 255))
        meta[plat] = {"size": d}
    print(json.dumps(meta))


def downscale(mask, d):
    img = Image.fromarray((mask * 255).astype(np.uint8)).resize((d, d), Image.LANCZOS)
    return np.array(img).astype(float)


def save_tinted(mask, name, rgb=BEER):
    rgba = np.zeros(mask.shape + (4,), np.uint8)
    rgba[..., :3] = rgb
    rgba[..., 3] = mask * 255
    Image.fromarray(rgba, "RGBA").save(os.path.join(OUT, name))


def save_bw(mask, name):
    Image.fromarray((mask * 255).astype(np.uint8)).convert("1").save(os.path.join(OUT, name))


def write_bottle_header(beer):
    """Fuellstaende der Flasche in Promille der Bitmap-Hoehe -> src/c/bottle.h

    0 % = Flaschenboden, 80 % = Ende des Flaschenhalses, 100 % = etwas
    unterhalb der Muendung (oben bleibt Luft wie bei einer echten Flasche).
    """
    S = beer.shape[0]
    rows = np.where(beer.any(axis=1))[0]
    top, bottom = rows.min(), rows.max()
    width = beer.sum(axis=1)
    upper = np.arange(top, top + int(0.4 * (bottom - top)))
    neck_w = np.median(width[upper])
    # Muendung: breiterer Rand ganz oben
    lip = top
    while width[lip + 1] > neck_w * 1.25 or lip < top + 3:
        lip += 1
    # Halsende: ab hier wird die Flasche deutlich breiter (Schulter)
    neck_end = upper[-1]
    while width[neck_end] > neck_w * 1.15:
        neck_end -= 1
    while width[neck_end + 1] <= neck_w * 1.15:
        neck_end += 1
    full = lip + 0.35 * (neck_end - lip)
    pm = lambda y: int(round(y * 1000 / S))
    path = os.path.join(HERE, "..", "src", "c", "bottle.h")
    with open(path, "w") as f:
        f.write("// Generiert von tools/make_assets.py – Fuellstaende der Flasche\n"
                "// in Promille der Logo-Bitmap-Hoehe (0 = oben)\n"
                "#pragma once\n"
                f"#define BOTTLE_FULL  {pm(full)}  // 100 %: etwas Luft im Hals\n"
                f"#define BOTTLE_NECK  {pm(neck_end)}  // 80 %: Ende des Flaschenhalses\n"
                f"#define BOTTLE_EMPTY {pm(bottom)}  // 0 %: Flaschenboden\n")


if __name__ == "__main__":
    main(sys.argv[1])
