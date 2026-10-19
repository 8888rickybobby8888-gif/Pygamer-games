ARCADIA LEVEL PACKS (optional)
==============================

What it is
  /packs/g<id>.pak on the PyGamer's USB drive: ready-made levels for a game that has a level creator,
  one file per game. <id> is the level-game id (the same number as in the custom-slot files g<id>s<slot>*.lvl).
  When a valid file exists, that game's Levels menu (Up on the title screen; Down on Reversi, Mastermind,
  Tank Duel) gets an extra row "Browse Packs" (hidden in 2 Player mode).

Generate (PC, any OS with Python 3, no extra packages)
  cd tools
  python make_packs.py        -> out\packs\g*.pak  (17 files, 322 levels, ~20 KB; deterministic, fixed seeds)
  python verify_packs.py      -> re-reads every file and prints a table (game, levels, bytes, OK/FAIL)

  Every generated level passes the same rules the sketch checks (see PyGamerPortal.ino *ValidateLevel), and
  where a game can be solved by a program the generator proves it: Sokoban (BFS over player + boxes), Lights
  Out (GF(2) solve, parity), Flood Fill (greedy solution fits the in-game move limit), Speed Maze (BFS),
  Cube Dash (a physics bot, 1/120 s steps, clears the track at all four speed tiers).

Install
  1. PyGamer: Settings > USB drive (the drive appears on the PC).
  2. PC:  powershell -ExecutionPolicy Bypass -File install_assets.ps1 -Packs
          (add -Drive E: if auto-detection fails). It finds the drive by its README.TXT, creates packs\ if
          needed, copies only the g<id>.pak files, prints the sizes and refuses when no PyGamer drive is found.
  3. EJECT the drive in Windows, then press B on the PyGamer. It reboots; nothing else is needed.
  Manual alternative: copy out\packs\*.pak to <drive>\packs\ yourself.

Remove
  Settings > USB drive, delete <drive>\packs\g<id>.pak (or the whole folder), eject, press B.
  The "Browse Packs" row disappears. Your own custom levels, saves and scores are never touched.

What the menu shows
  Levels menu > Browse Packs: the pack title, a scrollable list (name, D<n> = difficulty marker 1-9, a tick once
  you have cleared it) and a thumbnail of the highlighted level.
    Up/Down  choose        Left/Right  page +-5        A  play it
    Start    copy to my first free custom slot ("Saved to slot N")        B / Select  back
  Playing a pack level works like Test Play: pause menu "Back to Packs", B/Select on the over screen returns to the
  list. After a CLEAR the over screen shows "A: next level" (games that keep playing go straight on). Pack levels
  never change the global high scores or a custom slot's record. Plinko has no clear event, so it has no ticks.
  Ticks are stored in the save file (Settings > Reset saves clears them, Reset achievements does not).
  Awards: "Pack Rat" (10 pack levels cleared in total) and "Completionist" (every level of one pack cleared).
  A broken level (wrong size, tile id out of range, or rejected by the game's own checker) is listed greyed with
  "bad" and cannot be played. A file with a bad header, wrong game id, more than 60 levels or more than 20,480
  bytes is ignored (no row); a file cut short just ends the list at the last complete level.
  The packs are never read in USB drive mode or when the device runs on its RAM-only fallback.

File format (byte fields, no padding)
  offset 0   "ARPK"              magic
  offset 4   u8 version = 1
  offset 5   u8 game             LVLGAME_* id (must equal the <id> in the file name)
  offset 6   u8 count            1..60
  offset 7   u8 reserved = 0
  offset 8   char title[12]      ASCII, space padded
  offset 20  count records back to back:
               u8 w, u8 h        must fit the game's level grid
               char name[8]      A-Z 0-9 space '-' , space padded
               u8 par            1-9 difficulty marker (informational)
               u8 cells[w*h]     row-major, tile ids exactly as the level editor uses them
  File size < 20,480 bytes.

Games (id: grid, tiles) and what was generated
   0 Sokoban Mini   7x7    0 floor 1 wall 2 box 3 goal 4 start      30 levels, BFS-proved, difficulty = shortest solution
   2 Breakout       10x4   0 empty 1 brick                          15
   4 Speed Maze     9x7    0 floor 1 wall 2 start 3 goal            25, border walled, BFS path, difficulty = path length
   5 Space Invaders 5x3    0 empty 1 enemy                          12
   8 Minesweeper    10x8   0 empty 1 mine (8..28 mines)             20
   9 Flood Fill     10x10  colours 0-5, board = min(w,h)            20 (6x6..10x10, 3..6 colours, greedy <= move limit)
  10 Cube Dash      24xN   0 ground 1 spike 2 block 3 pit 4 double  20 tracks (48..96 cells), bot-cleared at all tiers
  11 Beat Tapper    16x4   0 empty 1 note (lane = row, step = column) 20
  12 Lunar Lander   20x1   heights 0-8, 9 = landing pad (3-5 wide)   20
  13 Lights Out     5x5    0 off 1 on                               30, GF(2)-solved, difficulty = fewest presses
  15 Plinko         9x9    0 empty 1 peg 2 bumper                   15 (no clear event: no ticks)
  16 Tank Duel      20x1   heights 0-8                              15
  20 Block Stack    10x8   0 empty 1-5 garbage colours              15, no full row, <= 70% filled
  21 Reversi        8x8    0 empty 1 black 2 white 3 block          15, black (and white) have an opening move
  22 Gem Swap       8x8    gems 0-5                                 15, no run at the start, a legal swap exists
  23 Bubble Shooter 10x8   0 empty 1-5 bubbles                      15, every bubble hangs from the ceiling
  24 Mastermind     5x1    colours 1-8 (5 pegs)                     20
  Not generated: Tilt Maze, Platform Dash, Snake, Wall Pong, Maze Chase, Air Hockey, Gap Flyer, Road Cross.
  You can add your own: make a g<id>.pak with the layout above (make_packs.py shows how) and install it.
