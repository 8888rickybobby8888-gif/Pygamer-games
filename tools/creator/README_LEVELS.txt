ARCADIA LEVEL CREATOR  (tools\creator\arcadia_levels.html)
==========================================================

One offline HTML file (no install, no internet, vanilla JS). Double-click it. Your work is kept in the
browser (localStorage) between visits; "Export everything" writes the real device files.

What it edits
  * 25 games that have an on-device level creator (the Levels menu of each game):
      0 Sokoban Mini   1 Tilt Maze      2 Breakout       3 Platform Dash   4 Speed Maze
      5 Space Invaders 6 Snake          7 Wall Pong      8 Minesweeper     9 Flood Fill
     10 Cube Dash     11 Beat Tapper   12 Lunar Lander  13 Lights Out     14 Maze Chase
     15 Plinko        16 Tank Duel     17 Air Hockey    18 Gap Flyer      19 Road Cross
     20 Block Stack   21 Reversi       22 Gem Swap      23 Bubble Shooter 24 Mastermind
    Grid sizes, tile palettes and validation rules are the ones in PyGamerPortal.ino (kLevelGames[] and the
    *ValidateLevel functions). A red message = the device refuses to play the level; an amber message = a
    pack-quality extra (solvability, Cube Dash bot, Flood Fill move limit, Speed Maze border).
  * Portal hand-made levels (portal.lvl, levels 1..52+, up to 40x40, tile letters).
  * Portal Quest world (quest.wld): 8x8 map of regions, per-region tile grid, objects (crystals, keys, locks,
    signs, checkpoints, teleports, secrets, gate, win diamond, NPCs), strings, header, doorway helper,
    whole-world reachability check (keys/locks/gate/teleports/ice/belts, like make_quest_world.py).
  Games WITHOUT a level creator (nothing to edit): Portal Quest levels are the world file above; all other picker
  games, carts (*.arc) and CHIP-8 roms are not level-based (see tools\README_CARTS.txt / README_CHIP8.txt).

Using it
  * Pick a game in the drop-down. Paint with the left mouse button, erase with the right button (erases to the
    game's default tile), tools Paint / Rect / Fill / Pick, Undo/Redo (Ctrl+Z / Ctrl+Y), mirror, clear, resize.
    Number keys 0-9 choose the tile. Height games (Lunar Lander, Tank Duel, Gap Flyer) draw bars: click at the
    height you want (choose PAD to place the Lunar Lander pad).
  * Import: "Import files..." or drag files onto the page. Understood: g<id>s<slot>[a|b].lvl (any version
    0xA5..0xA8, checksum checked), g<id>.pak, portal.lvl, portal_levels.txt, quest.wld.
  * Each level has: name (8 chars A-Z 0-9 -), pack difficulty 1-9, optional custom slot 0-4, "verified" flag.

What the exports are (byte-exact with what the device itself writes / the PC tools make)
  Slot file     levels\g<id>s<slot>a.lvl   device format v4 (0xA8): [magic][game|verified<<7][w][h][name x8]
                [best int32 = none][cells row-major][generation][rotating checksum]. This is exactly what
                lvlSerialize + the atomic saver produce. Choose "Generation" and file letter a/b in the panel.
                The device loads the valid file with the NEWER generation, so delete older
                g<id>s<slot>*.lvl on the drive first (or give your file a higher generation).
  Level pack    packs\g<id>.pak            "ARPK" v1, up to 60 levels, < 20,480 bytes (see README_PACKS.txt).
                Same bytes make_packs.py writes (the 322 shipped levels re-export identically).
  Portal        packs\portal.lvl           "ARPL" v1, 1616-byte records (see README_PORTAL.txt); also
                portal_levels.txt (the source make_portal_pack.py reads). Levels are numbered by position:
                only APPEND levels, never reorder/delete earlier ones. The device uses records 6..52; records
                1-5 are ignored (the flash copies win), keep them as they are.
  Quest world   worlds\quest.wld           "ARQW" v1 (see README_QUEST.txt). World id is recomputed as the
                CRC32 of all region data, like make_quest_world.py, so saves of an old world are reset.

Where the files go on the PyGamer drive
  1. PyGamer: Settings > USB drive.   2. Copy.   3. EJECT in Windows, THEN press B on the PyGamer.
      <drive>\levels\g<id>s<slot>a.lvl      custom level slots (5 per game)
      <drive>\packs\g<id>.pak               "Browse Packs" in that game's Levels menu
      <drive>\packs\portal.lvl              Portal levels 6..52
      <drive>\worlds\quest.wld              Portal Quest
  "Export everything (drive zip)" produces arcadia_drive_files.zip with exactly these folders - unzip it onto
  the drive. Packs over the size limit and a Portal/Quest file with errors are left out of the zip.

PowerShell installer (tools\install_assets.ps1, run one switch at a time)
  Save exports into tools\out\... and run, with the PyGamer in USB drive mode:
    -Levels   tools\out\levels\g<id>s<slot>[a|b].lvl  ->  <drive>\levels\     (new; checks names + headers)
    -Packs    tools\out\packs\g*.pak                   ->  <drive>\packs\
    -Portal   tools\out\portal.lvl                     ->  <drive>\packs\portal.lvl
    -Quest    tools\out\quest.wld                      ->  <drive>\worlds\quest.wld
  e.g.  powershell -ExecutionPolicy Bypass -File install_assets.ps1 -Levels      (add -Drive E: if needed)

Notes / limits
  * New levels start at the game's full grid. Smaller sizes are allowed (Flood Fill boards 6x6..10x10, Cube
    Dash tracks 24xN); the device pads smaller saved levels with the default tile when you edit them.
  * Slot files carry no "best score"; the verified flag is off unless you tick it (you only earn it by clearing
    the level in Test Play on the device).
  * Quest: the objects tool adds/selects objects (right-click removes). Adding a locked door / secret wall /
    crystal gate also places its K / # / N tile. "Open doorways to neighbours" carves 2-wide matching doorways;
    keep the same row/column on both sides of every link. Plate and laser puzzles are assumed solvable.
  * The deep check (Cube Dash) runs the same physics bot as verify_packs.py at all four speeds.
