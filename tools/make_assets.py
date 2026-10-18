#!/usr/bin/env python3
"""Builds banners.bin, the optional art pack for the Arcadia PyGamer sketch.

Format (see README_ASSETS.txt): header "ARB1", version=1, count, W=64, H=32, then count banners of
W*H RGB565 little-endian pixels, row-major. Game names/categories are parsed from PyGamerPortal.ino.

Usage:  python make_assets.py [--ino ../PyGamerPortal.ino] [--out out/banners.bin] [--preview out/preview.png]
Uses Pillow when installed (nicer fonts, anti-aliasing); otherwise falls back to a pure-stdlib
renderer with a built-in 5x7 block font.
"""
import argparse
import os
import re
import struct
import sys

W, H = 64, 32
CAT_COLS = {"Arcade": (255, 160, 40), "Reflex": (255, 230, 70), "Puzzle": (90, 210, 255),
            "Strategy": (180, 120, 255), "Battle": (255, 90, 90), "other": (90, 235, 150)}

try:
    from PIL import Image, ImageDraw, ImageFont
    HAVE_PIL = True
except Exception:
    HAVE_PIL = False


def parse_ino(path):
    src = open(path, encoding="utf-8", errors="replace").read()

    def table(name):
        m = re.search(name + r"\s*\[[^\]]*\]\s*=\s*\{(.*?)\};", src, re.S)
        if not m:
            sys.exit("cannot find " + name + " in " + path)
        return re.findall(r'"((?:[^"\\]|\\.)*)"', m.group(1))
    names, blurbs = table("kGameNames"), table("kGameBlurbs")
    n = min(len(names), len(blurbs))
    cats = []
    for b in blurbs[:n]:
        c = b.split(":")[0]
        cats.append(c if c in CAT_COLS else "other")
    return names[:n], cats


def rgb565(r, g, b):
    return ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


class Canvas:
    def __init__(self):
        self.px = [[(0, 0, 0)] * W for _ in range(H)]

    def put(self, x, y, c):
        if 0 <= x < W and 0 <= y < H:
            self.px[y][x] = c

    def rect(self, x, y, w, h, c):
        for yy in range(y, y + h):
            for xx in range(x, x + w):
                self.put(xx, yy, c)

    def circle(self, cx, cy, r, c):
        for yy in range(cy - r, cy + r + 1):
            for xx in range(cx - r, cx + r + 1):
                if (xx - cx) ** 2 + (yy - cy) ** 2 <= r * r:
                    self.put(xx, yy, c)

    def gradient(self, col):
        for y in range(H):
            c = lerp(lerp(col, (0, 0, 0), 0.25), lerp(col, (0, 0, 0), 0.8), y / (H - 1))
            for x in range(W):
                self.px[y][x] = c


def motif(cv, idx, col):
    """Decorative shapes in the upper half (the lower half carries the title)."""
    hi = lerp(col, (255, 255, 255), 0.55)
    lo = lerp(col, (0, 0, 0), 0.45)
    kind = idx % 6
    if kind == 0:      # bricks + ball
        for r in range(3):
            for k in range(5):
                cv.rect(3 + k * 12, 3 + r * 4, 10, 3, hi if (r + k) % 2 else col)
        cv.circle(40, 14, 2, (255, 255, 255))
    elif kind == 1:    # concentric rings
        for r, c in ((13, lo), (10, col), (7, hi), (4, col), (2, (255, 255, 255))):
            cv.circle(32, 8, r, c)
    elif kind == 2:    # staircase blocks
        for k in range(5):
            cv.rect(8 + k * 11, 14 - k * 3, 9, 3 + k * 3, hi if k % 2 else col)
    elif kind == 3:    # checker pattern
        for yy in range(3):
            for xx in range(8):
                cv.rect(xx * 8, 1 + yy * 5, 8, 5, hi if (xx + yy) % 2 else lo)
    elif kind == 4:    # diagonal bolts
        for k in range(6):
            for t in range(8):
                cv.put(6 + k * 10 + t, 2 + t, hi)
                cv.put(7 + k * 10 + t, 2 + t, col)
    else:              # dots
        for k in range(14):
            cv.circle(4 + (k * 13) % 60, 4 + (k * 7) % 11, 1 + k % 2, hi if k % 3 else col)


