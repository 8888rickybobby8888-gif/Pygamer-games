ARCADIA ART PACK (optional)
===========================

What it is
  assets\banners.bin on the PyGamer's USB drive. When present, the title screens of the games
  that use the shared title layout (Block Stack, 2048, Minesweeper, Road Cross, Maze Chase, Lunar
  Lander, Sky Hop, Beat Tapper, Space Blaster, Tower Stack, Slide 15, Plinko, Lucky Slots, Cube Dash,
  Flood Fill, Asteroids, Gem Swap, Road Racer, Bubble Shooter, Tilt Slalom) show a 64x32 banner
  instead of the small icon. The first banner shown unlocks the "Art Lover" award.
  Older games with their own hand-built title screens (and Mastermind, Checkers, Chess) keep their look.

Generate it (PC, any OS with Python 3)
  cd PyGamerPortal\tools
  python make_assets.py
  -> out\banners.bin (56 banners, 229,384 bytes) and out\preview.png (contact sheet)
  Pillow (pip install pillow) gives nicer text; without it a built-in pixel font is used. Game names
  and categories are read from PyGamerPortal.ino, so regenerate after adding games. Output is
  deterministic for the same inputs and fonts.

Install
  1. PyGamer: Settings > USB drive (the drive appears on the PC).
  2. PC:  powershell -ExecutionPolicy Bypass -File install_assets.ps1
          (or add -Drive E: if auto-detection fails). It finds the drive by its README.TXT,
          creates assets\ if needed and copies only banners.bin.
  3. EJECT the drive in Windows, then press B on the PyGamer. It reboots; the pack is checked at boot.
  Manual alternative: copy out\banners.bin to <drive>\assets\banners.bin yourself.

Remove
  Enter Settings > USB drive, delete <drive>\assets\banners.bin, eject, press B. The old icons return.

Without the pack (or if the file is damaged, short, or from another version)
  Nothing changes: the built-in 8x8 icon title screens are used and nothing is shown or reported.
  The file is never read in USB drive mode or when the device runs on its RAM-only fallback.

File format (little-endian)
  offset 0   "ARB1"           magic
  offset 4   u8 version = 1
  offset 5   u8 count         banners in the file (index = game number in the picker; extra games
                              beyond count simply get no banner)
  offset 6   u8 width  = 64
  offset 7   u8 height = 32
  offset 8   count x (64*32) RGB565 pixels, 2 bytes each, low byte first, row-major, top row first
             (4096 bytes per banner). File size must be >= 8 + count*4096.
  The game reads one 128-byte row at a time while drawing a title screen (about once per screen
  entry), so the pack costs no extra RAM.

Word list (Hangman / Wordle): see README_WORDS.txt  (install_assets.ps1 -Words).
