#!/usr/bin/env python3
"""Erzeugt die Watchface-Bitmaps aus dem WKC-Logo (SVG).

- Rendert das SVG gross (via Inkscape)
- trennt "CHOR"+Flasche von den beiden Ringen
- begradigt die handgezeichneten Ringe auf exakt konzentrische Kreise
  (die Grunge-Textur bleibt erhalten), damit sie sich im Code als
  Zeiger ausschneiden lassen
- schreibt pro Plattform logo.png (+ beer.png fuer Farbuhren)

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

    rings = straighten(inner, cx, cy, R_INNER, (S, S)) | \
            straighten(outer, cx, cy, R_OUTER, (S, S))
    full = crop(content) | rings
    beer = crop(beer)

    os.makedirs(OUT, exist_ok=True)
    meta = {}
    for plat, (d, color) in PLATFORMS.items():
        img = Image.fromarray((full * 255).astype(np.uint8)).resize((d, d), Image.LANCZOS)
        if color:
            a = np.array(img).astype(float) / 255
            a = np.round(a * 3) / 3 * 255  # 4 Graustufen
            img = Image.fromarray(a.astype(np.uint8)).convert("RGB")
        else:
            img = img.point(lambda v: 255 if v > 110 else 0).convert("1")
        img.save(os.path.join(OUT, f"logo~{plat}.png"))
        if color:
            b = Image.fromarray((beer * 255).astype(np.uint8)).resize((d, d), Image.LANCZOS)
            alpha = np.array(b)
            alpha = np.where(alpha > 100, 255, 0).astype(np.uint8)
            # Rand der Flasche nicht ueberdecken
            alpha = ndimage.binary_erosion(alpha > 0, iterations=1).astype(np.uint8) * 255
            rgba = np.zeros((d, d, 4), np.uint8)
            rgba[..., :3] = BEER
            rgba[..., 3] = alpha
            Image.fromarray(rgba, "RGBA").save(os.path.join(OUT, f"beer~{plat}.png"))
            ys = np.where(alpha.any(axis=1))[0]
            meta[plat] = {"beer_top": int(ys.min()), "beer_bottom": int(ys.max())}
        scale = d / S
        meta.setdefault(plat, {}).update({
            "size": d,
            "r_inner": round(R_INNER * scale, 2),
            "r_outer": round(R_OUTER * scale, 2),
        })
    print(json.dumps(meta, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
