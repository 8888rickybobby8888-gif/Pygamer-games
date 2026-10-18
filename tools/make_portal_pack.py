#!/usr/bin/env python3
"""Builds out/portal.lvl from portal_levels.txt (see extract_portal_levels.py).
Format: header 8 B  "ARPL", u8 version=1, u16 LE count, u8 reserved 0
        record i at 8 + i*REC (REC=1616): u8 w, u8 h, char name[12] (space padded), u8 flags (0), u8 pad,
        cells[40*40] row-major with stride w (first w*h bytes used, the rest 0)."""
import os, sys
MAXC, MAXR = 40, 40
REC = 16 + MAXC * MAXR
VALID = set("#N.~ISGXPD^v<>YKudlrFMTU")
here = os.path.dirname(os.path.abspath(__file__))

def parse(path):
    levels, name, rows = [], None, []
    def flush():
        if name is not None and rows: levels.append((name, rows[:]))
    for ln in open(path, encoding="utf-8").read().split("\n"):
        ln = ln.rstrip("\r")
        if ln.startswith("# "):
            if rows: flush(); rows.clear(); name = None
            # comment lines before the first level are ignored; a name line starts a level
            cand = ln[2:].strip()
            if cand and all(c.isalnum() or c in " -" for c in cand) and len(cand) <= 12 and not cand.startswith("Portal"):
                name = cand.upper()
        elif ln.strip() == "":
            if rows: flush(); rows.clear(); name = None
        elif name is not None:
            rows.append(ln)
    if rows: flush()
    return levels

def validate(i, name, rows):
    h = len(rows); w = max(len(r) for r in rows)
    if not (1 <= h <= MAXR and 1 <= w <= MAXC): raise SystemExit("level %d: size %dx%d out of range" % (i + 1, w, h))
    for r in rows:
        for ch in r:
            if ch not in VALID: raise SystemExit("level %d: bad tile %r" % (i + 1, ch))
    s = sum(r.count("S") for r in rows); g = sum(r.count("G") for r in rows)
    if s != 1 or g > 1: raise SystemExit("level %d: needs exactly one S and at most one G (S=%d G=%d)" % (i + 1, s, g))
    if g == 0: print("note: level %d has no goal (sandbox level, as in the original table)" % (i + 1))

def build(levels):
    data = bytearray(b"ARPL" + bytes([1]) + len(levels).to_bytes(2, "little") + b"\0")
    for i, (name, rows) in enumerate(levels):
        validate(i, name, rows)
        w = max(len(r) for r in rows); h = len(rows)
        rec = bytearray(REC)
        rec[0], rec[1] = w, h
        rec[2:14] = name.ljust(12)[:12].encode("ascii")
        for r, row in enumerate(rows):
            rec[16 + r * w:16 + r * w + w] = row.ljust(w, ".").encode("ascii")
        data += rec
    return bytes(data)

def verify(data, levels):
    assert data[:4] == b"ARPL" and data[4] == 1 and int.from_bytes(data[5:7], "little") == len(levels)
    assert len(data) == 8 + len(levels) * REC
    for i, (name, rows) in enumerate(levels):
        o = 8 + i * REC; w, h = data[o], data[o + 1]
        assert h == len(rows) and w == max(len(r) for r in rows)
        for r in range(h):
            got = data[o + 16 + r * w:o + 16 + (r + 1) * w].decode("ascii")
            assert got == rows[r].ljust(w, "."), (i, r)

if __name__ == "__main__":
    src = os.path.join(here, "portal_levels.txt")
    levels = parse(src)
    data = build(levels)
    verify(data, levels)
    os.makedirs(os.path.join(here, "out"), exist_ok=True)
    open(os.path.join(here, "out", "portal.lvl"), "wb").write(data)
    print("wrote out/portal.lvl: %d levels, %d bytes, verified" % (len(levels), len(data)))
