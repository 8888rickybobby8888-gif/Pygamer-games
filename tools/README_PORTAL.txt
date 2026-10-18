PORTAL HAND-MADE LEVELS ON THE DRIVE
====================================

What it is
  Portal levels 6..52 (the hand-made ones) are no longer compiled into the sketch. They are read at level
  load from /packs/portal.lvl on the PyGamer drive. Levels 1-5 (the tutorials) stay in flash as the fallback.
  Level NUMBERS never change: NUM_HAND_LEVELS is still the constant 52, generated levels are still 53..1052.
  If the file is missing / invalid, or one record is bad, that level number becomes a deterministic GENERATED
  maze (generator index (n-5)*3, so tiers 0-1, same n = same maze). Nothing crashes; progress numbering is the same.

Files
  tools\portal_levels.txt        source of truth: "# L06" line + grid rows per level, blank line between levels
  tools\extract_portal_levels.py one-off import of LEVELS[] from an OLD sketch (not needed any more)
  tools\make_portal_pack.py      portal_levels.txt -> tools\out\portal.lvl (validates, reads back, compares cells)
  tools\install_assets.ps1 -Portal   copies out\portal.lvl to <drive>\packs\portal.lvl

Install
  1. Build:   cd tools ; python make_portal_pack.py
  2. PyGamer: Settings > USB drive.
  3. PC:      powershell -ExecutionPolicy Bypass -File install_assets.ps1 -Portal   (add -Drive E: if needed)
  4. EJECT the drive, press B on the PyGamer (reboots; the file is probed once at boot).
  Do this BEFORE flashing the smaller sketch build (otherwise levels 6-52 are generated mazes until you do).

File format (fixed-size records so a level is found with one seek)
  header 8 B: "ARPL", u8 version=1, u16 LE count, u8 0
  record i at 8 + i*1616 (i = level index, 0-based): u8 w, u8 h, char name[12], u8 flags(0), u8 pad,
          then w*h tile chars (row-major, stride w, same letters as the old LEVELS[] rows), rest zero.
  Valid: w,h 1..40; only the tile letters #N.~ISGXPD^v<>YKudlrFMTU; exactly one S. Records 0-4 are ignored by
  the sketch (flash copy wins); only records < 52 are played. Records beyond 52 are stored but NOT shown yet
  (no "extra levels" menu was built, to keep the numbering and menus untouched).

Editing
  Edit tools\portal_levels.txt (keep order, do not delete/reorder: numbers must stay stable), run
  make_portal_pack.py, install again. level_editor_server.js "Upload" now appends the exported level to
  portal_levels.txt, rebuilds portal.lvl and tells you whether the PyGamer drive is mounted; POST /api/copy-portal
  (or install_assets.ps1 -Portal) copies it. It no longer touches the .ino or flashes the board.