def find_font():
    d = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts")
    for f in ("impact.ttf", "arialbd.ttf", "consolab.ttf", "consola.ttf", "DejaVuSans-Bold.ttf"):
        p = os.path.join(d, f)
        if os.path.exists(p):
            return p
    return None


def banner_pil(idx, name, cat, font_path):
    col = CAT_COLS[cat]
    cv = Canvas()
    cv.gradient(col)
    motif(cv, idx, col)
    img = Image.new("RGB", (W, H))
    img.putdata([p for row in cv.px for p in row])
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle([0, 17, W - 1, H - 1], fill=(0, 0, 0, 150))
    size = 14
    font = ImageFont.load_default()
    while font_path and size >= 6:
        font = ImageFont.truetype(font_path, size)
        box = d.textbbox((0, 0), name, font=font)
        if box[2] - box[0] <= W - 6:
            break
        size -= 1
    box = d.textbbox((0, 0), name, font=font)
    tx = (W - (box[2] - box[0])) // 2 - box[0]
    ty = 17 + (H - 17 - (box[3] - box[1])) // 2 - box[1]
    d.text((tx + 1, ty + 1), name, fill=(0, 0, 0, 255), font=font)
    d.text((tx, ty), name, fill=(255, 255, 255, 255), font=font)
    d.rectangle([0, 0, W - 1, H - 1], outline=lerp(col, (255, 255, 255), 0.5))
    return img


FONT5x7 = {
    "A": "01110 10001 10001 11111 10001 10001 10001", "B": "11110 10001 10001 11110 10001 10001 11110",
    "C": "01110 10001 10000 10000 10000 10001 01110", "D": "11110 10001 10001 10001 10001 10001 11110",
    "E": "11111 10000 10000 11110 10000 10000 11111", "F": "11111 10000 10000 11110 10000 10000 10000",
    "G": "01110 10001 10000 10111 10001 10001 01111", "H": "10001 10001 10001 11111 10001 10001 10001",
    "I": "01110 00100 00100 00100 00100 00100 01110", "J": "00111 00010 00010 00010 00010 10010 01100",
    "K": "10001 10010 10100 11000 10100 10010 10001", "L": "10000 10000 10000 10000 10000 10000 11111",
    "M": "10001 11011 10101 10101 10001 10001 10001", "N": "10001 11001 10101 10011 10001 10001 10001",
    "O": "01110 10001 10001 10001 10001 10001 01110", "P": "11110 10001 10001 11110 10000 10000 10000",
    "Q": "01110 10001 10001 10001 10101 10010 01101", "R": "11110 10001 10001 11110 10100 10010 10001",
    "S": "01111 10000 10000 01110 00001 00001 11110", "T": "11111 00100 00100 00100 00100 00100 00100",
    "U": "10001 10001 10001 10001 10001 10001 01110", "V": "10001 10001 10001 10001 10001 01010 00100",
    "W": "10001 10001 10001 10101 10101 11011 10001", "X": "10001 10001 01010 00100 01010 10001 10001",
    "Y": "10001 10001 01010 00100 00100 00100 00100", "Z": "11111 00001 00010 00100 01000 10000 11111",
    "0": "01110 10011 10101 10101 11001 10001 01110", "1": "00100 01100 00100 00100 00100 00100 01110",
    "2": "01110 10001 00001 00110 01000 10000 11111", "3": "11110 00001 00001 01110 00001 00001 11110",
    "4": "00010 00110 01010 10010 11111 00010 00010", "5": "11111 10000 11110 00001 00001 10001 01110",
    "6": "00110 01000 10000 11110 10001 10001 01110", "7": "11111 00001 00010 00100 01000 01000 01000",
    "8": "01110 10001 10001 01110 10001 10001 01110", "9": "01110 10001 10001 01111 00001 00010 01100",
    "-": "00000 00000 00000 11111 00000 00000 00000", " ": "00000 00000 00000 00000 00000 00000 00000",
}


