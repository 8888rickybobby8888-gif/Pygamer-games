#!/usr/bin/env python3
"""Reads the hand-made LEVELS[] table out of PyGamerPortal.ino and writes portal_levels.txt
(the human-editable source of truth).  Only needed once (or to re-import from an old sketch);
after the levels moved to the drive, the sketch keeps just the first 5 levels.
Then run make_portal_pack.py to build out/portal.lvl.
Usage: python extract_portal_levels.py [path-to-ino]"""
import os, re, sys

here = os.path.dirname(os.path.abspath(__file__))
ino = sys.argv[1] if len(sys.argv) > 1 else os.path.join(here, "..", "PyGamerPortal.ino")
text = open(ino, encoding="utf-8").read()
start = text.index("static const Level LEVELS[] = {")
end = text.index("// LEVEL_EDITOR_INSERT_POINT")
body = text[start:end]
levels = []
for m in re.finditer(r"\{\{(.*?)\}\}", body, re.S):
    rows = re.findall(r'"([^"]*)"', re.sub(r"//[^\n]*", "", m.group(1)))
    levels.append(rows)
out = ["# Portal levels. One block per level: a '# name' line (max 12 chars, A-Z 0-9 space -), then the rows.",
       "# Blank line between levels. Tile letters: # wall, N no-portal wall, . floor, ~ pit, I ice, S start, G goal,",
       "# X box, P plate, D door, ^v<> emitters, Y key, K locked door, u d l r conveyors, F boost, M mud, T/U teleporters.",
       "# Level numbers = order in this file (1-based). Never reorder/delete existing ones: append only.",
       ""]
for i, rows in enumerate(levels):
    out.append("# L%02d" % (i + 1))
    out.extend(rows)
    out.append("")
open(os.path.join(here, "portal_levels.txt"), "w", newline="\n").write("\n".join(out))
print("extracted", len(levels), "levels ->", os.path.join(here, "portal_levels.txt"))