def banner_plain(idx, name, cat):
    col = CAT_COLS[cat]
    cv = Canvas()
    cv.gradient(col)
    motif(cv, idx, col)
    cv.rect(0, 17, W, H - 17, (10, 10, 20))
    text = name.upper()
    lines = [text]
    if len(text) * 6 - 1 > W - 4 and " " in text:   # wrap long names onto 2 lines
        words = text.split(" ")
        best = min(range(1, len(words)), key=lambda k: abs(len(" ".join(words[:k])) - len(" ".join(words[k:]))))
        lines = [" ".join(words[:best]), " ".join(words[best:])]
    total_h = 7 if len(lines) == 1 else 15
    y0 = 17 + (H - 17 - total_h) // 2
    for li, ln in enumerate(lines):
        x0 = (W - (len(ln) * 6 - 1)) // 2
        for ci, ch in enumerate(ln):
            g = FONT5x7.get(ch, FONT5x7[" "]).split()
            for gy, rowbits in enumerate(g):
                for gx, bit in enumerate(rowbits):
                    if bit == "1":
                        cv.put(x0 + ci * 6 + gx, y0 + li * 8 + gy, (255, 255, 255))
    edge = lerp(col, (255, 255, 255), 0.5)
    for x in range(W):
        cv.put(x, 0, edge)
        cv.put(x, H - 1, edge)
    for y in range(H):
        cv.put(0, y, edge)
        cv.put(W - 1, y, edge)
    return cv.px


def to_bytes(rows):
    out = bytearray()
    for row in rows:
        for (r, g, b) in row:
            out += struct.pack("<H", rgb565(r, g, b))
    return bytes(out)


def main():
    here = os.path.dirname(os.path.abspath(__file__))
    ap = argparse.ArgumentParser()
    ap.add_argument("--ino", default=os.path.join(here, "..", "PyGamerPortal.ino"))
    ap.add_argument("--out", default=os.path.join(here, "out", "banners.bin"))
    ap.add_argument("--preview", default=os.path.join(here, "out", "preview.png"))
    a = ap.parse_args()
    names, cats = parse_ino(a.ino)
    count = len(names)
    font_path = find_font() if HAVE_PIL else None
    print("renderer: " + ("Pillow" if HAVE_PIL else "stdlib fallback (install Pillow for nicer banners)")
          + ((" + " + os.path.basename(font_path)) if font_path else ""))
    data = bytearray(b"ARB1" + bytes([1, count, W, H]))
    previews = []
    for i, (n, c) in enumerate(zip(names, cats)):
        if HAVE_PIL:
            img = banner_pil(i, n, c, font_path)
            rows = [[img.getpixel((x, y)) for x in range(W)] for y in range(H)]
            previews.append(img)
        else:
            rows = banner_plain(i, n, c)
        b = to_bytes(rows)
        assert len(b) == W * H * 2
        data += b
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "wb") as f:
        f.write(data)
    print("wrote %s: %d banners, %d bytes" % (a.out, count, len(data)))
    if previews:
        cols = 8
        rows_n = (count + cols - 1) // cols
        sheet = Image.new("RGB", (cols * (W + 4), rows_n * (H + 4)), (20, 20, 20))
        for i, im in enumerate(previews):
            sheet.paste(im, ((i % cols) * (W + 4) + 2, (i // cols) * (H + 4) + 2))
        sheet = sheet.resize((sheet.width * 2, sheet.height * 2), Image.NEAREST)
        sheet.save(a.preview)
        print("preview sheet:", a.preview)


if __name__ == "__main__":
    main()
